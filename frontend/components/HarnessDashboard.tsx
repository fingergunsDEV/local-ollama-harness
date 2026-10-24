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

  // Audit filter state
  const [auditQuery, setAuditQuery] = useState("");
  const [auditActionType, setAuditActionType] = useState("");
  const [auditResult, setAuditResult] = useState("");

  // Semantic index and search state
  const [refreshingIndex, setRefreshingIndex] = useState(false);
  const [indexMessage, setIndexMessage] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [searching, setSearching] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const [s, modelsData, sessionsData, rateData, approvalsData, filesData, auditData] = await Promise.all([
        getJson<any>("/api/settings"),
        getJson<any>("/api/models"),
        getJson<any>("/api/sessions"),
        getJson<any>("/api/rate-status"),
        getJson<any>("/api/approvals"),
        getJson<any>("/api/files?path=.&depth=3"),
        getJson<any>("/api/audit")
      ]);
      setSettings(s); setModels(modelsData.models || []); setModel((current) => current || modelsData.models?.[0]?.name || ""); setSessions(sessionsData.sessions || []); setRate(rateData); setApprovals(approvalsData.approvals || []); setFiles(filesData.entries || []); setAudit(auditData.entries || []); setError("");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to reach the local backend"); }
  }, []);

  useEffect(() => { void refresh(); const id = window.setInterval(() => { void getJson<any>("/api/rate-status").then(setRate).catch(() => undefined); void getJson<any>("/api/approvals").then(x => setApprovals(x.approvals || [])).catch(() => undefined); }, 2500); return () => window.clearInterval(id); }, [refresh]);

  const loadSession = async (candidate: Session) => { try { const data = await getJson<any>(`/api/sessions/${candidate.id}`); setSession(data.session); setTranscript((data.messages || []).map((m: any) => { if (m.role !== "tool") return { id: m.id, role: m.role, content: m.content }; try { return { id: m.id, role: "tool", name: "persisted tool result", result: JSON.parse(m.content) }; } catch { return { id: m.id, role: "tool", name: "persisted tool result", result: { content: m.content } }; } })); setActiveTab("chat"); } catch (cause) { setError(String(cause)); } };
  const ensureSession = async (): Promise<Session> => { if (session) return session; if (!model) throw new Error("Select an installed Ollama model first"); const created = await postJson<Session>("/api/sessions", { model }); setSessions(items => [created, ...items]); setSession(created); return created; };
  const toggleDryRun = async () => { if (!session) return; const changed = await postJson<Session>(`/api/sessions/${session.id}/dry-run`, { dry_run: !session.dry_run }); setSession(current => current ? { ...current, dry_run: changed.dry_run } : current); setSessions(items => items.map(item => item.id === changed.id ? changed : item)); };
  const resolve = async (item: Approval, approved: boolean, remember: boolean) => { await postJson(`/api/approvals/${item.id}/resolve`, { approved, remember_for_session: remember }); await refresh(); };
  const stop = async () => { if (session) await postJson(`/api/sessions/${session.id}/kill`); };
  const restore = async (snapshot: string, path: string) => { try { await postJson("/api/snapshots/restore", { snapshot_id: snapshot, path }); setError(""); await refresh(); } catch (cause) { setError(cause instanceof Error ? cause.message : "Snapshot restore failed"); } };

  // Export & Fork handlers
  const exportSession = (format: "markdown" | "json") => {
    if (!session) return;
    window.open(`${API}/api/sessions/${session.id}/export?format=${format}`, "_blank");
  };

  const forkSession = async () => {
    if (!session) return;
    try {
      const created = await postJson<Session>(`/api/sessions/${session.id}/fork`);
      setSessions(items => [created, ...items]);
      await loadSession(created);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Failed to fork session");
    }
  };

  // Filtered Audit Handlers
  const refreshFilteredAudit = useCallback(async (query: string, actionType: string, result: string) => {
    try {
      const params = new URLSearchParams();
      if (query.trim()) params.set("query", query.trim());
      if (actionType) params.set("action_type", actionType);
      if (result) params.set("result", result);
      const data = await getJson<any>(`/api/audit?${params.toString()}`);
      setAudit(data.entries || []);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Failed to fetch audit log");
    }
  }, []);

  const exportAuditCsv = () => {
    const params = new URLSearchParams();
    params.set("format", "csv");
    if (auditQuery.trim()) params.set("query", auditQuery.trim());
    if (auditActionType) params.set("action_type", auditActionType);
    if (auditResult) params.set("result", auditResult);
    window.open(`${API}/api/audit?${params.toString()}`, "_blank");
  };

  // Index and Search Handlers
  const handleRefreshIndex = async () => {
    try {
      setRefreshingIndex(true);
      setIndexMessage("");
      const res = await postJson<any>("/api/index/refresh");
      setIndexMessage(`Index refreshed: ${res.indexed_chunks || res.indexed || res.chunks || 0} chunks indexed.`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Index refresh failed");
    } finally {
      setRefreshingIndex(false);
    }
  };

  const handleSemanticSearch = async (e: FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    try {
      setSearching(true);
      const res = await postJson<any>("/api/search/semantic", { query: searchQuery.trim(), top_k: 5 });
      setSearchResults(res.results || []);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Semantic search failed");
    } finally {
      setSearching(false);
    }
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault(); const message = prompt.trim(); if (!message || running) return;
    try {
      const current = await ensureSession(); setPrompt(""); setRunning(true); setError(""); setLiveText(""); const userItem: Transcript = { id: crypto.randomUUID(), role: "user", content: message }; setTranscript(items => [...items, userItem]);
      const response = await fetch(`${API}/api/sessions/${current.id}/run`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message }) }); if (!response.ok || !response.body) throw new Error(await response.text());
      const reader = response.body.getReader(); const decoder = new TextDecoder(); let buffer = ""; let eventName = "message";
      const receive = (raw: string) => { for (const line of raw.split("\n")) { if (line.startsWith("event: ")) eventName = line.slice(7); if (line.startsWith("data: ")) { const payload = JSON.parse(line.slice(6)); handleEvent(eventName, payload); } } };
      const handleEvent = (type: string, data: any) => { if (type === "token") setLiveText(value => value + data.content); else if (type === "assistant_message") { setTranscript(items => [...items, { id: crypto.randomUUID(), role: "assistant", content: data.content }]); setLiveText(""); } else if (type === "tool_call_start") { setTranscript(items => [...items, { id: data.tool_call_id, role: "tool", name: data.name, args: data.arguments, dryRun: data.dry_run, pending: false }]); } else if (type === "tool_call_result") setTranscript(items => items.map(item => item.id === data.tool_call_id ? { ...item, result: data.result, pending: false } : item)); else if (type === "approval_required") { setTranscript(items => items.map(item => item.id === data.tool_call_id ? { ...item, pending: true } : item)); void getJson<any>("/api/approvals").then(result => setApprovals(result.approvals || [])); } else if (type === "run_error") setError(data.message); };
      while (true) { const { value, done } = await reader.read(); if (done) break; buffer += decoder.decode(value, { stream: true }); let boundary; while ((boundary = buffer.indexOf("\n\n")) !== -1) { receive(buffer.slice(0, boundary)); buffer = buffer.slice(boundary + 2); eventName = "message"; } }
      await refresh();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Run failed"); } finally { setRunning(false); }
  };

  const visibleAudit = useMemo(() => audit.slice(0, 80), [audit]);

  return <main className="shell">
    <aside className="sidebar"><div className="brand"><span className="brand-mark">◉</span><div><b>LOCAL HARNESS</b><small>Ollama · workspace-bound</small></div></div><nav>{[["chat","Chat"],["files","Files"],["approvals",`Approvals ${approvals.length ? `(${approvals.length})` : ""}`],["audit","Audit"],["settings","Settings"]].map(([key,label]) => <button key={key} className={activeTab === key ? "nav-active" : ""} onClick={() => setActiveTab(key)}>{label}</button>)}</nav><section className="sidebar-foot"><p>Outbound inference is restricted to the configured loopback Ollama daemon.</p><RateLimitBadge status={rate}/></section></aside>
    <section className="content"><header className="topbar"><div><span className="eyebrow">SAFETY CONTROL PLANE</span><h1>{activeTab === "chat" ? "Agent session" : activeTab[0].toUpperCase() + activeTab.slice(1)}</h1></div><div className="top-actions">{session && <button className={`toggle ${session.dry_run ? "on" : ""}`} onClick={toggleDryRun} title="Changing dry-run is a logged user action">Dry run {session.dry_run ? "ON" : "OFF"}</button>}<KillSwitch disabled={!running} onKill={() => void stop()}/></div></header>
      {error && <div className="notice error"><strong>Local backend notice:</strong> {error}</div>}
      {activeTab === "chat" && <section className="chat-layout"><div className="session-strip"><label>Model <select value={model} onChange={e => setModel(e.target.value)} disabled={!!session}>{!models.length && <option value="">No local models discovered</option>}{models.map(item => <option key={item.name} value={item.name}>{item.name}</option>)}</select></label><label>Session <select value={session?.id || ""} onChange={e => { const found = sessions.find(item => item.id === e.target.value); if (found) void loadSession(found); }}><option value="">New session</option>{sessions.map(item => <option key={item.id} value={item.id}>{item.model} · {item.status} · {item.id.slice(0, 8)}</option>)}</select></label>{session && <div style={{ display: "flex", gap: "6px", alignItems: "flex-end" }}><button type="button" className="secondary" onClick={() => exportSession("markdown")} title="Export session transcript as Markdown">Export MD</button><button type="button" className="secondary" onClick={() => exportSession("json")} title="Export session transcript as JSON">Export JSON</button><button type="button" className="secondary" onClick={() => void forkSession()} title="Fork session at this checkpoint">Fork Session</button></div>}<span className="workspace-label">{settings?.workspace_root || "Loading workspace policy…"}</span></div><div className="safety-banner"><b>{session?.dry_run ?? settings?.dry_run_default ? "Dry-run protection active" : "Live apply mode"}</b><span>{session?.dry_run ?? settings?.dry_run_default ? "Every mutation is rendered as a proposal; no workspace content changes." : "Mutations still require an approval record unless you explicitly remember a scoped action."}</span></div><div className="transcript">{!transcript.length && <div className="empty"><b>Start with a focused workspace request.</b><p>The agent can search and read within the configured root. Edits, deletes, commits, checkout, and execution are approval-gated.</p></div>}{transcript.map(item => item.role === "tool" ? <ToolCallCard key={item.id} name={item.name || "tool"} argumentsValue={item.args} result={item.result} dryRun={item.dryRun} pending={item.pending} onRestore={typeof item.args === "object" && item.args !== null && "path" in item.args && typeof (item.args as { path?: unknown }).path === "string" ? (snapshot) => void restore(snapshot, (item.args as { path: string }).path) : undefined}/> : <article key={item.id} className={`bubble ${item.role}`}><span>{item.role === "user" ? "You" : "Agent"}</span><p>{item.content}</p></article>)}{liveText && <article className="bubble assistant streaming"><span>Agent · streaming</span><p>{liveText}</p></article>}</div><form className="composer" onSubmit={submit}><textarea value={prompt} onChange={e => setPrompt(e.target.value)} placeholder="Ask the local agent to inspect, search, or propose a scoped change…" disabled={running}/><button type="submit" disabled={running || !prompt.trim()}>{running ? "Running…" : "Run agent"}</button></form></section>}
      {activeTab === "approvals" && <section className="stack">{approvals.length ? approvals.map(item => <ApprovalModal key={item.id} item={item} onResolve={(approved, remember) => void resolve(item, approved, remember)}/>) : <div className="empty"><b>No pending approvals.</b><p>Mutations pause the agent here before anything is applied.</p></div>}</section>}
      {activeTab === "files" && <section className="stack"><div className="tool-card" style={{ display: "flex", flexWrap: "wrap", gap: "10px", alignItems: "center", justifyContent: "space-between" }}><div style={{ display: "flex", gap: "8px", alignItems: "center" }}><button type="button" onClick={() => void handleRefreshIndex()} disabled={refreshingIndex}>{refreshingIndex ? "Indexing…" : "Refresh Workspace Index"}</button>{indexMessage && <small className="muted">{indexMessage}</small>}</div><form onSubmit={handleSemanticSearch} style={{ display: "flex", gap: "8px", flex: 1, maxWidth: "500px" }}><input type="text" value={searchQuery} onChange={e => setSearchQuery(e.target.value)} placeholder="Semantic vector search across workspace..." style={{ flex: 1, padding: "8px", background: "var(--panel)", border: "1px solid var(--line)", borderRadius: "6px", color: "var(--ink)" }}/><button type="submit" disabled={searching || !searchQuery.trim()}>{searching ? "Searching…" : "Search"}</button></form></div>{searchResults.length > 0 && <div className="tool-card"><h3>Semantic Search Results</h3><div style={{ display: "grid", gap: "8px" }}>{searchResults.map((res: any, i: number) => <div key={i} className="result" style={{ borderLeft: "3px solid var(--accent)" }}><strong>{res.file_path || res.path}</strong> <small className="muted">(score: {typeof res.score === "number" ? res.score.toFixed(3) : res.similarity})</small><pre>{res.chunk_text || res.content}</pre></div>)}</div></div>}<div className="files-layout"><div className="file-list">{files.map(item => <button key={item.path} onClick={() => item.type === "file" && getJson<any>(`/api/files/content?path=${encodeURIComponent(item.path)}`).then(setPreview).catch(cause => setError(String(cause)))}><span>{item.type === "dir" ? "▾" : "·"}</span>{item.path}<small>{item.size ?? ""}</small></button>)}</div><div className="file-preview">{preview ? <><h3>{preview.path}</h3><pre>{preview.content}</pre></> : <div className="empty"><b>Read-only file preview</b><p>Select a text file. Credential-shaped paths and files beyond the read limit are denied by the backend.</p></div>}</div></div></section>}
      {activeTab === "audit" && <section className="audit-table"><div className="audit-note" style={{ display: "flex", flexWrap: "wrap", gap: "10px", alignItems: "center", justifyContent: "space-between" }}><div>Append-only JSONL + SQLite mirror. Sensitive-looking fields are redacted before persistence.</div><button type="button" className="secondary" onClick={exportAuditCsv}>Export Audit CSV</button></div><div style={{ display: "flex", flexWrap: "wrap", gap: "10px", padding: "12px", background: "#0f1723", borderBottom: "1px solid var(--line)" }}><input type="text" value={auditQuery} onChange={e => { setAuditQuery(e.target.value); void refreshFilteredAudit(e.target.value, auditActionType, auditResult); }} placeholder="Filter by text query..." style={{ padding: "7px 10px", background: "var(--panel)", border: "1px solid var(--line)", borderRadius: "6px", color: "var(--ink)", minWidth: "200px" }}/><select value={auditActionType} onChange={e => { setAuditActionType(e.target.value); void refreshFilteredAudit(auditQuery, e.target.value, auditResult); }}><option value="">All Action Types</option><option value="session_create">session_create</option><option value="session_fork">session_fork</option><option value="dry_run_toggle">dry_run_toggle</option><option value="file_write">file_write</option><option value="command_exec">command_exec</option><option value="approval_resolve">approval_resolve</option><option value="snapshot_restore">snapshot_restore</option><option value="kill_switch">kill_switch</option></select><select value={auditResult} onChange={e => { setAuditResult(e.target.value); void refreshFilteredAudit(auditQuery, auditActionType, e.target.value); }}><option value="">All Results</option><option value="success">success</option><option value="approved">approved</option><option value="denied">denied</option><option value="error">error</option></select></div><table><thead><tr><th>Time</th><th>Actor</th><th>Action</th><th>Target</th><th>Result</th></tr></thead><tbody>{visibleAudit.map(item => <tr key={item.id}><td>{new Date(item.created_at).toLocaleTimeString()}</td><td>{item.actor}</td><td>{item.action_type}</td><td>{item.target || "—"}</td><td><span className={`badge ${item.result === "denied" || item.result === "error" ? "warn" : ""}`}>{item.result}</span></td></tr>)}</tbody></table>{!audit.length && <div className="empty"><b>Audit trail will appear here.</b></div>}</section>}
      {activeTab === "settings" && <section className="settings-card"><h2>Immutable safety configuration</h2><p>These values are loaded on backend startup. The UI is deliberately read-only: an agent cannot modify its own sandbox, allowlist, rate limits, or approval policy.</p><dl><dt>Workspace root</dt><dd>{settings?.workspace_root}</dd><dt>Max iterations</dt><dd>{settings?.limits?.max_iterations}</dd><dt>Wall-clock cap</dt><dd>{settings?.limits?.max_wall_clock_seconds}s</dd><dt>Execution policy</dt><dd>{settings?.execution?.os_sandbox_required ? "Linux user/mount/network/PID namespace required; fail-closed if unavailable" : "Enabled only with argv allowlist"}</dd><dt>Configured binaries</dt><dd>{settings?.execution?.allowlist?.join(", ")}</dd></dl><p className="muted">Rate limiting protects local GPU/CPU health, establishes backpressure for concurrent sessions, and prevents runaway agent loops. It is not a cloud billing control.</p></section>}
    </section>
  </main>;
}
