"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import ApprovalModal from "./ApprovalModal";
import KillSwitch from "./KillSwitch";
import RateLimitBadge from "./RateLimitBadge";
import ToolCallCard from "./ToolCallCard";

const API = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";
type Session = { id: string; model: string; dry_run: boolean; status: string; created_at: string };
type Transcript = { id: string; role: "user" | "assistant" | "tool" | "system"; content?: string; name?: string; args?: unknown; result?: unknown; dryRun?: boolean; pending?: boolean };
type Approval = { id: string; session_id: string; action_type: string; diff_or_plan: string };
type FileEntry = { path: string; type: string; size: number | null };
type Audit = { id: string; created_at: string; actor: string; action_type: string; target: string | null; result: string; payload_json: Record<string, unknown> };

async function getJson<T>(path: string): Promise<T> { const response = await fetch(`${API}${path}`); if (!response.ok) throw new Error(await response.text()); return response.json(); }
async function postJson<T>(path: string, body?: unknown): Promise<T> { const response = await fetch(`${API}${path}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: body ? JSON.stringify(body) : undefined }); if (!response.ok) throw new Error(await response.text()); return response.json(); }

export default function HarnessDashboard() {
  const [settings, setSettings] = useState<any>(null); const [models, setModels] = useState<any[]>([]); const [sessions, setSessions] = useState<Session[]>([]);
  const [session, setSession] = useState<Session | null>(null); const [model, setModel] = useState(""); const [prompt, setPrompt] = useState(""); const [transcript, setTranscript] = useState<Transcript[]>([]);
  const [liveText, setLiveText] = useState(""); const [running, setRunning] = useState(false); const [error, setError] = useState(""); const [rate, setRate] = useState<any>(null);
  const [approvals, setApprovals] = useState<Approval[]>([]); const [files, setFiles] = useState<FileEntry[]>([]); const [preview, setPreview] = useState<any>(null); const [audit, setAudit] = useState<Audit[]>([]); const [activeTab, setActiveTab] = useState("chat");

  // Telemetry & metrics state
  const [streamStartTime, setStreamStartTime] = useState<number | null>(null);
  const [tokenCount, setTokenCount] = useState<number>(0);
  const [tokensPerSec, setTokensPerSec] = useState<number>(0);

  // Theme state
  const [theme, setTheme] = useState<"dark" | "light">("dark");

  // Audit filter state
  const [auditQuery, setAuditQuery] = useState("");
  const [auditActor, setAuditActor] = useState("");
  const [auditAction, setAuditAction] = useState("");
  const [auditResult, setAuditResult] = useState("");

  // Semantic search state
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [isIndexing, setIsIndexing] = useState(false);

  useEffect(() => {
    const savedTheme = (localStorage.getItem("harness-theme") as "dark" | "light") || "dark";
    setTheme(savedTheme);
    document.body.setAttribute("data-theme", savedTheme);
  }, []);

  const toggleTheme = () => {
    const nextTheme = theme === "dark" ? "light" : "dark";
    setTheme(nextTheme);
    localStorage.setItem("harness-theme", nextTheme);
    document.body.setAttribute("data-theme", nextTheme);
  };

  const refreshAudit = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      if (auditQuery) params.append("query", auditQuery);
      if (auditActor) params.append("actor", auditActor);
      if (auditAction) params.append("action_type", auditAction);
      if (auditResult) params.append("result", auditResult);
      const auditData = await getJson<any>(`/api/audit?${params.toString()}`);
      setAudit(auditData.entries || []);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to filter audit log");
    }
  }, [auditQuery, auditActor, auditAction, auditResult]);

  const refresh = useCallback(async () => {
    try {
      const [s, modelsData, sessionsData, rateData, approvalsData, filesData, auditData] = await Promise.all([
        getJson<any>("/api/settings"),
        getJson<any>("/api/models"),
        getJson<any>("/api/sessions"),
        getJson<any>("/api/rate-status"),
        getJson<any>("/api/approvals"),
        getJson<any>("/api/files?path=.&depth=3"),
        getJson<any>("/api/audit"),
      ]);
      setSettings(s);
      setModels(modelsData.models || []);
      setModel((current) => current || modelsData.models?.[0]?.name || "");
      setSessions(sessionsData.sessions || []);
      setRate(rateData);
      setApprovals(approvalsData.approvals || []);
      setFiles(filesData.entries || []);
      setAudit(auditData.entries || []);
      setError("");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to reach the local backend");
    }
  }, []);

  useEffect(() => {
    void refresh();
    const id = window.setInterval(() => {
      void getJson<any>("/api/rate-status").then(setRate).catch(() => undefined);
      void getJson<any>("/api/approvals").then((x) => setApprovals(x.approvals || [])).catch(() => undefined);
    }, 2500);
    return () => window.clearInterval(id);
  }, [refresh]);

  const loadSession = async (candidate: Session) => {
    try {
      const data = await getJson<any>(`/api/sessions/${candidate.id}`);
      setSession(data.session);
      setTranscript(
        (data.messages || []).map((m: any) => {
          if (m.role !== "tool") return { id: m.id, role: m.role, content: m.content };
          try {
            return { id: m.id, role: "tool", name: "persisted tool result", result: JSON.parse(m.content) };
          } catch {
            return { id: m.id, role: "tool", name: "persisted tool result", result: { content: m.content } };
          }
        })
      );
      setActiveTab("chat");
    } catch (cause) {
      setError(String(cause));
    }
  };

  const ensureSession = async (): Promise<Session> => {
    if (session) return session;
    if (!model) throw new Error("Select an installed Ollama model first");
    const created = await postJson<Session>("/api/sessions", { model });
    setSessions((items) => [created, ...items]);
    setSession(created);
    return created;
  };

  const toggleDryRun = async () => {
    if (!session) return;
    const changed = await postJson<Session>(`/api/sessions/${session.id}/dry-run`, { dry_run: !session.dry_run });
    setSession((current) => (current ? { ...current, dry_run: changed.dry_run } : current));
    setSessions((items) => items.map((item) => (item.id === changed.id ? changed : item)));
  };

  const resolve = async (item: Approval, approved: boolean, remember: boolean) => {
    await postJson(`/api/approvals/${item.id}/resolve`, { approved, remember_for_session: remember });
    await refresh();
  };

  const stop = async () => {
    if (session) await postJson(`/api/sessions/${session.id}/kill`);
  };

  const restore = async (snapshot: string, path: string) => {
    try {
      await postJson("/api/snapshots/restore", { snapshot_id: snapshot, path });
      setError("");
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Snapshot restore failed");
    }
  };

  // Fork session
  const forkCurrentSession = async () => {
    if (!session) return;
    try {
      const forked = await postJson<Session>(`/api/sessions/${session.id}/fork`);
      setSessions((items) => [forked, ...items]);
      await loadSession(forked);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Failed to fork session");
    }
  };

  // Export session
  const exportSessionMarkdown = () => {
    if (!session) return;
    window.open(`${API}/api/sessions/${session.id}/export?format=markdown`, "_blank");
  };

  const exportSessionJson = () => {
    if (!session) return;
    window.open(`${API}/api/sessions/${session.id}/export?format=json`, "_blank");
  };

  // Export audit CSV
  const exportAuditCsv = () => {
    const params = new URLSearchParams();
    if (auditQuery) params.append("query", auditQuery);
    if (auditActor) params.append("actor", auditActor);
    if (auditAction) params.append("action_type", auditAction);
    if (auditResult) params.append("result", auditResult);
    params.append("format", "csv");
    window.open(`${API}/api/audit?${params.toString()}`, "_blank");
  };

  // Semantic search execute
  const runSemanticSearch = async (e: FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim() || isSearching) return;
    setIsSearching(true);
    try {
      const res = await postJson<any>("/api/search/semantic", { query: searchQuery, top_k: 8 });
      setSearchResults(res.results || []);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Semantic search failed");
    } finally {
      setIsSearching(false);
    }
  };

  // Index refresh
  const triggerIndexRefresh = async () => {
    setIsIndexing(true);
    try {
      await postJson("/api/index/refresh");
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Index refresh failed");
    } finally {
      setIsIndexing(false);
    }
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const message = prompt.trim();
    if (!message || running) return;
    try {
      const current = await ensureSession();
      setPrompt("");
      setRunning(true);
      setError("");
      setLiveText("");
      const start = Date.now();
      setStreamStartTime(start);
      setTokenCount(0);
      setTokensPerSec(0);

      const userItem: Transcript = { id: crypto.randomUUID(), role: "user", content: message };
      setTranscript((items) => [...items, userItem]);

      const response = await fetch(`${API}/api/sessions/${current.id}/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
      });
      if (!response.ok || !response.body) throw new Error(await response.text());

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let eventName = "message";
      let localTokens = 0;

      const receive = (raw: string) => {
        for (const line of raw.split("\n")) {
          if (line.startsWith("event: ")) eventName = line.slice(7);
          if (line.startsWith("data: ")) {
            const payload = JSON.parse(line.slice(6));
            handleEvent(eventName, payload);
          }
        }
      };

      const handleEvent = (type: string, data: any) => {
        if (type === "token") {
          setLiveText((value) => value + data.content);
          localTokens++;
          setTokenCount(localTokens);
          const elapsedSec = (Date.now() - start) / 1000;
          if (elapsedSec > 0.3) {
            setTokensPerSec(Math.round((localTokens / elapsedSec) * 10) / 10);
          }
        } else if (type === "assistant_message") {
          setTranscript((items) => [...items, { id: crypto.randomUUID(), role: "assistant", content: data.content }]);
          setLiveText("");
        } else if (type === "tool_call_start") {
          setTranscript((items) => [
            ...items,
            { id: data.tool_call_id, role: "tool", name: data.name, args: data.arguments, dryRun: data.dry_run, pending: false },
          ]);
        } else if (type === "tool_call_result") {
          setTranscript((items) => items.map((item) => (item.id === data.tool_call_id ? { ...item, result: data.result, pending: false } : item)));
        } else if (type === "approval_required") {
          setTranscript((items) => items.map((item) => (item.id === data.tool_call_id ? { ...item, pending: true } : item)));
          void getJson<any>("/api/approvals").then((result) => setApprovals(result.approvals || []));
        } else if (type === "run_error") {
          setError(data.message);
        }
      };

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        let boundary;
        while ((boundary = buffer.indexOf("\n\n")) !== -1) {
          receive(buffer.slice(0, boundary));
          buffer = buffer.slice(boundary + 2);
          eventName = "message";
        }
      }
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Run failed");
    } finally {
      setRunning(false);
      setStreamStartTime(null);
    }
  };

  const visibleAudit = useMemo(() => audit.slice(0, 100), [audit]);

  return (
    <main className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">◉</span>
          <div>
            <b>LOCAL HARNESS</b>
            <small>Ollama · workspace-bound</small>
          </div>
        </div>
        <nav>
          {[
            ["chat", "Chat"],
            ["files", "Files & Search"],
            ["approvals", `Approvals ${approvals.length ? `(${approvals.length})` : ""}`],
            ["audit", "Audit Trail"],
            ["settings", "Settings"],
          ].map(([key, label]) => (
            <button key={key} className={activeTab === key ? "nav-active" : ""} onClick={() => setActiveTab(key)}>
              {label}
            </button>
          ))}
        </nav>
        <section className="sidebar-foot">
          <p>Outbound inference is restricted to the configured loopback Ollama daemon.</p>
          <RateLimitBadge status={rate} />
        </section>
      </aside>

      <section className="content">
        <header className="topbar">
          <div>
            <span className="eyebrow">SAFETY CONTROL PLANE</span>
            <h1>{activeTab === "chat" ? "Agent session" : activeTab === "files" ? "Files & Search" : activeTab[0].toUpperCase() + activeTab.slice(1)}</h1>
          </div>
          <div className="top-actions">
            <button className="secondary btn-sm" onClick={toggleTheme} title="Toggle Dark/Light Mode">
              {theme === "dark" ? "☀️ Light" : "🌙 Dark"}
            </button>
            {session && (
              <>
                <button className={`toggle ${session.dry_run ? "on" : ""}`} onClick={toggleDryRun} title="Changing dry-run is a logged user action">
                  Dry run {session.dry_run ? "ON" : "OFF"}
                </button>
                <button className="secondary btn-sm" onClick={forkCurrentSession} title="Branch / Fork current session">
                  Fork Branch
                </button>
                <button className="secondary btn-sm" onClick={exportSessionMarkdown} title="Export as Markdown">
                  Export .MD
                </button>
                <button className="secondary btn-sm" onClick={exportSessionJson} title="Export as JSON">
                  Export JSON
                </button>
              </>
            )}
            <KillSwitch disabled={!running} onKill={() => void stop()} />
          </div>
        </header>

        {error && (
          <div className="notice error">
            <strong>Local backend notice:</strong> {error}
          </div>
        )}

        {activeTab === "chat" && (
          <section className="chat-layout">
            <div className="session-strip">
              <label>
                Model
                <select value={model} onChange={(e) => setModel(e.target.value)} disabled={!!session}>
                  {!models.length && <option value="">No local models discovered</option>}
                  {models.map((item) => (
                    <option key={item.name} value={item.name}>
                      {item.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Session
                <select
                  value={session?.id || ""}
                  onChange={(e) => {
                    const found = sessions.find((item) => item.id === e.target.value);
                    if (found) void loadSession(found);
                  }}
                >
                  <option value="">New session</option>
                  {sessions.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.model} · {item.status} · {item.id.slice(0, 8)}
                    </option>
                  ))}
                </select>
              </label>
              <span className="workspace-label">{settings?.workspace_root || "Loading workspace policy…"}</span>
            </div>

            <div className="safety-banner">
              <b>{session?.dry_run ?? settings?.dry_run_default ? "Dry-run protection active" : "Live apply mode"}</b>
              <span>
                {session?.dry_run ?? settings?.dry_run_default
                  ? "Every mutation is rendered as a proposal; no workspace content changes."
                  : "Mutations still require an approval record unless you explicitly remember a scoped action."}
              </span>
            </div>

            {running && (
              <div className="telemetry-bar">
                <span>Streaming tokens: <b>{tokenCount}</b></span>
                <span>Speed: <b>{tokensPerSec > 0 ? `${tokensPerSec} tok/s` : "calculating…"}</b></span>
                <span>Status: <b>Active generation</b></span>
              </div>
            )}

            <div className="transcript">
              {!transcript.length && (
                <div className="empty">
                  <b>Start with a focused workspace request.</b>
                  <p>The agent can search and read within the configured root. Edits, deletes, commits, checkout, and execution are approval-gated.</p>
                </div>
              )}
              {transcript.map((item) =>
                item.role === "tool" ? (
                  <ToolCallCard
                    key={item.id}
                    name={item.name || "tool"}
                    argumentsValue={item.args}
                    result={item.result}
                    dryRun={item.dryRun}
                    pending={item.pending}
                    onRestore={
                      typeof item.args === "object" && item.args !== null && "path" in item.args && typeof (item.args as { path?: unknown }).path === "string"
                        ? (snapshot) => void restore(snapshot, (item.args as { path: string }).path)
                        : undefined
                    }
                  />
                ) : (
                  <article key={item.id} className={`bubble ${item.role}`}>
                    <span>{item.role === "user" ? "You" : "Agent"}</span>
                    <p>{item.content}</p>
                  </article>
                )
              )}
              {liveText && (
                <article className="bubble assistant streaming">
                  <span>Agent · streaming ({tokenCount} tokens)</span>
                  <p>{liveText}</p>
                </article>
              )}
            </div>

            <form className="composer" onSubmit={submit}>
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Ask the local agent to inspect, search, or propose a scoped change…"
                disabled={running}
              />
              <button type="submit" disabled={running || !prompt.trim()}>
                {running ? "Running…" : "Run agent"}
              </button>
            </form>
          </section>
        )}

        {activeTab === "approvals" && (
          <section className="stack">
            {approvals.length ? (
              approvals.map((item) => (
                <ApprovalModal key={item.id} item={item} onResolve={(approved, remember) => void resolve(item, approved, remember)} />
              ))
            ) : (
              <div className="empty">
                <b>No pending approvals.</b>
                <p>Mutations pause the agent here before anything is applied.</p>
              </div>
            )}
          </section>
        )}

        {activeTab === "files" && (
          <div className="stack">
            <div className="filter-bar">
              <form onSubmit={runSemanticSearch} style={{ display: "flex", gap: "8px", flex: 1 }}>
                <input
                  type="text"
                  placeholder="Semantic code search (e.g. 'find session store SQLite queries')..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  style={{ flex: 1, maxWidth: "none" }}
                />
                <button type="submit" className="btn-sm" disabled={isSearching || !searchQuery.trim()}>
                  {isSearching ? "Searching…" : "Semantic Search"}
                </button>
              </form>
              <button className="secondary btn-sm" onClick={triggerIndexRefresh} disabled={isIndexing}>
                {isIndexing ? "Indexing…" : "Refresh Workspace Index"}
              </button>
            </div>

            {searchResults.length > 0 && (
              <div style={{ background: "var(--panel)", padding: "12px", borderRadius: "8px", border: "1px solid var(--line)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                  <b>Semantic Search Results ({searchResults.length})</b>
                  <button className="secondary btn-sm" onClick={() => setSearchResults([])}>Close Results</button>
                </div>
                <div className="stack">
                  {searchResults.map((res: any, idx: number) => (
                    <div key={idx} style={{ padding: "8px", background: "var(--bg)", borderRadius: "6px", fontSize: "12px" }}>
                      <div style={{ color: "var(--accent)", marginBottom: "4px" }}>
                        <strong>{res.path}</strong> <small style={{ color: "var(--muted)" }}>(score: {Math.round((res.similarity || 0) * 100)}%)</small>
                      </div>
                      <pre style={{ margin: 0, fontSize: "11px", maxHeight: "120px" }}>{res.content || res.chunk}</pre>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <section className="files-layout">
              <div className="file-list">
                {files.map((item) => (
                  <button
                    key={item.path}
                    onClick={() =>
                      item.type === "file" &&
                      getJson<any>(`/api/files/content?path=${encodeURIComponent(item.path)}`)
                        .then(setPreview)
                        .catch((cause) => setError(String(cause)))
                    }
                  >
                    <span>{item.type === "dir" ? "▾" : "·"}</span>
                    {item.path}
                    <small>{item.size ?? ""}</small>
                  </button>
                ))}
              </div>
              <div className="file-preview">
                {preview ? (
                  <>
                    <h3>{preview.path}</h3>
                    <pre>{preview.content}</pre>
                  </>
                ) : (
                  <div className="empty">
                    <b>Read-only file preview</b>
                    <p>Select a text file. Credential-shaped paths and files beyond the read limit are denied by the backend.</p>
                  </div>
                )}
              </div>
            </section>
          </div>
        )}

        {activeTab === "audit" && (
          <section className="audit-table">
            <div className="audit-note">
              Append-only JSONL + SQLite mirror. Sensitive-looking fields are redacted before persistence.
            </div>
            <div className="filter-bar">
              <input
                type="text"
                placeholder="Search target or payload…"
                value={auditQuery}
                onChange={(e) => setAuditQuery(e.target.value)}
              />
              <select value={auditActor} onChange={(e) => setAuditActor(e.target.value)}>
                <option value="">All Actors</option>
                <option value="user">User</option>
                <option value="agent">Agent</option>
              </select>
              <select value={auditAction} onChange={(e) => setAuditAction(e.target.value)}>
                <option value="">All Actions</option>
                <option value="session_create">session_create</option>
                <option value="session_fork">session_fork</option>
                <option value="dry_run_toggle">dry_run_toggle</option>
                <option value="kill_switch">kill_switch</option>
                <option value="approval_resolve">approval_resolve</option>
                <option value="tool_call">tool_call</option>
              </select>
              <select value={auditResult} onChange={(e) => setAuditResult(e.target.value)}>
                <option value="">All Results</option>
                <option value="success">Success</option>
                <option value="denied">Denied</option>
                <option value="error">Error</option>
                <option value="proposed">Proposed</option>
              </select>
              <button className="btn-sm" onClick={() => void refreshAudit()}>Filter</button>
              <button
                className="secondary btn-sm"
                onClick={() => {
                  setAuditQuery("");
                  setAuditActor("");
                  setAuditAction("");
                  setAuditResult("");
                  void refresh();
                }}
              >
                Reset
              </button>
              <button className="secondary btn-sm" style={{ marginLeft: "auto" }} onClick={exportAuditCsv}>
                Export CSV
              </button>
            </div>
            <table>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Actor</th>
                  <th>Action</th>
                  <th>Target</th>
                  <th>Result</th>
                </tr>
              </thead>
              <tbody>
                {visibleAudit.map((item) => (
                  <tr key={item.id}>
                    <td>{new Date(item.created_at).toLocaleTimeString()}</td>
                    <td>{item.actor}</td>
                    <td>{item.action_type}</td>
                    <td>{item.target || "—"}</td>
                    <td>
                      <span className={`badge ${item.result === "denied" || item.result === "error" ? "warn" : ""}`}>
                        {item.result}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!audit.length && (
              <div className="empty">
                <b>No audit entries match filter criteria.</b>
              </div>
            )}
          </section>
        )}

        {activeTab === "settings" && (
          <section className="settings-card">
            <h2>Immutable safety configuration</h2>
            <p>
              These values are loaded on backend startup. The UI is deliberately read-only: an agent cannot modify its own sandbox, allowlist, rate limits, or approval policy.
            </p>
            <dl>
              <dt>Workspace root</dt>
              <dd>{settings?.workspace_root}</dd>
              <dt>Max iterations</dt>
              <dd>{settings?.limits?.max_iterations}</dd>
              <dt>Wall-clock cap</dt>
              <dd>{settings?.limits?.max_wall_clock_seconds}s</dd>
              <dt>Execution policy</dt>
              <dd>
                {settings?.execution?.os_sandbox_required
                  ? "Linux user/mount/network/PID namespace required; fail-closed if unavailable"
                  : "Enabled only with argv allowlist"}
              </dd>
              <dt>Configured binaries</dt>
              <dd>{settings?.execution?.allowlist?.join(", ")}</dd>
            </dl>
            <p className="muted">
              Rate limiting protects local GPU/CPU health, establishes backpressure for concurrent sessions, and prevents runaway agent loops. It is not a cloud billing control.
            </p>
          </section>
        )}
      </section>
    </main>
  );
}
