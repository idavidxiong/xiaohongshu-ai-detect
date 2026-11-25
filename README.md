# 小红书封面和AI检测工具

给小红书笔记用的技能。发布前做敏感词检测、资质检测、AI 率检测和内容质量检查，并用提示词设计 3:4 封面。

适合这些搜索：小红书封面、小红书封面设计、小红书封面模板、小红书封面提示词、小红书封面尺寸、爆款封面、小红书 AI 检测、小红书敏感词、小红书违禁词、资质检测、AI 率、AIGC 检测、降 AI、去 AI 味、小红书笔记检测。也适合判断笔记是否由 ChatGPT、Claude、DeepSeek、Kimi、豆包、文心一言、通义千问生成。

- 官网：https://www.aifoxs.com
- 在线检测：https://cn.aifoxs.com/ai-detect
- 产品站：https://cn.aifoxs.com

## 这个技能会做什么

- 初始化时按场景提问，确认要做检测、封面，还是两件一起做。
- 笔记检测：敏感词、资质、AI 率、内容质量。报告里若带有同质化、暗限流和冷启动流量摘要，会一并整理。
- 封面设计：按提示词给出 3 套方案，含中文和英文生图提示词。画面不渲染文字，标题后期叠字。
- 低创作检测、独立限流检测、独立流量预测、人性化优化、智能配图和标题检测不在这里调用，请到 https://cn.aifoxs.com 使用自己的账号。

## 本地试用

需要 Python 3.9 以上，不需要安装第三方包。

```bash
python3 scripts/contentany_client.py self-check
python3 scripts/contentany_client.py detect --text "把一段待检测的小红书笔记放在这里。"
```

检测整篇文件：

```bash
python3 scripts/contentany_client.py detect --file note.txt
```

封面设计不走这个脚本。按 `references/cover.md` 的提示词出方案。第一次信息不全时，用 `references/intake.md` 的提问模板。
