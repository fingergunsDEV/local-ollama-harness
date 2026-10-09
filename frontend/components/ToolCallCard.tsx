"use client";

type Props = { name: string; argumentsValue?: unknown; result?: unknown; dryRun?: boolean; pending?: boolean; onRestore?: (snapshot: string) => void };
export default function ToolCallCard({ name, argumentsValue, result, dryRun, pending, onRestore }: Props) {
  const snapshot = typeof result === "object" && result !== null && "snapshot" in result && typeof (result as { snapshot?: unknown }).snapshot === "string" ? (result as { snapshot: string }).snapshot : null;
  return <article className={`tool-card ${dryRun ? "proposed" : ""}`}>
    <div className="tool-heading"><strong>{name}</strong><span className={`badge ${pending ? "warn" : dryRun ? "proposed" : "applied"}`}>{pending ? "approval pending" : dryRun ? "proposed (dry run)" : "tool result"}</span></div>
    {argumentsValue !== undefined && <pre className="compact">{JSON.stringify(argumentsValue, null, 2)}</pre>}
    {result !== undefined && <pre className="result">{JSON.stringify(result, null, 2)}</pre>}
    {snapshot && onRestore && <button className="secondary restore" onClick={() => onRestore(snapshot)}>Restore pre-change snapshot</button>}
  </article>;
}
