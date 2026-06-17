from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Sequence

from app.cli_runtime import (
    DEFAULT_SHUTDOWN_TIMEOUT_SECONDS,
    DEFAULT_STARTUP_TIMEOUT_SECONDS,
    ServeOptions,
    default_log_file,
    default_pid_file,
    load_running_metadata,
    shutdown_background_server,
    start_background_server,
)
from app.codex_sessions_retag import RetagResult, default_codex_home, retag_codex_sessions
from app.core.runtime_logging import build_log_config

if TYPE_CHECKING:
    from app.core.runtime_logging import LogConfig


class _CliHelpFormatter(argparse.HelpFormatter):
    def __init__(self, prog: str) -> None:
        super().__init__(prog, max_help_position=36, width=120)


def _add_serve_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--host", default=os.getenv("HOST", "127.0.0.1"))
    parser.add_argument("--port", default=os.getenv("PORT", "2455"))
    parser.add_argument("--ssl-certfile", default=os.getenv("SSL_CERTFILE"))
    parser.add_argument("--ssl-keyfile", default=os.getenv("SSL_KEYFILE"))
    parser.add_argument(
        "--timeout-keep-alive",
        default=os.getenv("UVICORN_TIMEOUT_KEEP_ALIVE", "7200"),
        help=(
            "Seconds to keep idle HTTP connections open. Codex CLI reuses local "
            "connections for large compact POSTs; short keepalive windows can leave the "
            "client writing to a stale socket before the request reaches the app."
        ),
    )


def _has_explicit_option(args: Sequence[str], option: str) -> bool:
    return any(arg == option or arg.startswith(f"{option}=") for arg in args)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the codex-lb-cinamon API server.",
        formatter_class=_CliHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    serve_parser = subparsers.add_parser(
        "serve",
        help="Run the API server in the foreground.",
        formatter_class=_CliHelpFormatter,
    )
    _add_serve_arguments(serve_parser)

    start_parser = subparsers.add_parser(
        "start",
        help="Start the API server in the background.",
        formatter_class=_CliHelpFormatter,
    )
    _add_serve_arguments(start_parser)
    start_parser.add_argument("--pid-file", type=Path, default=default_pid_file())
    start_parser.add_argument("--log-file", type=Path, default=default_log_file())
    start_parser.add_argument("--startup-timeout", type=float, default=DEFAULT_STARTUP_TIMEOUT_SECONDS)

    status_parser = subparsers.add_parser(
        "status",
        help="Show background server status.",
        formatter_class=_CliHelpFormatter,
    )
    status_parser.add_argument("--pid-file", type=Path, default=default_pid_file())

    shutdown_parser = subparsers.add_parser(
        "shutdown",
        help="Stop the tracked background server.",
        formatter_class=_CliHelpFormatter,
    )
    shutdown_parser.add_argument("--pid-file", type=Path, default=default_pid_file())
    shutdown_parser.add_argument("--timeout", type=float, default=DEFAULT_SHUTDOWN_TIMEOUT_SECONDS)

    codex_sessions = subparsers.add_parser(
        "codex-sessions",
        help="Manage local Codex session metadata.",
        formatter_class=_CliHelpFormatter,
    )
    codex_sessions_subparsers = codex_sessions.add_subparsers(dest="codex_sessions_command")
    retag = codex_sessions_subparsers.add_parser(
        "retag",
        help="Re-tag Codex threads between the openai and codex-lb model providers.",
        formatter_class=_CliHelpFormatter,
    )
    retag.add_argument(
        "--from",
        dest="source_provider",
        metavar="PROVIDER",
        required=True,
        help="Provider tag to replace.",
    )
    retag.add_argument("--to", dest="target_provider", metavar="PROVIDER", required=True, help="Provider tag to write.")
    retag.add_argument(
        "--codex-home",
        type=Path,
        metavar="PATH",
        default=None,
        help="Codex data directory. Defaults to CODEX_HOME, /codex-home in Docker, or ~/.codex.",
    )
    retag.add_argument("--dry-run", action="store_true", help="Show what would change without writing files.")
    retag.add_argument(
        "--yes",
        action="store_true",
        help="Confirm that Codex/Codex CLI is closed and allow a non-interactive write.",
    )

    return parser


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    raw_args = list(argv) if argv is not None else sys.argv[1:]
    if raw_args and raw_args[0] in {"-h", "--help"}:
        return _build_parser().parse_args(raw_args)
    if not raw_args or raw_args[0].startswith("-"):
        raw_args = ["serve", *raw_args]
    args = _build_parser().parse_args(raw_args)
    if args.command in {"serve", "start"}:
        if _has_explicit_option(raw_args, "--port"):
            args.port = _parse_server_port(args.port)
        if _has_explicit_option(raw_args, "--timeout-keep-alive"):
            args.timeout_keep_alive = _parse_server_timeout_keep_alive(args.timeout_keep_alive)
    return args


def _serve_options_from_args(args: argparse.Namespace) -> ServeOptions:
    return ServeOptions(
        host=args.host,
        port=_parse_server_port(args.port),
        ssl_certfile=args.ssl_certfile,
        ssl_keyfile=args.ssl_keyfile,
        timeout_keep_alive=_parse_server_timeout_keep_alive(args.timeout_keep_alive),
    )


def _validate_ssl_flags(options: ServeOptions) -> None:
    if bool(options.ssl_certfile) ^ bool(options.ssl_keyfile):
        raise SystemExit("Both --ssl-certfile and --ssl-keyfile must be provided together.")


