# Eval Results（本地 fixture，非线上生产）

生成脚本：`scripts/run_eval.py`。数字来自真实 DeepSeek 调用与 MCP 工具统计。

## Baseline（summary=0, cache=0）

| case | latency_ms | prompt_tokens | completion_tokens | tool_calls | cache_hits |
|------|------------|---------------|-------------------|------------|------------|
| case-checkout-504 | 16541 | 5561 | 1000 | 5 | 0 |
| case-inventory-redis | 28413 | 4066 | 759 | 3 | 0 |

## Improved（summary=1, cache=1）

| case | latency_ms | prompt_tokens | completion_tokens | tool_calls | cache_hits |
|------|------------|---------------|-------------------|------------|------------|
| case-checkout-504 | 15871 | 5653 | 918 | 1 | 4 |
| case-checkout-504#repeat | 18599 | 5976 | 1089 | 1 | 4 |
| case-inventory-redis | 17538 | 6235 | 1044 | 2 | 1 |
| case-inventory-redis#repeat | 15112 | 6378 | 884 | 0 | 3 |

## 解读提示

- `prompt_tokens`：摘要开启后通常更低（同告警对比）。
- `#repeat` 行：缓存开启后 `tool_calls` 应下降或 `cache_hits` 上升。
- 延迟受网络与模型排队影响，以同一次脚本输出为准。
