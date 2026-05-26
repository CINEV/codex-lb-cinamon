from __future__ import annotations

from pathlib import Path
from typing import Any

from app.cli_runtime import RuntimeMetadata
from app.menubar_runtime import (
    MenuBarRuntimeOptions,
    dashboard_page_url,
    dashboard_scheme_for_options,
    dashboard_url,
    get_menu_bar_runtime_status,
    resolve_codex_provider_command,
    start_menu_bar_runtime,
    stopped_runtime_snapshot,
    sync_codex_provider,
)


def test_get_menu_bar_runtime_status_reports_running_metadata(monkeypatch, tmp_path: Path) -> None:
    log_file = tmp_path / "server.log"
    metadata = RuntimeMetadata(pid=1234, host="127.0.0.1", port=2455, log_file=str(log_file))

    monkeypatch.setattr("app.menubar_runtime.load_running_metadata", lambda pid_file: (metadata, False))

    status = get_menu_bar_runtime_status(
        pid_file=tmp_path / "server.pid",
        log_file=tmp_path / "fallback.log",
        default_host="127.0.0.1",
        default_port=2455,
    )

    assert status.running is True
    assert status.pid == 1234
    assert status.dashboard_url == "http://127.0.0.1:2455"
    assert status.log_file == log_file


def test_get_menu_bar_runtime_status_reports_stopped_defaults(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("app.menubar_runtime.load_running_metadata", lambda pid_file: (None, True))

    status = get_menu_bar_runtime_status(
        pid_file=tmp_path / "server.pid",
        log_file=tmp_path / "server.log",
        default_host="0.0.0.0",
        default_port=2455,
    )

    assert status.running is False
    assert status.pid is None
    assert status.dashboard_url == "http://127.0.0.1:2455"
    assert status.stale_metadata_removed is True


def test_start_menu_bar_runtime_uses_background_lifecycle(monkeypatch, tmp_path: Path) -> None:
    runtime = RuntimeMetadata(pid=4321, host="127.0.0.1", port=2455, log_file=str(tmp_path / "server.log"))
    calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
    options = MenuBarRuntimeOptions(
        host="127.0.0.1",
        port=2455,
        ssl_certfile=None,
        ssl_keyfile=None,
        pid_file=tmp_path / "server.pid",
        log_file=tmp_path / "server.log",
        startup_timeout_seconds=3.0,
        start_on_launch=False,
    )

    def fake_start(*args, **kwargs):
        calls.append((args, kwargs))
        return runtime

    monkeypatch.setattr("app.menubar_runtime.start_background_server", fake_start)

    assert start_menu_bar_runtime(options) == runtime
    assert len(calls) == 1


def test_stopped_runtime_snapshot_reports_stopped_state(tmp_path: Path) -> None:
    status = get_menu_bar_runtime_status(
        pid_file=tmp_path / "server.pid",
        log_file=tmp_path / "server.log",
        default_host="127.0.0.1",
        default_port=2455,
    )

    snapshot = stopped_runtime_snapshot(status)

    assert snapshot.title == "Stopped"
    assert ("Status", "Stopped") in snapshot.rows
    assert ("Dashboard", "http://127.0.0.1:2455") in snapshot.rows


def test_dashboard_page_url_points_to_spa_dashboard_route() -> None:
    assert dashboard_page_url("http://127.0.0.1:2455") == "http://127.0.0.1:2455/dashboard"
    assert dashboard_page_url("http://127.0.0.1:2455/") == "http://127.0.0.1:2455/dashboard"


def test_dashboard_url_supports_https_and_loopback_fallback() -> None:
    assert dashboard_url("0.0.0.0", 2455, scheme="https") == "https://127.0.0.1:2455"


def test_dashboard_scheme_for_options_uses_https_for_tls_runtime(tmp_path: Path) -> None:
    options = MenuBarRuntimeOptions(
        host="127.0.0.1",
        port=2455,
        ssl_certfile="cert.pem",
        ssl_keyfile="key.pem",
        pid_file=tmp_path / "server.pid",
        log_file=tmp_path / "server.log",
        startup_timeout_seconds=3.0,
        start_on_launch=False,
    )

    assert dashboard_scheme_for_options(options) == "https"


def test_get_menu_bar_runtime_status_uses_dashboard_scheme(monkeypatch, tmp_path: Path) -> None:
    metadata = RuntimeMetadata(pid=1234, host="0.0.0.0", port=2455, log_file=str(tmp_path / "server.log"))
    monkeypatch.setattr("app.menubar_runtime.load_running_metadata", lambda pid_file: (metadata, False))

    status = get_menu_bar_runtime_status(
        pid_file=tmp_path / "server.pid",
        log_file=tmp_path / "fallback.log",
        default_host="127.0.0.1",
        default_port=2455,
        dashboard_scheme="https",
    )

    assert status.dashboard_url == "https://127.0.0.1:2455"


def test_sync_codex_provider_runs_provider_sync(monkeypatch, tmp_path: Path) -> None:
    calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
    provider_bin = tmp_path / "codex-provider"
    provider_bin.write_text("#!/usr/bin/env node\n", encoding="utf-8")

    def fake_run(*args, **kwargs):
        calls.append((args, kwargs))
        return type("Completed", (), {"returncode": 0, "stdout": "synced\n", "stderr": ""})()

    monkeypatch.setenv("CODEX_PROVIDER_BIN", str(provider_bin))
    monkeypatch.setattr("app.menubar_runtime.subprocess.run", fake_run)

    result = sync_codex_provider(timeout_seconds=3.0)

    assert result.succeeded is True
    assert result.message == "synced"
    assert len(calls) == 1
    args, kwargs = calls[0]
    assert args == ([str(provider_bin), "sync"],)
    assert kwargs["capture_output"] is True
    assert kwargs["check"] is False
    assert "env" in kwargs
    assert kwargs["text"] is True
    assert kwargs["timeout"] == 3.0


def test_sync_codex_provider_reports_missing_command(monkeypatch) -> None:
    monkeypatch.setattr("app.menubar_runtime.shutil.which", lambda *args, **kwargs: None)

    result = sync_codex_provider()

    assert result.succeeded is False
    assert result.message == "codex-provider command not found"


def test_sync_codex_provider_reports_missing_configured_command(monkeypatch, tmp_path: Path) -> None:
    missing = tmp_path / "codex-provider"
    monkeypatch.setenv("CODEX_PROVIDER_BIN", str(missing))

    result = sync_codex_provider()

    assert result.succeeded is False
    assert result.message == f"codex-provider command not found at {missing}"


def test_sync_codex_provider_reports_nonzero_stderr(monkeypatch, tmp_path: Path) -> None:
    provider_bin = tmp_path / "codex-provider"
    provider_bin.write_text("#!/usr/bin/env node\n", encoding="utf-8")

    def fake_run(*args, **kwargs):
        return type("Completed", (), {"returncode": 2, "stdout": "ignored\n", "stderr": "failed\n"})()

    monkeypatch.setenv("CODEX_PROVIDER_BIN", str(provider_bin))
    monkeypatch.setattr("app.menubar_runtime.subprocess.run", fake_run)

    result = sync_codex_provider()

    assert result.succeeded is False
    assert result.message == "failed"


def test_sync_codex_provider_reports_timeout(monkeypatch, tmp_path: Path) -> None:
    provider_bin = tmp_path / "codex-provider"
    provider_bin.write_text("#!/usr/bin/env node\n", encoding="utf-8")

    monkeypatch.setenv("CODEX_PROVIDER_BIN", str(provider_bin))
    monkeypatch.setattr(
        "app.menubar_runtime.subprocess.run",
        lambda *args, **kwargs: (_ for _ in ()).throw(__import__("subprocess").TimeoutExpired("cmd", 4.0)),
    )

    result = sync_codex_provider(timeout_seconds=4.0)

    assert result.succeeded is False
    assert result.message == "codex-provider sync timed out after 4s"


def test_sync_codex_provider_reports_os_error(monkeypatch, tmp_path: Path) -> None:
    provider_bin = tmp_path / "codex-provider"
    provider_bin.write_text("#!/usr/bin/env node\n", encoding="utf-8")

    monkeypatch.setenv("CODEX_PROVIDER_BIN", str(provider_bin))
    monkeypatch.setattr(
        "app.menubar_runtime.subprocess.run",
        lambda *args, **kwargs: (_ for _ in ()).throw(PermissionError("denied")),
    )

    result = sync_codex_provider()

    assert result.succeeded is False
    assert "denied" in result.message


def test_resolve_codex_provider_command_searches_augmented_path(monkeypatch) -> None:
    provider_bin = "/opt/homebrew/bin/codex-provider"
    seen_paths: list[str] = []

    def fake_which(command: str, *, path: str) -> str:
        seen_paths.append(path)
        assert command == "codex-provider"
        return provider_bin

    monkeypatch.delenv("CODEX_PROVIDER_BIN", raising=False)
    monkeypatch.setattr("app.menubar_runtime.shutil.which", fake_which)

    assert resolve_codex_provider_command() == Path(provider_bin)
    assert "/opt/homebrew/bin" in seen_paths[0]
