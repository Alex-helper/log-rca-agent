# PROMPT_HISTORY — 日志根因定位 Agent（log-rca-agent）

> 自动记录：产品/项目每一次改进相关的**用户提示词**。
> 由全局 skill `prompt-history-recorder` 维护；新改进完成后追加，勿删历史条目。

- 项目名称：日志根因定位 Agent（MCP）
- 项目路径：`log-rca-agent/`
- 条目数：4
- 生成来源：Cursor agent-transcripts（回溯 + 后续会话追加）

> 备注：首轮创建需求可能在更早会话中（本机 transcripts 仅见「继续」及后续 GitHub/提交相关指令）；产品定位见 docs/PRD.md。

## 改进时间线

| # | 时间 | 一句话 | Transcript |
|---|------|--------|------------|
| 1 | Thursday, Jul 16, 2026, 7:59 PM (UTC+8) | 你帮我弹出来github，我登录一下，然后你帮我推送 | `5d8bcd61` |
| 2 | Thursday, Jul 16, 2026, 8:26 PM (UTC+8) | 每个文件的不要全是feat开头啊 | `5d8bcd61` |
| 3 | Friday, Jul 17, 2026, 6:41 PM (UTC+8) | 日志归因Agent项目，把github上面的每个文件介绍不要一模一样，要差异非常大 | `4812174e` |
| 4 | Friday, Jul 17, 2026, 6:52 PM (UTC+8) | 不要用中文写 | `4812174e` |

## 原文（按时间）

### 1. Thursday, Jul 16, 2026, 7:59 PM (UTC+8)

- transcript: `5d8bcd61-dbc0-40bd-b648-bb81da234d6e`

```text
你帮我弹出来github，我登录一下，然后你帮我推送
```

### 2. Thursday, Jul 16, 2026, 8:26 PM (UTC+8)

- transcript: `5d8bcd61-dbc0-40bd-b648-bb81da234d6e`

```text
每个文件的不要全是feat开头啊
```

### 3. Friday, Jul 17, 2026, 6:41 PM (UTC+8)

- transcript: `4812174e-f474-4a03-9663-50faa307a8f0`

```text
日志归因Agent项目，把github上面的每个文件介绍不要一模一样，要差异非常大
```

### 4. Friday, Jul 17, 2026, 6:52 PM (UTC+8)

- transcript: `4812174e-f474-4a03-9663-50faa307a8f0`

```text
不要用中文写
```
