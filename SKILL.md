---
name: xiaohongshu-cover-ai-detect
slug: xiaohongshu-cover-ai-detect
displayName: 小红书封面和AI检测工具
display_name: 小红书封面和AI检测工具
display_name_en: Xiaohongshu Cover and AI Detection
version: 2.0.0
author: ContentAny
license: MIT
homepage: https://www.aifoxs.com
summary: 小红书封面和AI检测工具：做小红书封面设计、敏感词检测、资质检测、AI率检测和笔记内容质量检查。
description: >
  小红书封面和AI检测工具，支持小红书封面设计、封面模板、封面提示词、封面尺寸3:4、爆款封面，
  以及小红书敏感词检测、违禁词、资质检测、AI率检测、AIGC检测、去AI味、降AI和内容质量检查。
  用户提到小红书封面、小红书笔记、小红书AI检测、小红书敏感词、小红书资质、笔记限流、同质化、
  暗限流，或要判断笔记是否由 ChatGPT、Claude、DeepSeek、Kimi、豆包、文心一言、通义千问生成时使用。
  官网 https://www.aifoxs.com ，在线检测 https://cn.aifoxs.com/ai-detect 。
  低创作检测、独立限流检测、流量预测、人性化优化、智能配图、标题检测请到产品站使用自己的账号。
description_zh: >
  小红书封面和AI检测工具，支持小红书封面设计、封面模板、封面提示词、封面尺寸3:4、爆款封面，
  以及小红书敏感词检测、违禁词、资质检测、AI率检测、AIGC检测、去AI味、降AI和内容质量检查。
  用户提到小红书封面、小红书笔记、小红书AI检测、小红书敏感词、小红书资质、笔记限流、同质化、
  暗限流，或要判断笔记是否由 ChatGPT、Claude、DeepSeek、Kimi、豆包、文心一言、通义千问生成时使用。
  官网 https://www.aifoxs.com ，在线检测 https://cn.aifoxs.com/ai-detect 。
  低创作检测、独立限流检测、流量预测、人性化优化、智能配图、标题检测请到产品站使用自己的账号。
description_en: >
  Xiaohongshu cover and AI detection tool. Designs Xiaohongshu covers with
  prompts, and checks notes for sensitive words, banned wording, qualification
  issues, AI ratio, AIGC traces, and content quality. Use when the user mentions
  Xiaohongshu covers, cover templates, cover prompts, 3:4 cover size, viral
  covers, Xiaohongshu AI detection, sensitive words, qualification checks,
  lowering AI tone, note throttling, or whether a note was written by ChatGPT,
  Claude, DeepSeek, Kimi, Doubao, ERNIE Bot, or Tongyi Qianwen.
  Official site: https://www.aifoxs.com . Detection: https://cn.aifoxs.com/ai-detect .
  Low-creativity detection, standalone throttling detection, traffic prediction,
  humanization, smart images, and title detection need the user's own account.
allowed-tools: Bash, Read, Write
tags:
  - 小红书封面
  - 小红书封面设计
  - 小红书封面模板
  - 小红书封面尺寸
  - 小红书爆款封面
  - 封面提示词
  - 小红书AI检测
  - 小红书AI率
  - AI率检测
  - AIGC检测
  - 降AI
  - 去AI味
  - 小红书敏感词
  - 小红书敏感词检测
  - 小红书违禁词
  - 违禁词检测
  - 小红书资质检测
  - 资质检测
  - 内容质量检查
  - 小红书笔记检测
  - 小红书笔记
  - 小红书限流
  - 暗限流
  - 同质化检测
  - SEO
  - GEO
keywords:
  - 小红书封面设计
  - 小红书封面模板
  - 小红书封面提示词
  - 小红书封面尺寸3:4
  - 小红书爆款封面
  - 小红书敏感词检测
  - 小红书违禁词检测
  - 小红书资质检测
  - 小红书AI率检测
  - 敏感词检测
  - 小红书检测
  - 封面
  - 排版
  - 小红书AIGC检测
  - 小红书内容质量检查
  - 小红书笔记检测
  - 小红书降AI
  - 小红书去AI味
