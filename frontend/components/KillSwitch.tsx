"use client";
export default function KillSwitch({ disabled, onKill }: { disabled: boolean; onKill: () => void }) { return <button className="kill" disabled={disabled} onClick={onKill}>Stop run</button>; }
