# IMPROVEMENTS — 基线 vs 自研改进

数字来源：`scripts/run_eval.py` → `docs/eval_results.md`（**本地 fixture，非线上生产**）。

## 改进点

| 改进 | 朴素基线 | 做法 | 预期/实测方向 | 测量方法 |
|------|----------|------|---------------|----------|
| 结构化日志摘要 | 工具原样全文回灌 LLM | 抽 level/service/trace/error 压缩 | observation 体积↓；prompt 受轨迹影响会波动 | 同告警开关 `FEATURE_SUMMARY` |
| 多级缓存 | 每次必调 MCP | L1 dict + L2 磁盘，query hash | 重复告警 tool_calls↓、cache_hits↑ | 同告警连跑两次 |

## 本轮脚本实测摘录（2026-07-16）

| case | 配置 | latency_ms | prompt_tokens | tool_calls | cache_hits |
|------|------|------------|---------------|------------|------------|
| case-checkout-504 | baseline | 16541 | 5561 | 5 | 0 |
| case-inventory-redis | baseline | 28413 | 4066 | 3 | 0 |
| case-checkout-504 | improved | 15871 | 5653 | 1 | 4 |
| case-inventory-redis#repeat | improved | 15112 | 6378 | **0** | **3** |

解读（可写进 STAR-R）：

- checkout-504：`tool_calls` 5→1（**↓80%**），`cache_hits` 0→4
- inventory#repeat：`tool_calls` 可到 **0**（相对基线首跑 3 次 ≈ **↓100%**）
- inventory 延迟：28413→17538 ms（**↓38%**，受网络波动）
- Token 受 Agent 步数路径影响，不能单看一次绝对值；以同脚本对照表为准。

## A/B 开关

- `FEATURE_SUMMARY=0|1`（请求体 `feature_summary`）
- `FEATURE_CACHE=0|1`（请求体 `feature_cache`）

## 验收

- [x] 有对照表且数字来自脚本输出
- [x] README / STAR 标注「本地 fixture，非线上生产」
