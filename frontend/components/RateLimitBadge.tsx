"use client";
export default function RateLimitBadge({ status }: { status: { tokens_available: number; max_tokens: number; in_flight_limit: number; cooldown_active?: boolean; cooldown_remaining_seconds?: number } | null }) {
  if (!status) return <span className="badge">rate status unavailable</span>;
  return <span className={`badge ${status.cooldown_active ? "warn" : ""}`}>{status.cooldown_active ? `cooldown ${Math.ceil(status.cooldown_remaining_seconds || 0)}s` : `${status.tokens_available.toFixed(0)}/${status.max_tokens} Ollama RPM tokens`} · concurrency {status.in_flight_limit}</span>;
}
