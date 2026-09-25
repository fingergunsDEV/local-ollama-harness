from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.audit.logger import AuditLogger
from app.config import Settings, get_settings
from app.db.session_store import SessionStore
from app.ollama_client import OllamaClient, OllamaUnavailable
from app.orchestrator import AgentOrchestrator
from app.safety.approval import ApprovalManager
from app.safety.rate_limiter import OllamaRateLimiter
from app.tools import ToolRegistry
from app.streaming import sse_events


class CreateSession(BaseModel):
    model: str = Field(min_length=1, max_length=200)
    dry_run: bool | None = None

class RunRequest(BaseModel):
    message: str = Field(min_length=1, max_length=50_000)

class DryRunUpdate(BaseModel):
    dry_run: bool

class ApprovalResolve(BaseModel):
    approved: bool
    remember_for_session: bool = False

class SnapshotRestore(BaseModel):
    snapshot_id: str = Field(min_length=1, max_length=300)
    path: str = Field(min_length=1, max_length=1000)


class Runtime:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings; self.store = SessionStore(settings.sqlite_path)
        self.limiter = OllamaRateLimiter(settings); self.tools = ToolRegistry(settings)
        self.approvals = ApprovalManager(self.store); self.audit = AuditLogger(self.store, settings.audit_log_path)
        self.ollama = OllamaClient(settings, self.limiter)
        self.orchestrator = AgentOrchestrator(settings, self.store, self.ollama, self.tools, self.approvals, self.audit)


@asynccontextmanager
async def lifespan(app: FastAPI):
    runtime = Runtime(get_settings()); app.state.runtime = runtime
    try:
        await runtime.ollama.health()
    except OllamaUnavailable:
        # The harness stays inspectable when Ollama is offline; runs surface the same clear error.
        pass
    yield
    await runtime.ollama.close()


app = FastAPI(title="Local Ollama Agent Harness", version="0.1.0", lifespan=lifespan)
settings_for_cors = get_settings()
app.add_middleware(CORSMiddleware, allow_origins=[settings_for_cors.frontend_origin], allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["Content-Type"])


def runtime() -> Runtime: return app.state.runtime

def session_or_404(session_id: str) -> dict[str, Any]:
    value = runtime().store.get_session(session_id)
    if not value: raise HTTPException(404, "Session not found")
    return value


@app.get("/api/health")
async def health() -> dict[str, Any]:
    try:
        await runtime().ollama.health(); ollama = "healthy"
    except OllamaUnavailable as exc: ollama = str(exc)
    return {"status": "ok", "ollama": ollama, "workspace_root": str(runtime().settings.workspace_root)}

@app.get("/api/models")
async def models() -> dict[str, Any]:
    try: return {"models": await runtime().ollama.models()}
    except OllamaUnavailable as exc: raise HTTPException(503, str(exc)) from exc

@app.get("/api/models/{model}/capabilities")
async def model_capabilities(model: str) -> dict[str, Any]:
    try: return await runtime().ollama.capabilities(model)
    except OllamaUnavailable as exc: raise HTTPException(503, str(exc)) from exc

@app.get("/api/settings")
async def public_settings() -> dict[str, Any]:
    cfg = runtime().settings
    return {"workspace_root": str(cfg.workspace_root), "git_repository": runtime().tools.git.is_repository(), "dry_run_default": cfg.dry_run_default, "limits": {"max_iterations": cfg.max_iterations, "max_wall_clock_seconds": cfg.max_wall_clock_seconds, "max_output_tokens_per_turn": cfg.max_output_tokens_per_turn, "max_total_tokens_per_session": cfg.max_total_tokens_per_session, "max_file_read_bytes": cfg.max_file_read_bytes, "max_file_write_bytes": cfg.max_file_write_bytes}, "rate_limit": {"rpm": cfg.rate_limit_rpm, "max_concurrent_requests": cfg.max_concurrent_requests, "cooldown_seconds": cfg.cooldown_seconds}, "execution": {"os_sandbox_required": cfg.exec_require_os_sandbox, "allowlist": sorted(cfg.allowed_commands)}}

@app.get("/api/rate-status")
async def rate_status() -> dict[str, Any]: return asdict(await runtime().limiter.status())

