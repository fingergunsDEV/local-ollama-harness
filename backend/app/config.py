from __future__ import annotations

import ipaddress
import socket
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class SecurityConfigurationError(RuntimeError):
    """Raised for a configuration that weakens the local-only safety boundary."""


class Settings(BaseSettings):
    """All security-sensitive runtime configuration.

    Defaults are conservative, but WORKSPACE_ROOT deliberately has no default: an operator
    must choose a dedicated workspace rather than accidentally exposing a broad directory.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ollama_host: str = "http://127.0.0.1:11434"
    allow_remote_ollama: bool = False
    default_model: str = ""

    workspace_root: Path
    follow_symlinks: bool = False
    denylist_names: str = ".env,.env.local,.env.production,.git/config,.harness-snapshots,id_rsa,id_ed25519,credentials"

    rate_limit_rpm: int = Field(default=20, ge=1, le=10_000)
    max_concurrent_requests: int = Field(default=2, ge=1, le=64)
    cooldown_seconds: int = Field(default=30, ge=1, le=3600)
    cooldown_trigger_count: int = Field(default=3, ge=1, le=100)

    max_iterations: int = Field(default=25, ge=1, le=500)
    max_wall_clock_seconds: int = Field(default=600, ge=1, le=86_400)
    max_output_tokens_per_turn: int = Field(default=2048, ge=64, le=65_536)
    max_total_tokens_per_session: int = Field(default=100_000, ge=256, le=10_000_000)

    max_file_read_bytes: int = Field(default=1_000_000, ge=1, le=100_000_000)
    max_file_write_bytes: int = Field(default=2_000_000, ge=1, le=100_000_000)
    max_files_indexed: int = Field(default=20_000, ge=1, le=1_000_000)

    exec_allowlist: str = "git,ls,cat,grep,rg,python3,pytest,npm,node,pip"
    exec_timeout_seconds: int = Field(default=60, ge=1, le=3600)
    # There is no safe fallback for arbitrary process execution without a separately
    # verified OS sandbox. The executor denies commands while this remains true.
    exec_require_os_sandbox: bool = True

    require_approval_for: str = "write,delete,exec,git_commit,git_checkout"
    auto_approve: str = ""
    dry_run_default: bool = True

    audit_log_path: Path = Path("./data/audit.log")
    sqlite_path: Path = Path("./data/harness.db")
    backend_bind_host: str = "127.0.0.1"
    backend_port: int = Field(default=8000, ge=1, le=65535)
    frontend_origin: str = "http://localhost:3000"

    @field_validator("workspace_root")
    @classmethod
    def validate_workspace_exists(cls, value: Path) -> Path:
        root = value.expanduser().resolve()
        suspicious = {Path("/").resolve(), Path.home().resolve(), Path("/home").resolve(), Path("/tmp").resolve()}
        if root in suspicious or len(root.parts) < 3:
            raise ValueError("WORKSPACE_ROOT must be a dedicated non-top-level directory")
        if not root.exists() or not root.is_dir():
            raise ValueError("WORKSPACE_ROOT must exist and be a directory")
        return root

    @model_validator(mode="after")
    def validate_local_ollama(self) -> "Settings":
        parsed = urlparse(self.ollama_host)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("OLLAMA_HOST must be an http(s) URL with a hostname")
        if not self.allow_remote_ollama:
            self._assert_loopback_host(parsed.hostname)
        if self.backend_bind_host not in {"127.0.0.1", "::1", "localhost"}:
            raise ValueError("BACKEND_BIND_HOST must be loopback for a local-only harness")
        return self

    @staticmethod
    def _assert_loopback_host(hostname: str) -> None:
        try:
            addresses = {entry[4][0] for entry in socket.getaddrinfo(hostname, None)}
        except socket.gaierror as exc:
            raise ValueError(f"OLLAMA_HOST hostname cannot be resolved: {hostname}") from exc
        if not addresses:
            raise ValueError("OLLAMA_HOST resolved to no addresses")
        for address in addresses:
            if not ipaddress.ip_address(address).is_loopback:
                raise ValueError(
                    "OLLAMA_HOST must resolve only to loopback addresses; set "
                    "ALLOW_REMOTE_OLLAMA=true only after deliberate operator review"
                )

    @property
    def denylist(self) -> set[str]:
        return {item.strip().lower().replace("\\", "/") for item in self.denylist_names.split(",") if item.strip()}

    @property
    def allowed_commands(self) -> set[str]:
        return {item.strip() for item in self.exec_allowlist.split(",") if item.strip()}

    @property
    def approval_actions(self) -> set[str]:
        return {item.strip() for item in self.require_approval_for.split(",") if item.strip()}

    @property
    def startup_auto_approve(self) -> set[str]:
        return {item.strip() for item in self.auto_approve.split(",") if item.strip()} & self.approval_actions


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load settings once at startup; errors prevent the server from serving requests."""
    return Settings()
