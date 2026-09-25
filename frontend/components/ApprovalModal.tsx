"use client";

type Approval = { id: string; action_type: string; diff_or_plan: string; session_id: string };
export default function ApprovalModal({ item, onResolve }: { item: Approval; onResolve: (approved: boolean, remember: boolean) => void }) {
  return <article className="approval"><div><span className="badge warn">approval required</span><h3>{item.action_type}</h3><p className="muted">Session {item.session_id.slice(0, 8)}</p></div><pre className="diff">{item.diff_or_plan}</pre><div className="approval-actions"><button className="danger" onClick={() => onResolve(false, false)}>Deny</button><button onClick={() => onResolve(true, false)}>Approve once</button><button className="secondary" onClick={() => onResolve(true, true)}>Approve &amp; remember this session</button></div></article>;
}
