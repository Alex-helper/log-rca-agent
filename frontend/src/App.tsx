import { useEffect, useMemo, useState } from "react";

type Step = { type: string; content: string; tool?: string; step?: number };
type Report = {
  root_cause: string;
  evidence: string[];
  blast_radius: string;
  remediation: string[];
  confidence_note: string;
};
type Metrics = {
  latency_ms?: number;
  prompt_tokens?: number;
  completion_tokens?: number;
  tool_calls?: number;
  cache_hits?: number;
  model?: string;
};
type Sample = { id: string; alert: Record<string, string> };

const emptyAlert = {
  severity: "critical",
  service: "gateway",
  message: "",
  trace_id: "",
  timestamp: "",
};

export default function App() {
  const [health, setHealth] = useState<{ configured?: boolean; model?: string } | null>(null);
  const [samples, setSamples] = useState<Sample[]>([]);
  const [sampleId, setSampleId] = useState("");
  const [alert, setAlert] = useState(emptyAlert);
  const [summaryOn, setSummaryOn] = useState(true);
  const [cacheOn, setCacheOn] = useState(true);
  const [loading, setLoading] = useState(false);
  const [steps, setSteps] = useState<Step[]>([]);
  const [report, setReport] = useState<Report | null>(null);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch("/api/health")
      .then((r) => r.json())
      .then(setHealth)
      .catch(() => setHealth({ configured: false }));
    fetch("/api/samples")
      .then((r) => r.json())
      .then((d) => {
        setSamples(d.samples || []);
        if (d.samples?.[0]) {
          setSampleId(d.samples[0].id);
          setAlert({ ...emptyAlert, ...d.samples[0].alert });
        }
      })
      .catch(() => {});
  }, []);

  const statusBadge = useMemo(() => {
    if (!health) return <span className="badge">checking…</span>;
    if (health.configured)
      return <span className="badge ok">{health.model || "ready"}</span>;
    return <span className="badge warn">未配置 API Key</span>;
  }, [health]);

  function applySample(id: string) {
    setSampleId(id);
    const s = samples.find((x) => x.id === id);
    if (s) setAlert({ ...emptyAlert, ...s.alert });
  }

  async function runRca() {
    if (!alert.message.trim()) {
      setError("请填写告警 message，或选择样例");
      return;
    }
    setLoading(true);
    setError("");
    setSteps([]);
    setReport(null);
    setMetrics(null);

    try {
      const resp = await fetch("/api/rca/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          alert,
          feature_summary: summaryOn,
          feature_cache: cacheOn,
        }),
      });
      if (!resp.ok || !resp.body) {
        const t = await resp.text();
        throw new Error(t || `HTTP ${resp.status}`);
      }

      const reader = resp.body.getReader();
      const dec = new TextDecoder();
      let buf = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        const chunks = buf.split("\n\n");
        buf = chunks.pop() || "";
        for (const chunk of chunks) {
          const lines = chunk.split("\n");
          let ev = "message";
          let data = "";
          for (const line of lines) {
            if (line.startsWith("event:")) ev = line.slice(6).trim();
            if (line.startsWith("data:")) data += line.slice(5).trim();
          }
          if (!data) continue;
          const obj = JSON.parse(data);
          if (ev === "trace") setSteps((prev) => [...prev, obj]);
          else if (ev === "report") setReport(obj);
          else if (ev === "metrics") setMetrics(obj);
          else if (ev === "error") setError(obj.message || "未知错误");
        }
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <header className="header">
        <div>
          <h1>日志根因定位 Agent</h1>
          <p>告警驱动 · MCP 工具取证 · ReAct 多步推理 · DeepSeek</p>
        </div>
        {statusBadge}
      </header>

      <div className="grid">
        <section className="panel">
          <h2>Alert Input</h2>
          <label>样例告警</label>
          <select value={sampleId} onChange={(e) => applySample(e.target.value)} disabled={loading}>
            {samples.map((s) => (
              <option key={s.id} value={s.id}>
                {s.id}
              </option>
            ))}
          </select>

          <div className="row">
            <div>
              <label>severity</label>
              <input
                value={alert.severity}
                disabled={loading}
                onChange={(e) => setAlert({ ...alert, severity: e.target.value })}
              />
            </div>
            <div>
              <label>service</label>
              <input
                value={alert.service}
                disabled={loading}
                onChange={(e) => setAlert({ ...alert, service: e.target.value })}
              />
            </div>
          </div>

          <label>trace_id</label>
          <input
            value={alert.trace_id}
            disabled={loading}
            onChange={(e) => setAlert({ ...alert, trace_id: e.target.value })}
          />

          <label>message</label>
          <textarea
            value={alert.message}
            disabled={loading}
            placeholder="粘贴告警内容…"
            onChange={(e) => setAlert({ ...alert, message: e.target.value })}
          />

          <div className="toggles">
            <label>
              <input
                type="checkbox"
                checked={summaryOn}
                disabled={loading}
                onChange={(e) => setSummaryOn(e.target.checked)}
              />
              结构化摘要
            </label>
            <label>
              <input
                type="checkbox"
                checked={cacheOn}
                disabled={loading}
                onChange={(e) => setCacheOn(e.target.checked)}
              />
              多级缓存
            </label>
          </div>

          <button className="btn" disabled={loading} onClick={runRca}>
            {loading ? "定位中…" : "定位根因"}
          </button>
          <button
            className="btn ghost"
            disabled={loading}
            onClick={() => {
              setSteps([]);
              setReport(null);
              setMetrics(null);
              setError("");
            }}
          >
            清空结果
          </button>
        </section>

        <section className="panel">
          <h2>Agent Trace / Report</h2>
          {error && <div className="errbar">{error}</div>}

          {metrics && (
            <div className="metrics">
              <span className="metric">latency {metrics.latency_ms}ms</span>
              <span className="metric">prompt {metrics.prompt_tokens}</span>
              <span className="metric">completion {metrics.completion_tokens}</span>
              <span className="metric">tools {metrics.tool_calls}</span>
              <span className="metric">cache_hits {metrics.cache_hits}</span>
              <span className="metric">{metrics.model}</span>
            </div>
          )}

          {!loading && !steps.length && !report && !error && (
            <div className="empty">
              粘贴告警或选择样例，开始根因定位。
              <br />
              本产品不做闲聊 / 客服问答。
            </div>
          )}

          {loading && !steps.length && (
            <div className="empty">推理中，正在调用 MCP 工具…</div>
          )}

          <div className="stream">
            {steps.map((s, i) => (
              <div key={i} className={`step ${s.type}`}>
                <div className="tag">
                  {s.type}
                  {s.tool ? ` · ${s.tool}` : ""}
                  {s.step ? ` · #${s.step}` : ""}
                </div>
                <pre>{s.content}</pre>
              </div>
            ))}
          </div>

          {report && (
            <div className="report">
              <h3>结构化报告</h3>
              <p>
                <strong>根因：</strong>
                {report.root_cause}
              </p>
              <p className="muted">{report.confidence_note}</p>
              <p>
                <strong>影响范围：</strong>
                {report.blast_radius}
              </p>
              <strong>证据</strong>
              <ul>
                {(report.evidence || []).map((e, i) => (
                  <li key={i}>{e}</li>
                ))}
              </ul>
              <strong>修复建议</strong>
              <ul>
                {(report.remediation || []).map((e, i) => (
                  <li key={i}>{e}</li>
                ))}
              </ul>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