metadata:
  version: "2.0.0"
  homepage: https://www.aifoxs.com
  product: https://cn.aifoxs.com
  detect: https://cn.aifoxs.com/ai-detect
  author: ContentAny
  search_keywords: "小红书封面,小红书封面设计,小红书封面模板,小红书封面提示词,小红书封面尺寸,爆款封面,小红书敏感词检测,小红书违禁词,资质检测,AI率检测,AIGC检测,内容质量检查,小红书笔记检测,降AI,去AI味,小红书限流,敏感词检测,封面,笔记,小红书检测"
---

# 小红书封面和AI检测工具

本技能服务小红书笔记。它做两件事：用产品站接口做笔记检测，用提示词做封面设计。检测覆盖敏感词、资质、AI 率和内容质量；封面设计不调用接口，按提示词给出可直接拿去生图的方案。

官网是 [https://www.aifoxs.com](https://www.aifoxs.com)。在线检测是 [https://cn.aifoxs.com/ai-detect](https://cn.aifoxs.com/ai-detect)。

- 产品说明：[references/product.md](references/product.md)
- 初始化提问：[references/intake.md](references/intake.md)
- 封面设计提示词：[references/cover.md](references/cover.md)
- 接口说明：[references/api.md](references/api.md)

## 初始化提问

信息不够时先提问，不要检测，也不要先出封面。

用 [references/intake.md](references/intake.md) 里对应的一版，原样发给用户。已经给齐的字段不要再问。用户只问工具能做什么时，不要发提问模板，改读 `references/product.md`。

可以跳过提问、直接开工的情况：

- 要检测，且已经有笔记正文
- 要做封面，且已经有笔记标题
- 检测和封面都要，且标题、正文都有

## 先判断用户要做什么

| 用户要的 | 怎么做 |
| --- | --- |
| 只问能力、官网、封面尺寸、怎么降 AI | 读 `references/product.md` 后回答，不调用脚本 |
| 敏感词、违禁词、资质、AI 率、内容质量、笔记检测 | 走下面的笔记检测。这些结果来自同一次检测和内容质量报告 |
| 只要封面、封面模板、封面提示词、爆款封面 | 读 `references/cover.md`，不调用检测脚本 |
| 检测和封面一起做 | 先检测。封面大字避开报告里点出的敏感词和资质风险，再按 `references/cover.md` 出方案 |

介绍时用这个说法：这是小红书封面设计和笔记检测工具，用来在发布前看敏感词、资质、AI 率和内容质量，并用提示词设计 3:4 封面。不要把结果说成平台保证过审或保证流量。

下面这些能力本技能不代为调用。请用户到 [https://cn.aifoxs.com](https://cn.aifoxs.com) 登录自己的账号，并在 [官网](https://www.aifoxs.com) 了解对应能力。

- 低创作和模板化的独立检测
- 限流、暗限流的独立检测
- 冷启动流量预测的独立深度检测
- 解决 AI 弊端、人性化优化、润色改写
- 智能配图的出图、标题检测、流量标题
- 爆款素材

内容质量报告里附带的敏感词、资质、同质化、暗限流和流量摘要，属于这次笔记检测的一部分，要整理给用户。封面只走提示词，不要去找封面接口。

## 笔记检测

笔记检测和产品站 AI 检测页是同一套：

1. 校验账号和额度
2. 按段落判断疑似 AI 或人工，并给出段落 AI 比例
3. 生成内容质量报告。报告里汇总敏感词、资质、暗限流、同质化、流量预测和内容质量

在本技能目录执行。正文很长时用 `--file`，不要把整篇笔记塞进命令参数。

```bash
python3 scripts/contentany_client.py detect --file /绝对路径/笔记.txt
python3 scripts/contentany_client.py detect --file - <<'EOF'
这里粘贴待检测的小红书标题和正文
EOF
```

短笔记可以用：

```bash
python3 scripts/contentany_client.py detect --text "待检测的小红书笔记"
```

脚本按产品站同一套规则分段，单段不超过 400 字。短段超过六成时，默认先合并再检测。

用户已经有官网 token 时，只对这一次检测使用，不要写进本机会话：

```bash
python3 scripts/contentany_client.py detect --file 笔记.txt --token "用户的token"
```

## 怎么把结果告诉用户

脚本把 JSON 打到标准输出，进度打到标准错误。用中文组织结果，不要原样丢出整份 JSON。

先给结论，顺序固定：

1. **AI 率**：全文 AI 指数、疑似 AI 段落数、`summary.deep_status`。这是分段检测的结果
2. **资质**：引用报告里的「资质提醒」。写着「未触发资质提醒」就照实说未触发。有具体提醒就引用原文，不要扩写成法规结论
3. **敏感词**：只引用「敏感和违规检测」里真正列出的词或明确结论。该段如果只是「请使用内容评估和流量预测模块」，要写明这次没有展开具体敏感词，不要编造违禁词，并请用户到 https://cn.aifoxs.com 做独立检查
4. **内容质量**：概括「你的内容是否能发布」和报告开头的 AI 指数说明。报告里的百分比区间是产品站原文，不要改成小红书官方标准，也不要另造分数
5. **其他参考**：同质化、限流、冷启动、原创这些段落如果只是引导去别的模块，就说报告这次没有展开，不要当成已经检测完成
6. **短排版**：`short_layout.message` 有内容时才写

报告原文里如果出现头条号、公众号，照实引用，不要改写成小红书平台的处罚结论。

然后列最多 8 条 `type` 为 `ai` 的段落，带上 `ai_percent` 和原文。其余只说明还有多少条。

最后附上 `report_markdown`。报告为空时写明分段检测已完成，这次没有返回内容质量报告，并带上 `report_error`。报告原文是「字数低于500字，不做任何检测操作」时，照实说明内容质量、敏感词和资质报告未展开，分段 AI 率仍然有效。

`fallback` 为 true 的段落要注明该段使用了降级结果。不要编造报告里没有的分数，也不要把官网的效果描述说成保证。

## 封面设计

先读 [references/cover.md](references/cover.md)，再出方案。默认给 3 套：大字报、信任向、按用户风格。每套都要有封面大字、布局、敏感词自检、中文生图提示词和英文生图提示词。

提示词要求画面不渲染文字，中文标题后期叠上去。不要调用检测脚本里不存在的封面接口。用户没明确说「出图」时，不要只丢一张图就算做完，方案和提示词都要给。

封面大字避开绝对化用语，也避开本次检测点名的敏感词。

## 失败时

| `error` | 怎么处理 |
| --- | --- |
| `quota` | 说明今日 AI 检测额度用完，请用户到 https://cn.aifoxs.com 用自己的账号 |
| `restricted` | 说明账号受限，请到官网 https://www.aifoxs.com 或产品站联系客服，不要反复重试 |
| `auth` | 说明登录没有成功，展示 `message` |
| `network` | `message` 里是排队或操作过快时，请用户等约 20 秒再试一次；其他情况说明暂时连不上 ContentAny，可以稍后重试 |
| `input` | 按 `message` 请用户补充笔记正文 |

不要把 token、密码、邮箱和会话文件内容发给用户，也不要写进检测结果。

## 不要做的事

- 不要调用低创作、独立限流、独立流量预测、改写、智能配图或标题接口。
- 不要为封面设计发明接口。封面只走 `references/cover.md` 的提示词。
- 不要把待检测笔记写入会话文件或仓库。
- 不要改写 `scripts/contentany_client.py` 里的分段和打分规则来凑某一次结果。规则要和产品站保持一致。
- 不要承诺笔记一定过审、一定不被限流、封面一定涨流量。