def _run_foreground(options: ServeOptions) -> None:
    _validate_ssl_flags(options)
    os.environ["PORT"] = str(options.port)
    _load_uvicorn().run(
        "app.main:app",
        host=options.host,
        port=options.port,
        ssl_certfile=options.ssl_certfile,
        ssl_keyfile=options.ssl_keyfile,
        timeout_keep_alive=options.timeout_keep_alive,
        log_config=build_log_config(),
    )


def _run_background_start(args: argparse.Namespace) -> None:
    options = _serve_options_from_args(args)
    _validate_ssl_flags(options)
    try:
        metadata = start_background_server(
            options,
            pid_file=args.pid_file,
            log_file=args.log_file,
            startup_timeout_seconds=args.startup_timeout,
        )
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc

    print(f"Started codex-lb-cinamon in background (pid {metadata.pid}, {metadata.host}:{metadata.port})")
    print(f"PID file: {args.pid_file.expanduser()}")
    print(f"Log file: {Path(metadata.log_file).expanduser()}")


def _run_status(args: argparse.Namespace) -> None:
    metadata, stale = load_running_metadata(args.pid_file)
    if metadata is None:
        if stale:
            print(f"No running background server found. Removed stale PID file {args.pid_file.expanduser()}.")
        else:
            print("codex-lb-cinamon background server is not running.")
        raise SystemExit(1)

    print(f"codex-lb-cinamon background server is running (pid {metadata.pid}, {metadata.host}:{metadata.port})")
    print(f"PID file: {args.pid_file.expanduser()}")
    print(f"Log file: {Path(metadata.log_file).expanduser()}")


def _run_shutdown(args: argparse.Namespace) -> None:
    metadata, stale = load_running_metadata(args.pid_file)
    if metadata is None:
        if stale:
            print(f"No running background server found. Removed stale PID file {args.pid_file.expanduser()}.")
        else:
            print("codex-lb-cinamon background server is not running.")
        raise SystemExit(1)

    try:
        stopped = shutdown_background_server(args.pid_file, timeout_seconds=args.timeout)
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc
    if stopped is None:
        print("codex-lb-cinamon background server is not running.")
        raise SystemExit(1)

    print(f"Stopped codex-lb-cinamon background server (pid {stopped.pid}).")


def _run_codex_sessions_retag(args: argparse.Namespace) -> None:
    codex_home = args.codex_home or default_codex_home()
    if not args.dry_run:
        _confirm_retag_write(args.yes)

    try:
        result = retag_codex_sessions(
            codex_home=codex_home,
            source_provider=args.source_provider,
            target_provider=args.target_provider,
            dry_run=args.dry_run,
            progress_logger=lambda message: print(message, flush=True),
        )
    except sqlite3.OperationalError as exc:
        message = str(exc)
        if "locked" in message.casefold():
            message = (
                f"{message}\n"
                "Close Codex/Codex CLI and retry. The state_*.sqlite database can be locked while Codex is running."
            )
        raise SystemExit(message) from exc
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    except OSError as exc:
        raise SystemExit(f"Unable to read or write Codex session files: {exc}") from exc

    _print_retag_summary(result)


def _confirm_retag_write(yes: bool) -> None:
    warning = (
        "This command rewrites Codex session metadata, including state_*.sqlite when present.\n"
        "Close Codex/Codex CLI before continuing to avoid SQLite locks or stale writes."
    )
    print(warning, file=sys.stderr)
    if yes:
        return
    if not sys.stdin.isatty():
        raise SystemExit("Refusing to write without --yes in a non-interactive shell.")
    answer = input("Continue? [y/N] ").strip().casefold()
    if answer not in {"y", "yes"}:
        raise SystemExit("Aborted.")


def _print_retag_summary(result: RetagResult) -> None:
    action = "Would update" if result.dry_run else "Updated"
    methods = ", ".join(result.methods_used) if result.methods_used else "none"
    print("")
    print("Codex session retag summary")
    print(f"- Codex home: {result.codex_home}")
    print(f"- Methods used: {methods}")
    print(f"- JSONL files scanned: {result.jsonl_files_scanned}")
    print(f"- JSONL files matched: {result.jsonl_files_matched}")
    print(f"- SQLite DBs scanned: {result.sqlite_dbs_scanned}")
    print(f"- SQLite DBs matched: {result.sqlite_dbs_matched}")
    print(f"- {action} JSONL files: {result.jsonl_files_matched if result.dry_run else result.jsonl_files_updated}")
    print(f"- {action} SQLite rows: {result.sqlite_rows_matched if result.dry_run else result.sqlite_rows_updated}")
    if result.backup_path is not None:
        print(f"- Backup: {result.backup_path}")


def _build_log_config() -> "LogConfig":
    return build_log_config()


def _load_uvicorn():
    import uvicorn

    return uvicorn


def _parse_server_port(raw_port: str | int) -> int:
    try:
        return int(raw_port)
    except ValueError as exc:
        raise SystemExit(f"--port/PORT must be an integer, got {raw_port!r}.") from exc


def _parse_server_timeout_keep_alive(raw_timeout: str | int) -> int:
    try:
        return int(raw_timeout)
    except ValueError as exc:
        raise SystemExit(
            f"--timeout-keep-alive/UVICORN_TIMEOUT_KEEP_ALIVE must be an integer, got {raw_timeout!r}."
        ) from exc


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    command = args.command

    if command == "serve":
        _run_foreground(_serve_options_from_args(args))
        return
    if command == "start":
        _run_background_start(args)
        return
    if command == "status":
        _run_status(args)
        return
    if command == "shutdown":
        _run_shutdown(args)
        return
    if command == "codex-sessions":
        if args.codex_sessions_command == "retag":
            _run_codex_sessions_retag(args)
            return
        raise SystemExit("codex-sessions requires a subcommand")

    raise SystemExit(f"Unsupported command: {command}")


if __name__ == "__main__":
    main()
