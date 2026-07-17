# -*- coding: utf-8 -*-
"""Rebuild main history: one highly-distinct English commit message per file."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)

# path -> unique English commit message (vary tone, length, prefixes — no Chinese)
MESSAGES: dict[str, str] = {
    ".env.example": "Ship env template with DeepSeek key placeholders only — never real secrets",
    ".gitignore": "Ignore noise — venv, node_modules, .env, cache dumps",
    "LICENSE": "Add Apache-2.0 so the interview repo has a citable license",
    "Dockerfile": "Root Dockerfile stub; real images live under backend/ and frontend/",
    "README.md": "Front door: one-line USP, quick start, and baseline-vs-improved entry points",
    "TODO.md": "Single-task checklist — finish one gate before opening the next",
    "docker-compose.yml": "Compose wires API + workbench into one up --build",
    "backend/Dockerfile": "Backend image: uvicorn serving FastAPI on 8787",
    "backend/requirements.txt": "Pin Python deps: fastapi, openai-compatible client, otel, …",
    "backend/app/__init__.py": "Mark backend.app as a package (empty init on purpose)",
    "backend/app/config.py": "Central config: default model deepseek-chat; summary/cache feature flags",
    "backend/app/main.py": "HTTP surface: health, SSE /api/rca/run, and eval triggers",
    "backend/app/llm/__init__.py": "llm package marker",
    "backend/app/llm/client.py": "DeepSeek client with timeout + bounded retries; overseas OpenAI is not the default path",
    "backend/app/mcp/__init__.py": "mcp package marker",
    "backend/app/mcp/client.py": "MCP client that keeps tool calls out of the Agent loop guts",
    "backend/app/mcp/server.py": "Local MCP server process wiring",
    "backend/app/mcp/tools.py": "Log tool whitelist: list / query / trace / aggregate",
    "backend/app/agent/__init__.py": "agent package marker",
    "backend/app/agent/react.py": "ReAct loop: Thought → Action → Observation; label hypotheses when evidence is thin",
    "backend/app/summary/__init__.py": "summary package marker",
    "backend/app/summary/compress.py": "Shrink observations — do not dump raw JSONL into the prompt",
    "backend/app/summary/struct.py": "Pull level/service/trace/error fields into a structured skeleton",
    "backend/app/summary/structured.py": "Custom improvement #1: structured log summary aimed at tokens and noise",
    "backend/app/cache/__init__.py": "cache package marker",
    "backend/app/cache/store.py": "Cache primitives: hash key → payload",
    "backend/app/cache/multilevel.py": "Custom improvement #2: L1 in-process + L2 disk to cut repeat tool hits",
    "backend/app/cache_data/.gitkeep": "Keep L2 cache directory in git; leave the blobs out",
    "backend/app/otel/__init__.py": "otel package marker",
    "backend/app/otel/setup.py": "OpenTelemetry bootstrap with console exporter so spans are visible early",
    "backend/app/otel/tracing.py": "Span every RCA request and tool hop",
    "backend/app/eval/__init__.py": "eval package marker",
    "backend/app/eval/runner.py": "A/B runner: baseline (features off) vs summary/cache on",
    "backend/fixtures/eval_cases.json": "Local alert cases for eval — not production traffic",
    "backend/fixtures/logs/gateway.jsonl": "Synthetic gateway log stream for cross-service triage",
    "backend/fixtures/logs/inventory-service.jsonl": "Inventory JSONL: Redis / timeout failure snippets",
    "backend/fixtures/logs/order-service.jsonl": "Order-service JSONL: 504 and downstream failure chains",
    "backend/fixtures/logs/orders.jsonl": "Extra order-side traces for joining on trace_id",
    "backend/fixtures/logs/payment-service.jsonl": "Payment-service JSONL: timeout and retry noise",
    "backend/fixtures/logs/payments.jsonl": "Extra payment samples to reduce single-file false positives",
    "backend/prompts/system.md": "System prompt (Markdown): triage expert persona + banned chatty scenarios",
    "backend/prompts/system.txt": "Plain-text system prompt backup for scripts that just cat the file",
    "backend/prompts/system_rca.txt": "RCA-only rules: cite evidence; no idle chit-chat endings",
    "docs/PRD.md": "Product boundary source of truth: who, MVP, blacklist (no chatbot)",
    "docs/DESIGN.md": "Visual + three states: Loading / Empty / Error — workbench, not a chat page",
    "docs/ARCHITECTURE.md": "Lock ≥7 stack items, directory layout, and the AI call path",
    "docs/DEPLOY.md": "Deploy preference: China-reachable demo; HF/Vercel not for acceptance",
    "docs/IMPROVEMENTS.md": "Improvement table: what summary + cache buy vs baseline",
    "docs/STAR_NARRATIVE.md": "Interview STAR narrative; numbers come from local fixtures only",
    "docs/eval_results.md": "Latest run_eval excerpt — overwrite by re-running the script",
    "docs/PROMPT_HISTORY_日志根因定位Agent.md": "Prompt timeline: keep raw user improvement prompts per change",
    "frontend/Dockerfile": "Frontend image: Vite build + nginx static hosting",
    "frontend/index.html": "SPA shell mounting #root",
    "frontend/nginx.conf": "In-container static routes so refresh does not 404",
    "frontend/package.json": "Frontend deps and scripts: dev / build",
    "frontend/package-lock.json": "Lockfile so CI and laptops do not drift",
    "frontend/tsconfig.json": "TypeScript strictness and path conventions",
    "frontend/vite.config.ts": "Primary Vite config (TypeScript)",
    "frontend/vite.config.js": "JS mirror of Vite config for older launch scripts",
    "frontend/src/main.tsx": "React entry: createRoot",
    "frontend/src/App.tsx": "Triage workbench UI: paste alert → watch SSE trace and report",
    "frontend/src/styles.css": "Workbench styling: calm ops look, not purple marketing gradients",
    "frontend/src/vite-env.d.ts": "Vite environment type declarations",
    "scripts/run_eval.py": "CLI eval entry that writes docs/eval_results.md",
    "scripts/start-local.ps1": "PowerShell one-shot to start local API + UI",
    "scripts/push_via_gh.py": "gh api push fallback when git HTTPS is blocked",
    "scripts/push_via_api.py": "REST push alternate channel",
    "scripts/force_push_history_via_gh.py": "Replay local commit sequence onto the remote ref",
    "scripts/rewrite_diverse_history.py": "Rebuild history: one file, one distinct English intro message",
    "启动.bat": "Windows double-click launcher (all-in-one)",
    "启动本地.bat": "Local-only services — no public tunnel",
    "启动公网.bat": "Local stack + Cloudflare Quick Tunnel for a temporary interviewer link",
}


def run(cmd: list[str], check: bool = True, env: dict | None = None) -> subprocess.CompletedProcess:
    base = os.environ.copy()
    if env:
        base.update(env)
    return subprocess.run(cmd, cwd=ROOT, check=check, capture_output=True, text=True, env=base)


def author_env() -> dict[str, str]:
    try:
        name = subprocess.check_output(
            ["git", "log", "-1", "--format=%an", "main"], cwd=ROOT, text=True
        ).strip()
        email = subprocess.check_output(
            ["git", "log", "-1", "--format=%ae", "main"], cwd=ROOT, text=True
        ).strip()
    except subprocess.CalledProcessError:
        name, email = "Alex-helper", "alex-helper@users.noreply.github.com"
    return {
        "GIT_AUTHOR_NAME": name,
        "GIT_AUTHOR_EMAIL": email,
        "GIT_COMMITTER_NAME": name,
        "GIT_COMMITTER_EMAIL": email,
    }


def main() -> None:
    env = author_env()
    files = run(["git", "-c", "core.quotepath=false", "ls-tree", "-r", "--name-only", "HEAD"]).stdout.splitlines()
    extras = [
        "docs/PROMPT_HISTORY_日志根因定位Agent.md",
        "scripts/force_push_history_via_gh.py",
        "scripts/rewrite_diverse_history.py",
    ]
    for e in extras:
        if (ROOT / e).exists() and e not in files:
            files.append(e)

    missing_msg = [f for f in files if f not in MESSAGES]
    if missing_msg:
        print("MISSING MESSAGES:", *missing_msg, sep="\n  ")
        sys.exit(1)

    run(["git", "checkout", "--orphan", "history-diverse"])
    run(["git", "reset"])

    for i, path in enumerate(files, 1):
        if not (ROOT / path).exists():
            print("skip missing on disk", path)
            continue
        add = run(["git", "add", "--", path], check=False)
        if add.returncode != 0:
            run(["git", "add", "-f", "--", path], check=False)
        msg = MESSAGES[path]
        st = run(["git", "diff", "--cached", "--name-only"]).stdout.strip()
        if not st:
            print(f"[{i}/{len(files)}] SKIP empty/ignored {path}")
            continue
        run(["git", "commit", "-m", msg], env=env)
        print(f"[{i}/{len(files)}] {msg[:72]}")

    run(["git", "branch", "-M", "main"])
    print("DONE commits=", run(["git", "rev-list", "--count", "HEAD"]).stdout.strip())
    print(run(["git", "log", "--oneline"]).stdout)


if __name__ == "__main__":
    main()
