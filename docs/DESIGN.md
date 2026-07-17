# DESIGN — 日志根因定位 Agent

## 设计关键词

- 气质：运维控制台 / 值班台，冷静、信息密度可控
- 色彩：深青灰底 + 琥珀告警点缀（非紫、非奶油纸风）
- 布局：左输入 / 右过程+结果，单屏主路径
- 避免：聊天气泡堆叠成「客服」、营销卡片、浮动徽章

## CSS 变量（实现时落地）

```css
:root {
  --bg: #0f1419;
  --panel: #1a222c;
  --border: #2a3544;
  --text: #e7eef7;
  --muted: #8b9bb0;
  --accent: #3d9cf0;   /* 主操作 */
  --warn: #e8a317;     /* 告警 */
  --ok: #3ecf8e;       /* 成功步骤 */
  --err: #e85d5d;
  --mono: "IBM Plex Mono", "Cascadia Code", ui-monospace, monospace;
  --sans: "IBM Plex Sans", "Source Han Sans SC", system-ui, sans-serif;
}
```

## 信息架构

```
┌─────────────┬──────────────────────────────────┐
│ 告警输入     │  Agent 推理流（SSE）              │
│ 样例快捷选   │  Thought / Action / Observation │
│ [定位根因]   ├──────────────────────────────────┤
│ 指标条       │  结构化报告（根因/影响/建议）      │
└─────────────┴──────────────────────────────────┘
```

## 组件复用

| 组件 | 用途 |
|------|------|
| `AlertForm` | 告警文本 + 样例下拉 |
| `RunButton` | 主 CTA，Loading 禁用 |
| `TraceStream` | 逐步追加的推理卡片 |
| `ReportPanel` | Markdown/结构化报告 |
| `MetricBar` | Token / 延迟 / 缓存命中 / 工具次数 |
| `StateBlock` | Empty / Loading / Error 统一样式 |

## 关键交互

1. 提交后左侧表单锁定；右侧清空旧报告并进入 Loading。
2. SSE 每步推送一条 `trace` 事件，卡片淡入。
3. `report` 事件到达后展开报告；`metrics` 刷新指标条。
4. 失败：Error 条显示可读原因（超时 / 无 Key / 工具失败），可重试。

## 三态 UI

| 状态 | 表现 |
|------|------|
| Empty | 「粘贴告警或选择样例，开始根因定位」 |
| Loading | 主按钮 spinner；流区骨架或「推理中…」 |
| Error | 红条 + 错误文案；不假装已有根因 |

## 验收标准

1. 首屏一眼能识别为「告警排障」而非聊天产品。
2. 三态均可被手动触发验证（空提交、正常流、断 Key）。
3. 推理流与报告分区清晰，不混在同一气泡列表。
