from __future__ import annotations

from pathlib import Path

from app.menubar_app import snapshot_config_for_runtime
from app.menubar_runtime import MenuBarRuntimeStatus
from app.menubar_summary import MenuBarConfig


def test_snapshot_config_for_runtime_uses_tracked_dashboard_url(tmp_path: Path) -> None:
    config = MenuBarConfig(base_url="http://127.0.0.1:2455", verify_tls=False)
    status = MenuBarRuntimeStatus(
        running=True,
        pid=1234,
        host="127.0.0.1",
        port=2555,
        dashboard_url="https://127.0.0.1:2555",
        log_file=tmp_path / "server.log",
        stale_metadata_removed=False,
    )

    runtime_config = snapshot_config_for_runtime(config, status)

    assert runtime_config.base_url == "https://127.0.0.1:2555"
    assert runtime_config.verify_tls is False


def test_snapshot_config_for_runtime_keeps_config_without_status() -> None:
    config = MenuBarConfig(base_url="http://127.0.0.1:2455")

    assert snapshot_config_for_runtime(config, None) is config
