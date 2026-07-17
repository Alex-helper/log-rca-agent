# 日志根因定位 Agent（MCP）

> GitHub: https://github.com/Alex-helper/log-rca-agent  
> Demo（免费 Cloudflare Tunnel，本机在线时有效）: https://rhode-from-secret-conduct.trycloudflare.com  
> 本地: http://127.0.0.1:8787 · 备选见 [docs/DEPLOY.md](docs/DEPLOY.md)

告警驱动的微服务**日志根因定位** Agent：ReAct 多步推理 + MCP 工具取证 + DeepSeek `deepseek-chat` + FastAPI SSE + React 工作台。  
**不是**通用问答 / 智能客服。

## 核心技术栈（≥7）

| # | 技术 | 说明 |
|:-:|------|------|
| 1 | MCP | 日志工具标准化（list/query/trace/aggregate） |
| 2 | ReAct | Thought → Action → Observation |
| 3 | DeepSeek API | 国内主推理路径 `deepseek-chat` |
| 4 | FastAPI + SSE | 推理轨迹与报告流式推送 |
| 5 | 结构化日志摘要 | 自研改进，降 Token |
| 6 | 多级缓存 | L1 内存 + L2 磁盘，降重复工具调用 |
| 7 | OpenTelemetry | 请求/工具 span（console exporter） |
| 8 | Prompt Engineering | 证据强制、场景黑名单 |

## 一键启动

### Windows（推荐开发）

1. 复制 `.env.example` → `.env`，填入 DeepSeek Key  
2. 双击 `启动.bat`  
3. 打开 http://127.0.0.1:5173

### Docker Compose

```bash
cp .env.example .env   # 填 OPENAI_API_KEY
docker-compose up --build
# 浏览器打开 http://127.0.0.1:8787
```

### 手动

```powershell
# 后端
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend\requirements.txt
$env:PYTHONPATH="backend"
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8787

# 前端（另开终端）
cd frontend
npm install
npm run dev
```

## 评测（基线 vs 改进）

```powershell
$env:PYTHONPATH="backend"
.\.venv\Scripts\python scripts\run_eval.py
# 输出 docs/eval_results.md
```

## 文档

- [PRD](docs/PRD.md) · [DESIGN](docs/DESIGN.md) · [ARCHITECTURE](docs/ARCHITECTURE.md)
- [IMPROVEMENTS](docs/IMPROVEMENTS.md) · [DEPLOY](docs/DEPLOY.md) · [STAR](docs/STAR_NARRATIVE.md)
- [TODO](TODO.md)

## Publish（GitHub）

```bash
git init
git add .
git commit -m "feat: log RCA agent MVP"
# 在 GitHub 创建公开仓后：
git remote add origin https://github.com/<you>/log-rca-agent.git
git push -u origin main
```

License: [Apache-2.0](LICENSE)
