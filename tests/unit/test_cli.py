from __future__ import annotations

import logging
import sys
from typing import Any

import pytest

from app import cli
from app.cli_runtime import RuntimeMetadata
from app.core.runtime_logging import UtcDefaultFormatter

pytestmark = pytest.mark.unit


def test_main_passes_timestamped_log_config(monkeypatch):
    captured: dict[str, Any] = {}

    def fake_run(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs

    monkeypatch.setattr(sys, "argv", ["codex-lb-cinamon"])
    monkeypatch.setattr(cli.uvicorn, "run", fake_run)

    cli.main()

    kwargs = captured["kwargs"]
    assert isinstance(kwargs, dict)
    log_config = kwargs["log_config"]
    assert isinstance(log_config, dict)
    formatters = log_config["formatters"]
    assert formatters["default"]["fmt"].startswith("%(asctime)s ")
    assert formatters["access"]["fmt"].startswith("%(asctime)s ")


def test_parse_args_defaults_to_serve_for_legacy_flags(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["codex-lb-cinamon", "--port", "2555"])

    args = cli._parse_args()

    assert args.command == "serve"
    assert args.port == 2555


def test_parse_args_accepts_root_server_flags(monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "codex-lb-cinamon",
            "--host",
            "0.0.0.0",
            "--port",
            "2555",
            "--ssl-certfile",
            "cert.pem",
            "--ssl-keyfile",
            "key.pem",
        ],
    )

    args = cli._parse_args()

    assert args.command == "serve"
    assert args.host == "0.0.0.0"
    assert args.port == 2555
    assert args.ssl_certfile == "cert.pem"
    assert args.ssl_keyfile == "key.pem"


def test_main_rejects_unpaired_tls_flags(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["codex-lb-cinamon", "--ssl-certfile", "cert.pem"])

    with pytest.raises(SystemExit, match="Both --ssl-certfile and --ssl-keyfile must be provided together"):
        cli.main()


def test_parse_args_accepts_menubar_options(monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "codex-lb-cinamon",
            "menubar",
            "--base-url",
            "http://localhost:5173",
            "--refresh-interval",
            "10",
            "--session-cookie",
            "session-id",
        ],
    )

    args = cli._parse_args()

    assert args.command == "menubar"
    assert args.base_url == "http://localhost:5173"
    assert args.refresh_interval == 10
    assert args.session_cookie == "session-id"


def test_parse_args_ignores_invalid_menubar_refresh_env_for_status(monkeypatch):
    monkeypatch.setenv("CODEX_LB_MENUBAR_REFRESH_INTERVAL", "bad")
    monkeypatch.setattr(sys, "argv", ["codex-lb-cinamon", "status"])

    args = cli._parse_args()

    assert args.command == "status"


def test_parse_args_rejects_invalid_menubar_refresh_env_for_menubar(monkeypatch):
    monkeypatch.setenv("CODEX_LB_MENUBAR_REFRESH_INTERVAL", "bad")
    monkeypatch.setattr(sys, "argv", ["codex-lb-cinamon", "menubar"])

    with pytest.raises(SystemExit):
        cli._parse_args()


def test_parse_args_accepts_managed_menubar_runtime_options(monkeypatch, tmp_path):
    pid_file = tmp_path / "server.pid"
    log_file = tmp_path / "server.log"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "codex-lb-cinamon",
            "menubar",
            "--manage-server",
            "--start-on-launch",
            "--host",
            "0.0.0.0",
            "--port",
            "2555",
            "--pid-file",
            str(pid_file),
            "--log-file",
            str(log_file),
            "--startup-timeout",
            "4.5",
        ],
    )

    args = cli._parse_args()

    assert args.command == "menubar"
    assert args.manage_server is True
    assert args.start_on_launch is True
    assert args.host == "0.0.0.0"
    assert args.port == 2555
    assert args.pid_file == pid_file
    assert args.log_file == log_file
    assert args.startup_timeout == 4.5


def test_managed_menubar_uses_https_base_url_for_tls_runtime(monkeypatch, tmp_path):
    captured: dict[str, Any] = {}
    pid_file = tmp_path / "server.pid"
    log_file = tmp_path / "server.log"

    def fake_run_menu_bar_app(config, *, runtime_options):
        captured["config"] = config
        captured["runtime_options"] = runtime_options

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "codex-lb-cinamon",
            "menubar",
            "--manage-server",
            "--host",
            "0.0.0.0",
            "--port",
            "2555",
            "--ssl-certfile",
            "cert.pem",
            "--ssl-keyfile",
            "key.pem",
            "--pid-file",
            str(pid_file),
            "--log-file",
            str(log_file),
        ],
    )
    monkeypatch.setattr("app.menubar_app.run_menu_bar_app", fake_run_menu_bar_app)

    cli.main()

    assert captured["config"].base_url == "https://127.0.0.1:2555"
    assert captured["config"].verify_tls is False


def test_start_command_reports_background_runtime(monkeypatch, capsys, tmp_path):
    runtime = RuntimeMetadata(pid=4242, host="127.0.0.1", port=2455, log_file=str(tmp_path / "server.log"))
    pid_file = tmp_path / "server.pid"
    log_file = tmp_path / "server.log"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "codex-lb-cinamon",
            "start",
            "--pid-file",
            str(pid_file),
            "--log-file",
            str(log_file),
        ],
    )
    monkeypatch.setattr(cli, "start_background_server", lambda *args, **kwargs: runtime)

    cli.main()

    output = capsys.readouterr().out
    assert "Started codex-lb-cinamon in background" in output
    assert str(pid_file) in output
    assert str(log_file) in output


def test_status_command_reports_running_server(monkeypatch, capsys, tmp_path):
    runtime = RuntimeMetadata(pid=4242, host="127.0.0.1", port=2455, log_file=str(tmp_path / "server.log"))
    pid_file = tmp_path / "server.pid"

    monkeypatch.setattr(sys, "argv", ["codex-lb-cinamon", "status", "--pid-file", str(pid_file)])
    monkeypatch.setattr(cli, "load_running_metadata", lambda path: (runtime, False))

    cli.main()

    output = capsys.readouterr().out
    assert "background server is running" in output
    assert str(pid_file) in output


def test_shutdown_command_stops_running_server(monkeypatch, capsys, tmp_path):
    runtime = RuntimeMetadata(pid=4242, host="127.0.0.1", port=2455, log_file=str(tmp_path / "server.log"))
    pid_file = tmp_path / "server.pid"

    monkeypatch.setattr(sys, "argv", ["codex-lb-cinamon", "shutdown", "--pid-file", str(pid_file)])
    monkeypatch.setattr(cli, "load_running_metadata", lambda path: (runtime, False))
    monkeypatch.setattr(cli, "shutdown_background_server", lambda path, timeout_seconds: runtime)

    cli.main()

    output = capsys.readouterr().out
    assert "Stopped codex-lb-cinamon background server" in output


def test_utc_default_formatter_formats_without_converter_binding_error():
    formatter = UtcDefaultFormatter(
        fmt="%(asctime)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
        use_colors=None,
    )
    record = logging.LogRecord(
        name="uvicorn.error",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )
    record.created = 0.0

    assert formatter.format(record) == "1970-01-01T00:00:00Z hello"
