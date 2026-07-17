# STAR_NARRATIVE — 面试口述稿

## S — Situation

微服务排障时，值班要在多服务日志里手工关联 trace / error，耗时长、MTTR 高。缺的是「告警进、带证据的根因报告出」的专用 Agent；通用聊天助手接不上日志工具链，也容易幻觉。

## T — Task

我交付了 MVP：基于 MCP 兼容工具协议的日志根因定位 Agent。用户输入告警后，Agent 多步调工具，输出根因、影响范围与修复建议；本地可一键跑、可公开源码、国内可访问 Demo；推理用 DeepSeek `deepseek-chat`；不做微调、不做客服。

## A — Action

1. **DeepSeek**：国内直连、OpenAI-compatible、中文排障成本可控。
2. **ReAct + MCP 工具白名单**（list_services / query_logs / get_trace_logs / aggregate_errors）+ max_steps/超时，避免跑飞。
3. **自研改进**：结构化日志摘要降 observation 体积；L1/L2 缓存降重复工具调用；用评测脚本量化。
4. **可观测**：OpenTelemetry console span 覆盖 RCA 与工具调用。
5. **SDD**：文档黑名单 + TODO 通关，防止做成问答助手。
6. **Demo**：优先免费 Cloudflare Tunnel / Sealos，避开需翻墙托管。

## R — Result（本地 fixture，非线上生产；数字来自 `scripts/run_eval.py`）

| 对照 | 基线 | 改进后 | 变化 |
|------|------|--------|------|
| checkout-504 工具调用 | 5 次 | 1 次 | **↓80%**（摘要+缓存命中） |
| inventory#repeat 工具调用 | 3 次（基线首跑） | **0 次** | **↓100%**（L2 缓存全命中） |
| inventory 端到端延迟 | 28413 ms | 17538 ms（首跑改进） | **↓38%** |

- 本地 `启动.bat` / `docker-compose up` 可跑通主路径；样例告警约 15s 级出报告。
- 完整表见 `docs/eval_results.md` / `docs/IMPROVEMENTS.md`。
- Demo：免费 Cloudflare Quick Tunnel（链接见 README；本机在线时有效，进程退出即失效）。
- 反思：若重做，会把工具主机拆成独立 MCP stdio Server，并接真实 OTel Collector。

## 追问预案

| 追问 | 要点 |
|------|------|
| 为什么不是 RAG 客服？ | 输入告警、输出带证据 RCA，工具是日志 MCP |
| 如何防幻觉？ | 证据字段强制、假设标注、工具白名单 |
| 缓存一致性？ | query hash + TTL；评测可关缓存 |
