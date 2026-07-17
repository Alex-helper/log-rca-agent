# ARCHITECTURE — 日志根因定位 Agent

## 技术栈（≥7，写死）

| # | 技术/方法 | 类型 | 用途 |
|:-:|-----------|------|------|
| 1 | MCP | 较新栈 | 日志工具标准化暴露与调用 |
| 2 | ReAct | 方法 | Thought→Action→Observation 多步推理 |
| 3 | DeepSeek API (`deepseek-chat`) | 基础工程 | 国内主推理路径 |
| 4 | FastAPI + SSE | 较新栈 | Agent 轨迹与报告流式下发 |
| 5 | 结构化日志摘要 | **自研改进** | 压缩工具回传，降 Token |
| 6 | 多级缓存 | **自研改进** | 进程内 L1 + 磁盘 L2，降重复工具/LLM |
| 7 | OpenTelemetry | 较新栈 | 请求与工具调用链路追踪 |
| 8 | Prompt Engineering | 方法 | 角色约束、证据强制、黑名单场景 |

禁止：仅 CRUD；禁止改成客服/通用问答。

## 目录结构（目标）

```text
log-rca-agent/
├── docs/                 # PRD DESIGN ARCHITECTURE STAR IMPROVEMENTS DEPLOY
├── TODO.md
├── README.md
├── LICENSE               # Apache-2.0
├── .env.example
├── docker-compose.yml
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── agent/        # ReAct loop
│   │   ├── mcp/          # MCP client + local log tools server
│   │   ├── llm/          # DeepSeek client（重试/超时）
│   │   ├── summary/      # 结构化日志摘要
│   │   ├── cache/        # L1/L2
│   │   ├── otel/         # tracing
│   │   └── eval/         # 基线 vs 改进评测
│   ├── fixtures/logs/    # 合成微服务日志
│   ├── prompts/
│   └── requirements.txt
├── frontend/             # React + Vite
│   ├── src/
│   └── package.json
└── scripts/
```

## 数据模型（概念）

```text
AlertEvent { id?, service?, severity, message, timestamp?, trace_id?, raw }
AgentStep  { type: thought|action|observation|error, content, tool?, ts }
RcaReport  { root_cause, evidence[], blast_radius, remediation[], confidence_note, steps[] }
RunMetrics { latency_ms, prompt_tokens, completion_tokens, tool_calls, cache_hits }
```

## 服务层约定

1. **唯一推理入口**：`POST /api/rca/run` → SSE（`trace` / `report` / `metrics` / `error` / `done`）。
2. **MCP 工具白名单**（示例）：`list_services`、`query_logs`、`get_trace_logs`、`aggregate_errors`。
3. **LLM 客户端**：Base URL 默认 `https://api.deepseek.com/v1`；模型默认 `deepseek-chat`；超时与有限次重试。
4. **摘要开关 / 缓存开关**：环境变量或查询参数，供评测 A/B。
5. **OpenTelemetry**：每个 HTTP 请求与工具调用创建 span；导出可先用 console exporter。

## AI 调用机制

```text
Alert → System Prompt（排障专家 + 禁止闲聊）
     → ReAct Loop（max_steps）
         → LLM 决定 tool_call
         → MCP 执行 → 可选「结构化摘要」
         → Observation 回填（可走缓存）
     → 终态：强制产出 RcaReport JSON/Markdown
     → SSE 推送 report + metrics
```

## 绝不能破坏的约束

1. 主模型不得默认换成海外 OpenAI 官方模型名作为主路径。
2. 无证据不得写成「已确认根因」；需标注假设/证据不足。
3. 不得提供闲聊入口或通用知识库问答路由。
4. 评测数字必须来自本地 fixture 跑分脚本，禁止编造。

## 在线 Demo 策略（免费优先）

优先级：Sealos 免费容器 → 魔搭创空间 → 本机 + Cloudflare Quick Tunnel → 付费阿里云轻量（备选）。  
主路径须国内网络可打开；禁止 HF / Vercel / Railway / Streamlit Cloud 作为验收 Demo。

## 验收标准

1. 架构图与目录能在 README 中复述。
2. 任一请求可在日志中看到 OTel span 或等价 trace 输出。
3. 关闭摘要/缓存时评测脚本可跑出对照表行。
