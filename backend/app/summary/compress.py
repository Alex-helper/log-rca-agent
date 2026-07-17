"""Structured log summarization — self-improvement to cut tokens."""

from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any, List


def summarize_logs(raw: Any, *, enabled: bool = True, max_evidence: int = 8) -> str:
    """Compress tool observation into structured digest.

    Baseline path passes raw JSON string; improved path extracts
    level/service/trace/error patterns and top signatures.
    """
    if not enabled:
        if isinstance(raw, str):
            return raw
        return json.dumps(raw, ensure_ascii=False)

    if isinstance(raw, str):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return _fallback_text(raw, max_evidence)
    else:
        data = raw

    lines: List[dict] = []
    if isinstance(data, dict):
        if "logs" in data and isinstance(data["logs"], list):
            lines = [x for x in data["logs"] if isinstance(x, dict)]
        elif "items" in data and isinstance(data["items"], list):
            lines = [x for x in data["items"] if isinstance(x, dict)]
        else:
            return json.dumps(data, ensure_ascii=False)[:4000]
    elif isinstance(data, list):
        lines = [x for x in data if isinstance(x, dict)]
    else:
        return str(data)[:4000]

    if not lines:
        return json.dumps(data, ensure_ascii=False)[:2000]

    levels = Counter(str(x.get("level", "?")).upper() for x in lines)
    services = Counter(str(x.get("service", "?")) for x in lines)
    traces = Counter(str(x.get("trace_id", "")) for x in lines if x.get("trace_id"))
    err_msgs = []
    for x in lines:
        if str(x.get("level", "")).upper() in ("ERROR", "FATAL", "WARN", "WARNING"):
            err_msgs.append(str(x.get("msg", ""))[:180])

    # Signature clustering (simple normalize digits)
    sigs = Counter(_norm_sig(m) for m in err_msgs if m)

    digest = {
        "kind": "structured_log_summary",
        "count": len(lines),
        "levels": dict(levels),
        "services": dict(services),
        "top_traces": traces.most_common(5),
        "top_error_signatures": sigs.most_common(5),
        "evidence": err_msgs[:max_evidence],
        "time_span": {
            "first": lines[0].get("ts"),
            "last": lines[-1].get("ts"),
        },
    }
    return json.dumps(digest, ensure_ascii=False)


def _norm_sig(msg: str) -> str:
    s = re.sub(r"\d+", "N", msg)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:120]


def _fallback_text(text: str, max_evidence: int) -> str:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    errors = [ln for ln in lines if re.search(r"ERROR|FAIL|timeout|exhausted", ln, re.I)]
    return json.dumps(
        {
            "kind": "structured_log_summary",
            "count": len(lines),
            "evidence": errors[:max_evidence] or lines[:max_evidence],
        },
        ensure_ascii=False,
    )
