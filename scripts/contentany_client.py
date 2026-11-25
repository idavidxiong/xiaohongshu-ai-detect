#!/usr/bin/env python3
"""小红书封面和AI检测工具。

对接 ContentAny 产品站 https://cn.aifoxs.com ：账号校验、分段 AIGC 检测、内容质量报告。
报告里整理敏感词、资质和内容质量。封面设计不在这个脚本里，走技能提示词。
低创作、限流、流量预测、人性化优化等接口不在这里调用。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import ssl
import string
import sys
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

DEFAULT_API_BASE = "https://cn.aifoxs.com"
PRODUCT_URL = "https://cn.aifoxs.com"
EMAIL_DOMAIN = "contentany.cn"
SESSION_PATH = Path.home() / ".contentany" / "ai-detect-session.json"
AI_CHECK_MODEL_UNICODE_CAP = 400
BACKEND_SHORT_SEGMENT_THRESHOLD = 25
BACKEND_SHORT_SEGMENT_WARN_RATIO = 0.6
USER_AGENT = "ContentAnySkill/1.0"
_SSL_CONTEXT: ssl.SSLContext | None = None


def ssl_context() -> ssl.SSLContext:
    """macOS 自带 Python 常常没有可用的 CA 包，补上系统证书后再校验。"""
    global _SSL_CONTEXT
    if _SSL_CONTEXT is not None:
        return _SSL_CONTEXT
    try:
        import certifi

        _SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
        return _SSL_CONTEXT
    except Exception:
        context = ssl.create_default_context()
        for path in ("/etc/ssl/cert.pem", "/private/etc/ssl/cert.pem"):
            if os.path.exists(path):
                try:
                    context.load_verify_locations(path)
                    break
                except ssl.SSLError:
                    continue
        _SSL_CONTEXT = context
        return context


class ContentAnyError(Exception):
    def __init__(self, error: str, message: str, code: int | None = None, next_step: str = ""):
        super().__init__(message)
        self.error = error
        self.message = message
        self.code = code
        self.next_step = next_step


class AuthExpired(ContentAnyError):
    def __init__(self, message: str = "登录已失效"):
        super().__init__("auth", message, 401, "将使用本机已保存的账号重新登录。")


class AccountRestricted(ContentAnyError):
    def __init__(self, message: str, code: int = 402):
        super().__init__(
            "restricted",
            message or "账号暂停使用或存在多处登录，请到官网联系客服。",
            code,
            f"请打开 {PRODUCT_URL} 联系客服。",
        )


def emit(payload: dict[str, Any], code: int = 0) -> None:
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    raise SystemExit(code)


def log(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def encode_uri_component(value: str) -> str:
    return quote(value, safe="-_.!~*'()")


def is_success(payload: dict[str, Any]) -> bool:
    return str(payload.get("code")) == "200"


def as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return int(value)
    if isinstance(value, str) and value.strip():
        try:
            return int(float(value.strip()))
        except ValueError:
            return None
    return None


def to_base36(number: int) -> str:
    alphabet = "0123456789abcdefghijklmnopqrstuvwxyz"
    if number <= 0:
        return "0"
    digits: list[str] = []
    while number:
        number, remainder = divmod(number, 36)
        digits.append(alphabet[remainder])
    return "".join(reversed(digits))


def new_identity() -> dict[str, str]:
    local = f"ca{to_base36(int(time.time() * 1000))}{secrets.token_hex(5)}"
    local = re.sub(r"[^a-z0-9]", "", local.lower())[:40]
    if len(local) < 6:
        local = f"ca{secrets.token_hex(8)}"
    alphabet = string.ascii_letters + string.digits
    return {
        "email": f"{local}@{EMAIL_DOMAIN}",
        "nick_name": local[:20],
        "password": "".join(secrets.choice(alphabet) for _ in range(20)),
    }


def is_name_conflict(message: str) -> bool:
    text = (message or "").lower()
    hints = ("已存在", "已注册", "已被占用", "已被使用", "重复", "exist", "duplicate", "occupied")
    return any(hint in text for hint in hints)


def is_rate_limited(message: str) -> bool:
    text = (message or "").lower()
    hints = ("操作过快", "人数过多", "排队", "过于频繁", "频繁", "too many", "rate limit")
    return any(hint in text for hint in hints)


def busy_or_quota(message: str, next_step: str) -> ContentAnyError:
    if is_rate_limited(message):
        return ContentAnyError(
            "network",
            message or "当前检测排队中，请稍后重试",
            403,
            "请等待约 20 秒后再检测一次，不要连续重试。",
        )
    return ContentAnyError("quota", message or "检测次数或权限不足", 403, next_step)


def session_path_from(raw: str | None) -> Path:
    if raw:
        return Path(raw).expanduser()
    env = os.environ.get("CONTENTANY_SESSION_PATH", "").strip()
    if env:
        return Path(env).expanduser()
    return SESSION_PATH


def empty_session() -> dict[str, Any]:
    return {
        "email": "",
        "password": "",
        "nick_name": "",
        "token": "",
        "device_id": str(uuid.uuid4()),
        "user_id": "",
        "created_at": "",
        "updated_at": "",
    }


def load_session(path: Path) -> dict[str, Any]:
    session = empty_session()
    if not path.exists():
        return session
    try:
        saved = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return session
    if isinstance(saved, dict):
        session.update({key: saved.get(key, session[key]) for key in session})
    if not session.get("device_id"):
        session["device_id"] = str(uuid.uuid4())
    return session


def save_session(path: Path, session: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.parent.chmod(0o700)
    except OSError:
        pass
    session["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(session, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        temp.chmod(0o600)
    except OSError:
        pass
    temp.replace(path)


def api_base_from(raw: str | None) -> str:
    base = (raw or os.environ.get("CONTENTANY_API_BASE") or DEFAULT_API_BASE).strip()
    return base.rstrip("/")


def parse_response_body(raw: bytes) -> dict[str, Any]:
    text = raw.decode("utf-8", errors="replace").strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ContentAnyError("api", f"接口没有返回 JSON：{text[:180]}") from exc
    if not isinstance(parsed, dict):
        raise ContentAnyError("api", "接口返回格式无法识别")
    return parsed


def request_json(
    api_base: str,
    path: str,
    *,
    token: str = "",
    json_body: Any = None,
    form: dict[str, str] | None = None,
    timeout: int = 90,
) -> dict[str, Any]:
    headers = {
        "Accept": "application/json",
        "language": "zh-cn",
        "User-Agent": USER_AGENT,
    }
    data: bytes | None = None
    if json_body is not None:
        data = json.dumps(json_body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    elif form is not None:
        body = "&".join(f"{key}={encode_uri_component(value)}" for key, value in form.items())
        data = body.encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    if token:
        headers["token"] = token
    request = Request(f"{api_base}{path}", data=data, headers=headers, method="POST")
    try:
        with urlopen(request, timeout=timeout, context=ssl_context()) as response:
            payload = parse_response_body(response.read())
            status = getattr(response, "status", 200)
    except HTTPError as exc:
        payload = parse_response_body(exc.read())
        status = exc.code
    except URLError as exc:
        raise ContentAnyError("network", f"无法连接 ContentAny：{exc.reason}") from exc
    except TimeoutError as exc:
        raise ContentAnyError("network", "ContentAny 接口超时，请稍后重试") from exc

    code = as_int(payload.get("code")) if payload else None
    message = str(payload.get("msg") or payload.get("message") or "")
    if status == 401 or code == 401:
        raise AuthExpired(message or "登录已失效")
    if status == 402 or code == 402:
        raise AccountRestricted(message, 402)
    if status >= 400 and not payload:
        raise ContentAnyError("api", f"接口请求失败（HTTP {status}）", status)
    return payload


def pick_token(payload: dict[str, Any]) -> str:
    for source in (payload, payload.get("data") if isinstance(payload.get("data"), dict) else {}):
        if not isinstance(source, dict):
            continue
        for key in ("token", "Token"):
            value = source.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return ""


def pick_user(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data")
    if isinstance(data, list) and data:
        data = data[0]
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            data = None
    if isinstance(data, dict) and isinstance(data.get("user"), dict):
        data = data["user"]
    return data if isinstance(data, dict) else {}


def apply_user(session: dict[str, Any], payload: dict[str, Any]) -> None:
    user = pick_user(payload)
    user_id = user.get("id") or user.get("userId") or user.get("user_id")
    if user_id:
        session["user_id"] = str(user_id)
    counts = {}
    for key in (
        "current_ai_detect_count",
        "current_deep_detect_count",
        "current_article_count",
        "current_chatgpt_output_count",
    ):
        number = as_int(user.get(key))
        if number is not None:
            counts[key] = number
    if counts:
        session["counts"] = counts


def login(api_base: str, session: dict[str, Any]) -> None:
    payload = request_json(
        api_base,
        "/v1/api/user/login",
        json_body={
            "email": session["email"],
            "password": session["password"],
            "device_id": session["device_id"],
        },
    )
    if not is_success(payload):
        message = str(payload.get("msg") or "登录失败")
        if is_name_conflict(message) or "密码" in message or "password" in message.lower():
            raise AuthExpired(message)
        raise ContentAnyError("auth", message, as_int(payload.get("code")))
    token = pick_token(payload)
    if not token:
        raise ContentAnyError("auth", "登录成功但没有返回 token")
    session["token"] = token
    apply_user(session, payload)


def register_account(api_base: str, session: dict[str, Any]) -> None:
    last_message = "注册失败"
    for _ in range(6):
        identity = new_identity()
        payload = request_json(
            api_base,
            "/v1/api/user/add",
            form={
                "email": identity["email"],
                "nick_name": identity["nick_name"],
                "password": identity["password"],
            },
        )
        if is_success(payload):
            session.update(identity)
            if not session.get("created_at"):
                session["created_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            token = pick_token(payload)
            if token:
                session["token"] = token
                apply_user(session, payload)
                return
            login(api_base, session)
            return
        last_message = str(payload.get("msg") or last_message)
        if is_name_conflict(last_message):
            continue
        raise ContentAnyError("auth", last_message, as_int(payload.get("code")))
    raise ContentAnyError("auth", f"连续多次邮箱重名，已停止注册：{last_message}")


def validate_token(api_base: str, session: dict[str, Any]) -> bool:
    payload = request_json(
        api_base,
        "/v1/api/user/get",
        token=session.get("token") or "",
        json_body={"device_id": session.get("device_id") or str(uuid.uuid4())},
    )
    if is_success(payload):
        apply_user(session, payload)
        return True
    code = as_int(payload.get("code"))
    if code in (401, None):
        return False
    return False


def ensure_session(api_base: str, path: Path, *, force_new: bool = False) -> tuple[dict[str, Any], bool]:
    session = load_session(path)
    created = False
    if not force_new and session.get("token"):
        try:
            if validate_token(api_base, session):
                save_session(path, session)
                return session, False
        except AuthExpired:
            session["token"] = ""
        except AccountRestricted:
            raise
        except ContentAnyError:
            raise
    if not force_new and session.get("email") and session.get("password"):
        try:
            login(api_base, session)
            save_session(path, session)
            return session, False
        except AuthExpired:
            session["token"] = ""
        except AccountRestricted:
            raise
    register_account(api_base, session)
    created = True
    save_session(path, session)
    return session, created


def is_chinese(text: str) -> bool:
    return re.search(r"[\u4e00-\u9fff]", text) is not None


def character_count(text: str) -> int:
    if is_chinese(text):
        return len(text)
    return len([part for part in re.split(r"\s+", text) if part])


def normalize_breaks(text: str) -> str:
    value = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"<br\s*/?>|</br>", "\n", value, flags=re.IGNORECASE)


def split_and_preserve(text: str) -> list[str]:
    sentences: list[str] = []
    temp = ""
    punctuations = set("。！？.!?")
    for index, char in enumerate(text):
        temp += char
        nxt = text[index + 1] if index + 1 < len(text) else ""
        prv = text[index - 1] if index > 0 else ""
        if char in punctuations and not (
            re.match(r"[0-9.]", nxt or " ") or re.match(r"[0-9.]", prv or " ")
        ):
            sentences.append(temp)
            temp = ""
    if temp:
        sentences.append(temp)
    return sentences


def split_by_clause_separators(text: str) -> list[str]:
    parts: list[str] = []
    temp = ""
    for index, char in enumerate(text):
        temp += char
        prv = text[index - 1] if index > 0 else ""
        nxt = text[index + 1] if index + 1 < len(text) else ""
        is_ascii_comma = char == "," and not (prv.isdigit() and nxt.isdigit())
        if char in "，；" or is_ascii_comma:
            parts.append(temp)
            temp = ""
    if temp:
        parts.append(temp)
    return parts


def merge_parts_to_char_range(parts: list[str], min_chars: int, max_chars: int) -> list[str]:
    trimmed = [part.strip() for part in parts if part and part.strip()]
    if not trimmed:
        return []
    chunks: list[str] = []
    buf = trimmed[0]
    for piece in trimmed[1:]:
        if character_count(buf + piece) <= max_chars:
            buf += piece
        else:
            chunks.append(buf)
            buf = piece
    chunks.append(buf)
    merged: list[str] = []
    for current in chunks:
        if (
            merged
            and character_count(current) < min_chars
            and character_count(merged[-1] + current) <= max_chars
        ):
            merged[-1] = merged[-1] + current
        else:
            merged.append(current)
    return merged


def subdivide_for_cap(chunk: str, cap: int) -> list[str]:
    if not chunk:
        return []
    if len(chunk) <= cap:
        return [chunk]
    sentences = [item for item in split_and_preserve(chunk) if item.strip()]
    if not sentences:
        return [chunk[index : index + cap] for index in range(0, len(chunk), cap)]
    out: list[str] = []
    buf = ""

    def flush() -> None:
        nonlocal buf
        if buf:
            out.append(buf)
            buf = ""

    for sentence in sentences:
        if len(sentence) > cap:
            flush()
            out.extend(sentence[index : index + cap] for index in range(0, len(sentence), cap))
            continue
        if not buf:
            buf = sentence
        elif len(buf) + len(sentence) <= cap:
            buf += sentence
        else:
            flush()
            buf = sentence
    flush()
    return out


def build_sentence_list(text: str) -> list[str]:
    old_value = normalize_breaks(text)
    line_threshold = 150
    lines = [line for line in re.split(r"\r?\n|\r", old_value) if line.strip()]
    primary: list[str] = []
    clause_max = min(220, max(line_threshold + 20, 180))
    clause_min = min(32, max(24, line_threshold // 5))
    for line in lines:
        if character_count(line) > line_threshold:
            for segment in split_and_preserve(line):
                seg = segment.strip()
                if not seg:
                    continue
                if len(seg) > line_threshold:
                    pieces = split_by_clause_separators(seg)
                    primary.extend(
                        item
                        for item in merge_parts_to_char_range(pieces, clause_min, clause_max)
                        if item.strip()
                    )
                else:
                    primary.append(segment)
        else:
            primary.append(line)
    stage = primary
    if not stage and old_value.strip():
        stage = lines or [old_value]
    result: list[str] = []
    for segment in stage:
        if segment.strip():
            result.extend(subdivide_for_cap(segment, AI_CHECK_MODEL_UNICODE_CAP))
    return [item for item in result if item.strip()]


def split_into_paragraphs_like_backend(text: str) -> list[str]:
    normalized = normalize_breaks(text)
    if not normalized.strip():
        return []
    parts = re.split(r"([。！？\n])", normalized)
    paragraphs: list[str] = []
    current = ""
    for part in parts:
        if not part or not part.strip():
            continue
        current += part
        if part in "。！？\n":
            if current.strip():
                paragraphs.append(current.strip())
            current = ""
    if current.strip():
        paragraphs.append(current.strip())
    return paragraphs


def short_segment_stats(sentence_list: list[str], min_word_count: int) -> dict[str, float]:
    valid = [item.strip() for item in sentence_list if item and item.strip()]
    total = len(valid)
    if not total:
        return {"total": 0, "short_count": 0, "short_ratio": 0}
    short_count = sum(1 for item in valid if character_count(item) <= min_word_count)
    return {"total": total, "short_count": short_count, "short_ratio": short_count / total}


def merge_short_segments(
    sentence_list: list[str],
    min_word_count: int,
    target_min_chars: int = 60,
    max_merged_chars: int = 220,
) -> list[str]:
    valid = [item.strip() for item in sentence_list if item and item.strip()]
    merged: list[str] = []
    short_buf = ""

    def push_buf() -> None:
        nonlocal short_buf
        if short_buf:
            merged.append(short_buf)
            short_buf = ""

    for segment in valid:
        is_short = character_count(segment) <= min_word_count
        if is_short:
            if not short_buf:
                short_buf = segment
            elif character_count(short_buf + "\n" + segment) <= max_merged_chars:
                short_buf += "\n" + segment
            else:
                push_buf()
                short_buf = segment
            if character_count(short_buf) >= target_min_chars:
                push_buf()
            continue
        if short_buf:
            if (
                character_count(short_buf) < target_min_chars
                and character_count(short_buf + "\n" + segment) <= max_merged_chars
            ):
                merged.append(short_buf + "\n" + segment)
                short_buf = ""
                continue
            push_buf()
        merged.append(segment)
    if short_buf:
        if (
            merged
            and character_count(short_buf) < target_min_chars
            and character_count(merged[-1] + "\n" + short_buf) <= max_merged_chars
        ):
            merged[-1] = merged[-1] + "\n" + short_buf
        else:
            merged.append(short_buf)
    return [item for item in merged if item.strip()]


def parse_check_ai_word(raw: Any) -> dict[str, Any]:
    if raw is None or raw == "":
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw or "{}")
        except json.JSONDecodeError:
            return {}
        if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
            return parsed[0]
        if isinstance(parsed, dict):
            return parsed
    return {}


def segment_from_word(order: int, content: str, word: dict[str, Any], *, fallback: bool = False) -> dict[str, Any]:
    is_ai_number = as_int(word.get("isAi"))
    is_ai = is_ai_number == 1
    person = word.get("personScore")
    bot = word.get("aiBotScore")
    person_number = person if isinstance(person, (int, float)) and not isinstance(person, bool) else None
    bot_number = bot if isinstance(bot, (int, float)) and not isinstance(bot, bool) else None
    if person_number is not None and bot_number is not None:
        total = person_number + bot_number
        ai_percent = round(bot_number / total * 100) if total else (50 if is_ai else 0)
    else:
        ai_percent = 50 if is_ai else 0
    return {
        "order": order,
        "text": content,
        "type": "ai" if is_ai else "human",
        "label": "疑似AI" if is_ai else "人工",
        "ai_percent": ai_percent,
        "is_ai": 1 if is_ai else 0,
        "person_score": person_number,
        "ai_bot_score": bot_number,
        "fallback": fallback,
    }


def build_evaluation(segments: list[dict[str, Any]], min_word_count: int) -> dict[str, Any]:
    valid = [item for item in segments if len(item.get("text") or "") > min_word_count]
    base = valid or segments
    total = len(base)
    ai_count = sum(1 for item in base if item.get("type") == "ai")
    ai_percent = round(ai_count / total * 100) if total else 0
    full_text_ai = round(ai_count / total * 10000) / 100 if total else 0
    deep_status = "模型参考：约 80% 概率偏人工" if ai_percent < 20 else f"AIGC 段落占比约 {ai_percent}%"
    return {
        "ai_percent": ai_percent,
        "full_text_ai": full_text_ai,
        "ai_segments": ai_count,
        "total_segments": len(segments),
        "valid_segments": len(valid) or len(segments),
        "deep_status": deep_status,
    }


def extract_report(payload: dict[str, Any]) -> str:
    data = payload.get("data")
    if isinstance(data, dict) and isinstance(data.get("data"), str):
        return data["data"]
    if isinstance(data, str):
        return data
    return ""


def read_input_text(args: argparse.Namespace) -> str:
    if args.text and args.file:
        raise ContentAnyError("input", "请只使用 --text 或 --file 其中一种")
    if args.text:
        return args.text
    if args.file:
        if args.file == "-":
            return sys.stdin.read()
        return Path(args.file).expanduser().read_text(encoding="utf-8")
    raise ContentAnyError("input", "请用 --text 或 --file 提供待检测正文")


def post_detect(
    api_base: str,
    session_file: Path,
    session: dict[str, Any],
    explicit_token: str,
    api_path: str,
    *,
    json_body: Any = None,
    form: dict[str, str] | None = None,
) -> dict[str, Any]:
    token = explicit_token or session.get("token") or ""
    try:
        return request_json(api_base, api_path, token=token, json_body=json_body, form=form)
    except AuthExpired:
        if explicit_token or not session.get("password"):
            raise ContentAnyError(
                "auth",
                f"token 已失效。请到 {PRODUCT_URL} 重新获取，或去掉自定义 token 后重试。",
                401,
            )
        log("token 已失效，正在用本机账号重新登录")
        login(api_base, session)
        save_session(session_file, session)
        return request_json(
            api_base,
            api_path,
            token=session.get("token") or "",
            json_body=json_body,
            form=form,
        )


def run_detect(args: argparse.Namespace) -> dict[str, Any]:
    text = read_input_text(args).strip()
    if not text:
        raise ContentAnyError("input", "待检测内容是空的")
    if len(text) > 1_500_000:
        raise ContentAnyError("input", "正文超过 150 万字，请拆开后再检测")

    api_base = api_base_from(args.api_base)
    session_file = session_path_from(args.session)
    explicit_token = (args.token or os.environ.get("CONTENTANY_TOKEN") or "").strip()
    if explicit_token:
        session = load_session(session_file)
        log("使用本次提供的 token 进行小红书笔记检测")
        created = False
    else:
        log("正在准备小红书笔记检测")
        session, created = ensure_session(api_base, session_file, force_new=args.force_new_account)

    log("正在校验账号与检测额度")
    account_res = post_detect(
        api_base,
        session_file,
        session,
        explicit_token,
        "/v1/api/CheckUserAccount",
        form={"content": text},
    )
    if not is_success(account_res):
        code = as_int(account_res.get("code")) or 500
        message = str(account_res.get("msg") or "检测次数或权限不足")
        if code == 403:
            raise busy_or_quota(
                message,
                f"本机技能账号的 AI 检测额度已用完。请到 {PRODUCT_URL} 登录自己的账号继续检测。",
            )
        raise ContentAnyError("api", message, code)

    message = str(account_res.get("msg") or "").strip()
    data = account_res.get("data") if isinstance(account_res.get("data"), dict) else {}
    document_id = message or str(data.get("document_id") or "")
    if not document_id:
        raise ContentAnyError("api", "账号校验没有返回文档 ID")
    max_work = max(1, as_int(data.get("max_work")) or 1)
    min_word_count = max(4, as_int(data.get("min_word_count")) or 20)
    default_word = parse_check_ai_word(data.get("checkAiWord"))

    sentence_list = build_sentence_list(text)
    if not sentence_list:
        raise ContentAnyError("input", "有效内容过少，请增加内容后重试")

    paragraphs = split_into_paragraphs_like_backend(text)
    stats = short_segment_stats(paragraphs, BACKEND_SHORT_SEGMENT_THRESHOLD)
    short_note = ""
    merged = False
    if stats["total"] and stats["short_ratio"] >= BACKEND_SHORT_SEGMENT_WARN_RATIO:
        short_note = (
            f"短排版较多（{int(stats['short_count'])}/{int(stats['total'])} 段不超过 "
            f"{BACKEND_SHORT_SEGMENT_THRESHOLD} 字，约 {round(stats['short_ratio'] * 100)}%），可能影响准确度。"
        )
        if not args.keep_short:
            sentence_list = merge_short_segments(sentence_list, min_word_count)
            merged = True
            short_note += " 已按官网的「一键合并短段并检测」处理后再检测。"
        else:
            short_note += " 已按原文短段检测。"

    segments: dict[int, dict[str, Any]] = {}
    key = 0
    total = len(sentence_list)
    while key < total:
        params: list[dict[str, Any]] = []
        index = key
        while index < total and len(params) < max_work:
            content = sentence_list[index]
            if character_count(content) > min_word_count:
                params.append(
                    {
                        "document_id": document_id,
                        "order_number": index,
                        "content": content,
                        "checkAiWord": "",
                    }
                )
            else:
                segments[index] = segment_from_word(index, content, default_word)
                segments[index]["skipped_short"] = True
            key = index + 1
            index += 1
        if not params:
            break
        log(f"正在检测分段 {min(key, total)}/{total}")
        try:
            result = post_detect(
                api_base,
                session_file,
                session,
                explicit_token,
                "/v1/api/rewrite/checkAiWord",
                json_body=params,
            )
        except ContentAnyError as exc:
            if exc.error in {"quota", "restricted", "auth"}:
                raise
            result = {"code": 500, "msg": exc.message}
        code = as_int(result.get("code")) or 500
        if code == 403:
            raise busy_or_quota(
                str(result.get("msg") or "权限或额度不足"),
                f"请到 {PRODUCT_URL} 使用自己的账号。",
            )
        rows = result.get("data") if code == 200 and isinstance(result.get("data"), list) else []
        matched: set[int] = set()
        for row in rows:
            if not isinstance(row, dict):
                continue
            order = as_int(row.get("order_number"))
            if order is None:
                continue
            content = row.get("content") if isinstance(row.get("content"), str) else ""
            if not content:
                content = next((item["content"] for item in params if item["order_number"] == order), "")
            segments[order] = segment_from_word(order, content, parse_check_ai_word(row.get("checkAiWord")))
            matched.add(order)
        if code != 200 or len(matched) != len(params):
            for item in params:
                if item["order_number"] not in matched:
                    fallback = segment_from_word(
                        item["order_number"],
                        item["content"],
                        default_word,
                        fallback=True,
                    )
                    segments[item["order_number"]] = fallback

    ordered = [segments[index] for index in range(total) if index in segments]
    for item in ordered:
        item.pop("skipped_short", None)
    log("正在生成内容质量报告")
    joined = "\r\n".join(item["text"] for item in ordered)
    report = ""
    report_error = ""
    try:
        report_res = post_detect(
            api_base,
            session_file,
            session,
            explicit_token,
            "/v1/api/contentcheckforindex",
            form={"content": joined, "type": "1"},
        )
        if is_success(report_res):
            report = extract_report(report_res)
        else:
            report_error = str(report_res.get("msg") or "内容质量报告没有返回")
    except ContentAnyError as exc:
        if exc.error in {"quota", "restricted", "auth"}:
            raise
        report_error = exc.message

    return {
        "ok": True,
        "account_created": created,
        "document_id": document_id,
        "word_count": len(re.sub(r"\s+", "", text)),
        "min_word_count": min_word_count,
        "short_layout": {"warned": bool(short_note), "merged": merged, "message": short_note},
        "summary": build_evaluation(ordered, min_word_count),
        "segments": ordered,
        "report_markdown": report,
        "report_error": report_error,
        "counts": session.get("counts") or {},
    }


def run_self_check() -> dict[str, Any]:
    seen: set[str] = set()
    for _ in range(300):
        identity = new_identity()
        email = identity["email"]
        if not email.endswith(f"@{EMAIL_DOMAIN}"):
            raise AssertionError(email)
        local, _, domain = email.partition("@")
        if domain != EMAIL_DOMAIN or not re.fullmatch(r"[a-z0-9]{6,40}", local):
            raise AssertionError(email)
        if not 2 <= len(identity["nick_name"]) <= 20:
            raise AssertionError(identity["nick_name"])
        if len(identity["password"]) < 6:
            raise AssertionError("password too short")
        if email in seen:
            raise AssertionError(f"duplicate email {email}")
        seen.add(email)
    sample = "这是第一句。这是第二句！3.14是小数，不应该从点号切开。"
    pieces = split_and_preserve(sample)
    if any(piece == "3" for piece in pieces):
        raise AssertionError(pieces)
    long_text = "，".join([f"第{i}个从句内容用来测试长段切分" for i in range(80)])
    chunks = build_sentence_list(long_text)
    if not chunks or any(len(chunk) > AI_CHECK_MODEL_UNICODE_CAP for chunk in chunks):
        raise AssertionError("long text was not capped")
    return {"ok": True, "checked": "split, cap", "sample_chunks": len(chunks)}


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--api-base", default="", help="默认 https://cn.aifoxs.com")
    common.add_argument("--session", default="", help="token 保存路径，默认 ~/.contentany/ai-detect-session.json")

    parser = argparse.ArgumentParser(description="小红书封面和AI检测工具")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("self-check", parents=[common], help="检查邮箱生成和分段，不访问网络")
    ensure = sub.add_parser("ensure-session", parents=[common], help="准备 AI 检测")
    ensure.add_argument("--force-new-account", action="store_true")
    who = sub.add_parser("whoami", parents=[common], help="查看检测额度，不输出密码和 token")
    who.add_argument("--force-new-account", action="store_true")

    detect_parser = sub.add_parser("detect", parents=[common], help="执行小红书笔记 AI 率检测和内容质量报告")
    detect_parser.add_argument("--text", default="")
    detect_parser.add_argument("--file", default="")
    detect_parser.add_argument("--token", default="", help="本次使用官网申请的 token，不写入本机会话")
    detect_parser.add_argument("--keep-short", action="store_true", help="短段过多时不合并")
    detect_parser.add_argument("--force-new-account", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "self-check":
            emit(run_self_check())
        if args.command == "ensure-session":
            api_base = api_base_from(args.api_base)
            path = session_path_from(args.session)
            session, _created = ensure_session(api_base, path, force_new=args.force_new_account)
            emit(
                {
                    "ok": True,
                    "ready": bool(session.get("token")),
                }
            )
        if args.command == "whoami":
            api_base = api_base_from(args.api_base)
            path = session_path_from(args.session)
            session, _created = ensure_session(api_base, path, force_new=args.force_new_account)
            emit(
                {
                    "ok": True,
                    "ready": bool(session.get("token")),
                    "counts": session.get("counts") or {},
                }
            )
        if args.command == "detect":
            emit(run_detect(args))
        parser.error(f"未知命令 {args.command}")
    except ContentAnyError as exc:
        emit(
            {
                "ok": False,
                "error": exc.error,
                "code": exc.code,
                "message": exc.message,
                "next": exc.next_step,
            },
            1,
        )
    except OSError as exc:
        emit({"ok": False, "error": "input", "message": str(exc), "next": ""}, 2)


if __name__ == "__main__":
    main()
