from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from app.cli_runtime import (
    RuntimeMetadata,
    ServeOptions,
    load_running_metadata,
    shutdown_background_server,
    start_background_server,
)
from app.menubar_summary import MenuBarSnapshot

_CODEX_PROVIDER_BIN_ENV = "CODEX_PROVIDER_BIN"
_CODEX_PROVIDER_COMMAND = "codex-provider"
_PROVIDER_SEARCH_PATHS = (
    Path.home() / ".local" / "bin",
    Path("/opt/homebrew/bin"),
    Path("/usr/local/bin"),
    Path("/usr/bin"),
    Path("/bin"),
)


@dataclass(frozen=True, slots=True)
class MenuBarRuntimeOptions:
    host: str
    port: int
    ssl_certfile: str | None
    ssl_keyfile: str | None
    pid_file: Path
    log_file: Path
    startup_timeout_seconds: float
    start_on_launch: bool


@dataclass(frozen=True, slots=True)
class ProviderSyncResult:
    succeeded: bool
    message: str


@dataclass(frozen=True, slots=True)
class MenuBarRuntimeStatus:
    running: bool
    pid: int | None
    host: str
    port: int
    dashboard_url: str
    log_file: Path
    stale_metadata_removed: bool


def get_menu_bar_runtime_status(
    *,
    pid_file: Path,
    log_file: Path,
    default_host: str,
    default_port: int,
    dashboard_scheme: str = "http",
) -> MenuBarRuntimeStatus:
    metadata, stale = load_running_metadata(pid_file)
    if metadata is None:
        return MenuBarRuntimeStatus(
            running=False,
            pid=None,
            host=default_host,
            port=default_port,
            dashboard_url=dashboard_url(default_host, default_port, scheme=dashboard_scheme),
            log_file=log_file.expanduser(),
            stale_metadata_removed=stale,
        )

    return MenuBarRuntimeStatus(
        running=True,
        pid=metadata.pid,
        host=metadata.host,
        port=metadata.port,
        dashboard_url=dashboard_url(metadata.host, metadata.port, scheme=dashboard_scheme),
        log_file=Path(metadata.log_file).expanduser(),
        stale_metadata_removed=stale,
    )


def status_from_options(options: MenuBarRuntimeOptions) -> MenuBarRuntimeStatus:
    return get_menu_bar_runtime_status(
        pid_file=options.pid_file,
        log_file=options.log_file,
        default_host=options.host,
        default_port=options.port,
        dashboard_scheme=dashboard_scheme_for_options(options),
    )


def start_menu_bar_runtime(options: MenuBarRuntimeOptions) -> RuntimeMetadata:
    return start_background_server(
        ServeOptions(
            host=options.host,
            port=options.port,
            ssl_certfile=options.ssl_certfile,
            ssl_keyfile=options.ssl_keyfile,
        ),
        pid_file=options.pid_file,
        log_file=options.log_file,
        startup_timeout_seconds=options.startup_timeout_seconds,
    )


def stop_menu_bar_runtime(options: MenuBarRuntimeOptions) -> RuntimeMetadata | None:
    return shutdown_background_server(options.pid_file)


def resolve_codex_provider_command() -> Path | None:
    configured = os.getenv(_CODEX_PROVIDER_BIN_ENV)
    if configured:
        configured_path = Path(configured).expanduser()
        if configured_path.is_file():
            return configured_path
        return None

    executable = shutil.which(_CODEX_PROVIDER_COMMAND, path=_codex_provider_search_path())
    return None if executable is None else Path(executable)


def _codex_provider_search_path() -> str:
    paths: list[str] = []

    def add_path(path: Path | str | None) -> None:
        if path is None:
            return
        value = str(path)
        if value and value not in paths:
            paths.append(value)

    add_path(Path(sys.executable).resolve().parent)
    for path in os.getenv("PATH", "").split(os.pathsep):
        add_path(path)
    for path in _PROVIDER_SEARCH_PATHS:
        add_path(path)
    return os.pathsep.join(paths)


def _codex_provider_env() -> dict[str, str]:
    env: dict[str, str] = {}
    for key in ("HOME", "USER", "LOGNAME", "SHELL", "CODEX_HOME"):
        value = os.getenv(key)
        if value is not None:
            env[key] = value
    env["PATH"] = _codex_provider_search_path()
    return env


def sync_codex_provider(*, timeout_seconds: float = 120.0) -> ProviderSyncResult:
    command = resolve_codex_provider_command()
    if command is None:
        configured = os.getenv(_CODEX_PROVIDER_BIN_ENV)
        message = (
            f"codex-provider command not found at {configured}" if configured else "codex-provider command not found"
        )
        return ProviderSyncResult(succeeded=False, message=message)

    try:
        completed = subprocess.run(
            [str(command), "sync"],
            capture_output=True,
            check=False,
            env=_codex_provider_env(),
            text=True,
            timeout=timeout_seconds,
        )
    except FileNotFoundError:
        return ProviderSyncResult(
            succeeded=False,
            message="codex-provider command not found",
        )
    except OSError as exc:
        return ProviderSyncResult(
            succeeded=False,
            message=f"codex-provider sync failed: {exc}",
        )
    except subprocess.TimeoutExpired:
        return ProviderSyncResult(
            succeeded=False,
            message=f"codex-provider sync timed out after {timeout_seconds:g}s",
        )

    output = (completed.stderr or completed.stdout).strip()
    if completed.returncode == 0:
        return ProviderSyncResult(succeeded=True, message=output or "Provider sync completed")
    return ProviderSyncResult(
        succeeded=False,
        message=output or f"codex-provider sync exited with status {completed.returncode}",
    )


def stopped_runtime_snapshot(status: MenuBarRuntimeStatus) -> MenuBarSnapshot:
    status_label = "Stopped"
    if status.stale_metadata_removed:
        status_label = "Stopped (stale PID removed)"
    return MenuBarSnapshot(
        title="Stopped",
        rows=(
            ("Status", status_label),
            ("Dashboard", status.dashboard_url),
            ("Log file", str(status.log_file)),
        ),
        error_message=status_label,
    )


def dashboard_scheme_for_options(options: MenuBarRuntimeOptions | ServeOptions) -> str:
    return "https" if options.ssl_certfile and options.ssl_keyfile else "http"


def dashboard_url(host: str, port: int, *, scheme: str = "http") -> str:
    dashboard_host = "127.0.0.1" if host in {"", "0.0.0.0", "::"} else host
    if ":" in dashboard_host and not dashboard_host.startswith("["):
        dashboard_host = f"[{dashboard_host}]"
    return f"{scheme}://{dashboard_host}:{port}"


def dashboard_page_url(base_url: str) -> str:
    return f"{base_url.rstrip('/')}/dashboard"
