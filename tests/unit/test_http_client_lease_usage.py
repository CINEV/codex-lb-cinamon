from __future__ import annotations

import ast
from pathlib import Path


def _direct_get_http_client_session_lines(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    lines: list[int] = []
    get_http_client_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and _is_get_http_client_call(node.value):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    get_http_client_names.add(target.id)
            continue
        if not isinstance(node, ast.Attribute) or node.attr != "session":
            continue
        call = node.value
        if _is_get_http_client_call(call):
            lines.append(node.lineno)
            continue
        if isinstance(call, ast.Name) and call.id in get_http_client_names:
            lines.append(node.lineno)
    return lines


def _is_get_http_client_call(node: ast.AST) -> bool:
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "get_http_client"


def test_shared_http_session_callers_use_lease_helpers() -> None:
    paths = [
        Path("app/core/clients/openai_platform.py"),
        Path("app/core/clients/proxy.py"),
        Path("app/modules/proxy/platform_cache_alerts.py"),
    ]

    offenders = {str(path): lines for path in paths if (lines := _direct_get_http_client_session_lines(path))}

    assert offenders == {}
