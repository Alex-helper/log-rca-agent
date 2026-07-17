from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.agent import RcaAgent
from app.config import (
    FEATURE_CACHE,
    FEATURE_SUMMARY,
    MODEL_NAME,
    OPENAI_BASE_URL,
    ROOT,
)
from app.llm import DeepSeekClient
from app.mcp import get_registry
from app.otel import setup_otel

setup_otel("log-rca-agent")

app = FastAPI(title="Log RCA Agent", docs_url="/api/docs")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AlertIn(BaseModel):
    severity: str = "critical"
    service: str = ""
    message: str
    trace_id: str = ""
    timestamp: str = ""
    raw: str = ""


class RcaRunReq(BaseModel):
    alert: AlertIn
    feature_summary: Optional[bool] = None
    feature_cache: Optional[bool] = None


class EvalReq(BaseModel):
    case_ids: List[str] = Field(default_factory=list)
    feature_summary: bool = True
    feature_cache: bool = True


@app.get("/api/health")
async def health():
    llm = DeepSeekClient()
    return {
        "ok": True,
        "configured": llm.configured(),
        "model": MODEL_NAME,
        "base_url": OPENAI_BASE_URL,
        "feature_summary": FEATURE_SUMMARY,
        "feature_cache": FEATURE_CACHE,
        "mcp_tools": [t["name"] for t in get_registry().list_tools()],
    }


@app.get("/api/mcp/tools")
async def mcp_tools():
    return {"tools": get_registry().list_tools()}


@app.get("/api/samples")
async def samples():
    path = Path(__file__).resolve().parents[1] / "fixtures" / "eval_cases.json"
    cases = json.loads(path.read_text(encoding="utf-8"))
    return {"samples": cases}


@app.post("/api/rca/run")
async def rca_run(req: RcaRunReq):
    if not (req.alert.message or "").strip():
        raise HTTPException(status_code=400, detail="alert.message 不能为空")

    alert = req.alert.model_dump()
    if req.alert.raw.strip():
        alert["raw"] = req.alert.raw.strip()

    agent = RcaAgent(
        use_summary=FEATURE_SUMMARY if req.feature_summary is None else req.feature_summary,
        use_cache=FEATURE_CACHE if req.feature_cache is None else req.feature_cache,
    )

    async def gen():
        async for ev in agent.run_stream(alert):
            payload = json.dumps(ev["data"], ensure_ascii=False)
            yield f"event: {ev['event']}\ndata: {payload}\n\n"

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/eval/run")
async def eval_run(req: EvalReq):
    """同步跑评测集（供脚本/页面）；数字来自真实调用。"""
    from app.eval.runner import run_cases

    results = await run_cases(
        case_ids=req.case_ids or None,
        feature_summary=req.feature_summary,
        feature_cache=req.feature_cache,
    )
    return results


# Static frontend: prefer Vite build, else backend/static copy
_DIST_CANDIDATES = [
    ROOT / "frontend" / "dist",
    ROOT / "backend" / "static",
]
DIST = next((p for p in _DIST_CANDIDATES if (p / "index.html").exists()), None)
if DIST is not None:
    assets = DIST / "assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/")
    async def index():
        return FileResponse(DIST / "index.html")
else:

    @app.get("/")
    async def index_fallback():
        return {
            "service": "log-rca-agent",
            "hint": "开发时请启动 frontend (Vite)。生产构建后将托管 frontend/dist。",
            "health": "/api/health",
        }
