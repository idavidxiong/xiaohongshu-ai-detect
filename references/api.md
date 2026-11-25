# 小红书笔记检测接口

默认站点根：`https://cn.aifoxs.com`

产品站和接口使用同一个域名。可用环境变量 `CONTENTANY_API_BASE` 或参数 `--api-base` 覆盖。不要在根地址后面再加 `/api` 或 `/v1/api`。

所有请求都带 `language: zh-cn`。需要登录的请求再带 `token` 头。

登录态由检测脚本维护。不要在对话里展示 token、密码或邮箱。

## 检测三步

1. `POST /v1/api/CheckUserAccount`

   表单只有 `content`。成功时文档 ID 优先取 `msg`，否则取 `data.document_id`。`data.max_work` 是每批提交条数，`data.min_word_count` 是短段阈值。

2. `POST /v1/api/rewrite/checkAiWord`

   JSON 数组。每一项包含 `document_id`、`order_number`、`content`、`checkAiWord`。只提交长于 `min_word_count` 的段落，每批不超过 `max_work`。`checkAiWord.isAi === 1` 记为疑似 AI。段落 AI 比例 = `aiBotScore / (personScore + aiBotScore)`。

3. `POST /v1/api/contentcheckforindex`

   表单 `content` 是各段用 `\r\n` 拼回的正文，`type=1`。报告正文在 `data.data`。正文大约不足 500 字时，接口会返回「字数低于500字，不做任何检测操作」，这时分段 AI 结果仍然有效。

分段和产品站一致：先按换行，超过约 150 字再按句号切开；仍超长则按逗号切分；最后把每段压到 400 个字符以内，避免检测模型截断。按 `。！？` 和换行统计，不超过 25 字的段落达到六成时，默认合并短段后再检测。

## 业务码

| code | 含义 | 技能行为 |
| --- | --- | --- |
| 200 | 成功 | 继续 |
| 401 | token 失效 | 重试这一次请求；仍然失败就停止并说明原因 |
| 402 | 账号受限或异地登录冲突 | 停止，请用户到 https://cn.aifoxs.com 联系客服 |
| 403 | 额度或会员不足；若文案是操作过快、排队，则只是临时繁忙 | 额度不足时停止并引导到 https://cn.aifoxs.com ；排队时等待约 20 秒再试一次 |
| 500 | 单批检测失败 | 该批使用账号校验返回的默认结果，并标记 `fallback` |

低创作检测的 `/v1/api/low-creativity-detect`、深度流量预测的 `/v1/api/CheckDeepDetectionAccount` 和改写接口，都不由这个脚本调用。

敏感词、违禁词、资质和内容质量没有单独的接口，都看第 3 步 `contentcheckforindex` 的报告正文。资质看「资质提醒」。敏感词只在「敏感和违规检测」写出具体词或明确结论时才算有结果；如果这几段只是「请使用内容评估和流量预测模块」，就告诉用户这次没有展开，不要另找接口补，也不要编造词条。

封面设计不走这里的任何路径。方案和生图提示词按 `references/cover.md` 在对话里完成。