@app.post("/api/index/refresh")
async def refresh_index() -> dict[str, Any]:
    # Import lazily so metadata indexing stays an operator-triggered local operation.
    from app.indexing.indexer import LocalIndexer
    return LocalIndexer(runtime().settings, runtime().tools.sandbox, runtime().store).refresh()

@app.get("/api/sessions")
async def list_sessions() -> dict[str, Any]: return {"sessions": runtime().store.list_sessions()}

@app.post("/api/sessions")
async def create_session(request: CreateSession) -> dict[str, Any]:
    cfg = runtime().settings
    record = runtime().store.create_session(request.model, cfg.dry_run_default if request.dry_run is None else request.dry_run, str(cfg.workspace_root))
    runtime().audit.log(session_id=record["id"], actor="user", action_type="session_create", tool_name=None, target=None, result="success", dry_run=record["dry_run"])
    return record

@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str) -> dict[str, Any]:
    session = session_or_404(session_id); return {"session": session, "messages": runtime().store.messages(session_id)}

@app.post("/api/sessions/{session_id}/dry-run")
async def update_dry_run(session_id: str, request: DryRunUpdate) -> dict[str, Any]:
    session_or_404(session_id); runtime().store.set_dry_run(session_id, request.dry_run)
    runtime().audit.log(session_id=session_id, actor="user", action_type="dry_run_toggle", tool_name=None, target=None, result="success", dry_run=request.dry_run)
    return {"id": session_id, "dry_run": request.dry_run}

@app.post("/api/sessions/{session_id}/run")
async def run(session_id: str, request: RunRequest) -> StreamingResponse:
    session_or_404(session_id)
    return StreamingResponse(sse_events(runtime().orchestrator.run(session_id, request.message)), media_type="text/event-stream", headers={"Cache-Control":"no-cache", "X-Accel-Buffering":"no"})

@app.post("/api/sessions/{session_id}/kill")
async def kill(session_id: str) -> dict[str, Any]:
    session_or_404(session_id); stopped = runtime().orchestrator.stop(session_id)
    runtime().audit.log(session_id=session_id, actor="user", action_type="kill_switch", tool_name=None, target=None, result="success" if stopped else "no_active_run", dry_run=False)
    return {"stopped": stopped}

@app.get("/api/approvals")
async def approvals(session_id: str | None = None) -> dict[str, Any]: return {"approvals": runtime().store.pending_approvals(session_id)}

@app.post("/api/approvals/{approval_id}/resolve")
async def resolve_approval(approval_id: str, request: ApprovalResolve) -> dict[str, Any]:
    pending = next((item for item in runtime().store.pending_approvals() if item["id"] == approval_id), None)
    if not pending: raise HTTPException(404, "Pending approval not found")
    await runtime().approvals.resolve(approval_id, request.approved, "user", request.remember_for_session, pending["session_id"], pending["action_type"])
    runtime().audit.log(session_id=pending["session_id"], actor="user", action_type="approval_resolve", tool_name=None, target=pending["tool_call_id"], result="approved" if request.approved else "denied", dry_run=False)
    return {"id": approval_id, "status": "approved" if request.approved else "denied"}

@app.post("/api/snapshots/restore")
async def restore_snapshot(request: SnapshotRestore) -> dict[str, Any]:
    try:
        result = runtime().tools.restore_snapshot(request.snapshot_id, request.path)
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc
    runtime().audit.log(session_id=None, actor="user", action_type="snapshot_restore", tool_name=None, target=request.path, result="success", dry_run=False, params={"snapshot_id": request.snapshot_id}, content_before=result.pop("content_before"), content_after=result.pop("content_after"))
    return result

@app.get("/api/audit")
async def audit(session_id: str | None = None, query: str = "") -> dict[str, Any]: return {"entries": runtime().store.audit_entries(session_id, query)}

@app.get("/api/files")
async def files(path: str = ".", depth: int = 3) -> dict[str, Any]:
    try: return runtime().tools.files.list_files(path, depth)
    except Exception as exc: raise HTTPException(400, str(exc)) from exc

@app.get("/api/files/content")
async def file_content(path: str, offset: int = 0, length: int | None = None) -> dict[str, Any]:
    try: return runtime().tools.files.read_file(path, offset, length)
    except Exception as exc: raise HTTPException(400, str(exc)) from exc
