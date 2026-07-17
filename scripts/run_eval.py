#!/usr/bin/env python3
"""A/B eval: baseline vs summary/cache. Writes docs/eval_results.md"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.eval.runner import run_cases  # noqa: E402


async def main():
    # Use first 2 cases to keep cost/time reasonable for demo
    ids = ["case-checkout-504", "case-inventory-redis"]

    baseline = await run_cases(case_ids=ids, feature_summary=False, feature_cache=False)
    improved = await run_cases(case_ids=ids, feature_summary=True, feature_cache=True)

    lines = [
        "# Eval Results（本地 fixture，非线上生产）",
        "",
        "生成脚本：`scripts/run_eval.py`。数字来自真实 DeepSeek 调用与 MCP 工具统计。",
        "",
        "## Baseline（summary=0, cache=0）",
        "",
        "| case | latency_ms | prompt_tokens | completion_tokens | tool_calls | cache_hits |",
        "|------|------------|---------------|-------------------|------------|------------|",
    ]
    for r in baseline["rows"]:
        if r["case_id"].endswith("#repeat"):
            continue
        lines.append(
            f"| {r['case_id']} | {r['latency_ms']} | {r['prompt_tokens']} | "
            f"{r['completion_tokens']} | {r['tool_calls']} | {r['cache_hits']} |"
        )

    lines += [
        "",
        "## Improved（summary=1, cache=1）",
        "",
        "| case | latency_ms | prompt_tokens | completion_tokens | tool_calls | cache_hits |",
        "|------|------------|---------------|-------------------|------------|------------|",
    ]
    for r in improved["rows"]:
        lines.append(
            f"| {r['case_id']} | {r['latency_ms']} | {r['prompt_tokens']} | "
            f"{r['completion_tokens']} | {r['tool_calls']} | {r['cache_hits']} |"
        )

    lines += [
        "",
        "## 解读提示",
        "",
        "- `prompt_tokens`：摘要开启后通常更低（同告警对比）。",
        "- `#repeat` 行：缓存开启后 `tool_calls` 应下降或 `cache_hits` 上升。",
        "- 延迟受网络与模型排队影响，以同一次脚本输出为准。",
        "",
    ]

    out = ROOT / "docs" / "eval_results.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    asyncio.run(main())
