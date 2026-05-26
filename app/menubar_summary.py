from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, cast
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen

from app import __version__

DASHBOARD_SESSION_COOKIE = "codex_lb_dashboard_session"


@dataclass(frozen=True)
class MenuBarConfig:
    base_url: str = "http://127.0.0.1:2455"
    refresh_interval_seconds: int = 30
    session_cookie: str | None = None
    timeout_seconds: float = 5.0


@dataclass(frozen=True)
class AccountStatusCounts:
    total: int
    active: int
    paused: int
    limited: int
    deactivated: int


@dataclass(frozen=True)
class AccountMenuCard:
    account_id: str
    title: str
    subtitle: str
    status_label: str
    primary_percent: int | None
    secondary_percent: int | None
    primary_reset: str
    secondary_reset: str
    details_path: str
    shows_quota: bool = True
    is_current: bool = False


@dataclass(frozen=True)
class MenuBarDonutSegment:
    account_id: str
    label: str
    value: float


@dataclass(frozen=True)
class MenuBarDonutSummary:
    title: str
    center_label: str
    center_value: str
    total_label: str
    used_label: str
    used_value: float
    total_value: float
    segments: tuple[MenuBarDonutSegment, ...]


@dataclass(frozen=True)
class MenuBarSnapshot:
    title: str
    rows: tuple[tuple[str, str], ...]
    account_cards: tuple[AccountMenuCard, ...] = ()
    primary_donut: MenuBarDonutSummary | None = None
    error_message: str | None = None


def build_cookie_header(session_cookie: str | None) -> str | None:
    if session_cookie is None:
        return None
    value = session_cookie.strip()
    if not value:
        return None
    if "=" in value:
        return value
    return f"{DASHBOARD_SESSION_COOKIE}={value}"


def fetch_menu_bar_snapshot(config: MenuBarConfig) -> MenuBarSnapshot:
    cookie_header = build_cookie_header(config.session_cookie)
    try:
        overview = _request_json(
            config.base_url,
            "/api/dashboard/overview?timeframe=7d",
            cookie_header=cookie_header,
            timeout_seconds=config.timeout_seconds,
        )
        settings = _request_json(
            config.base_url,
            "/api/settings",
            cookie_header=cookie_header,
            timeout_seconds=config.timeout_seconds,
        )
        accounts_payload = _request_json(
            config.base_url,
            "/api/accounts",
            cookie_header=cookie_header,
            timeout_seconds=config.timeout_seconds,
        )
        request_logs_payload = _request_json(
            config.base_url,
            "/api/request-logs?limit=1&status=ok",
            cookie_header=cookie_header,
            timeout_seconds=config.timeout_seconds,
        )
    except HTTPError as exc:
        return build_unavailable_snapshot(_http_error_message(exc))
    except URLError as exc:
        return build_unavailable_snapshot(f"Connection failed: {exc.reason}")
    except OSError as exc:
        return build_unavailable_snapshot(f"Connection failed: {exc}")
    except ValueError as exc:
        return build_unavailable_snapshot(str(exc))

    return build_menu_bar_snapshot(
        overview,
        settings,
        accounts_payload=accounts_payload,
        request_logs_payload=request_logs_payload,
    )


def build_unavailable_snapshot(error_message: str) -> MenuBarSnapshot:
    return MenuBarSnapshot(
        title="5h --",
        rows=(
            ("Status", "Unavailable"),
            ("Error", error_message),
        ),
        error_message=error_message,
    )


def build_menu_bar_snapshot(
    overview: dict[str, Any],
    settings: dict[str, Any],
    *,
    accounts_payload: dict[str, Any] | None = None,
    request_logs_payload: dict[str, Any] | None = None,
    version: str = __version__,
) -> MenuBarSnapshot:
    primary_remaining = remaining_percent(_nested(overview, "summary", "primaryWindow", "remainingPercent"))
    secondary_remaining = remaining_percent(_nested(overview, "summary", "secondaryWindow", "remainingPercent"))
    metrics = _as_dict(_nested(overview, "summary", "metrics"))
    accounts = _as_list(_as_dict(accounts_payload).get("accounts")) or _as_list(overview.get("accounts"))
    current_subject_id = current_account_subject_id(request_logs_payload)
    current_label = current_account_label(accounts, current_subject_id)
    counts = count_account_statuses(accounts)
    account_cards = build_account_cards(accounts, current_subject_id=current_subject_id)
    primary_donut = build_primary_donut_summary(overview, accounts)
    title = f"5h {format_percent(primary_remaining)}"
    rows = (
        ("5h remaining", format_percent(primary_remaining)),
        ("7d remaining", format_percent(secondary_remaining)),
        ("Last sync", format_timestamp(overview.get("lastSyncAt"))),
        (
            "Routing",
            routing_label(
                settings.get("routingStrategy"),
                settings.get("stickyThreadsEnabled"),
                settings.get("preferEarlierResetAccounts"),
            ),
        ),
        ("Version", version),
        ("Active accounts", f"{counts.active}/{counts.total}"),
        ("Current", current_label),
        (
            "Accounts",
            (
                f"{counts.total} total / {counts.active} active / {counts.paused} paused / "
                f"{counts.limited} limited / {counts.deactivated} deactivated"
            ),
        ),
        ("Requests", format_compact_number(metrics.get("requests"))),
        ("Tokens", format_compact_number(metrics.get("tokens"))),
        ("Cost", format_currency(_nested(overview, "summary", "cost", "totalUsd"))),
        ("Error rate", format_rate(metrics.get("errorRate"))),
    )
    return MenuBarSnapshot(title=title, rows=rows, account_cards=account_cards, primary_donut=primary_donut)


def build_primary_donut_summary(overview: dict[str, Any], accounts: list[object]) -> MenuBarDonutSummary | None:
    primary_window = _as_dict(_nested(overview, "windows", "primary"))
    primary_summary = _as_dict(_nested(overview, "summary", "primaryWindow"))
    total = finite_float(primary_summary.get("capacityCredits"))
    if total is None or total <= 0:
        return None

    remaining_by_account = build_remaining_credit_index(primary_window)
    if not remaining_by_account:
        return None

    secondary_by_account = build_remaining_credit_index(_as_dict(_nested(overview, "windows", "secondary")))
    segments: list[MenuBarDonutSegment] = []
    for item in accounts:
        account = _as_dict(item)
        account_id = _display_text(account.get("accountId"))
        if account_id is None:
            continue
        if _display_text(account.get("providerKind")) == "openai_platform":
            continue
        if account.get("windowMinutesPrimary") is None and account.get("windowMinutesSecondary") is not None:
            continue
        remaining = remaining_by_account.get(account_id)
        if remaining is None:
            continue
        usage = _as_dict(account.get("usage"))
        secondary_remaining_percent = finite_float(usage.get("secondaryRemainingPercent"))
        secondary_remaining = secondary_by_account.get(account_id)
        if secondary_remaining is not None and secondary_remaining_percent is not None:
            remaining = min(remaining, secondary_remaining)
        if remaining <= 0:
            continue
        segments.append(
            MenuBarDonutSegment(
                account_id=account_id,
                label=account_label(account),
                value=remaining,
            )
        )

    segments.sort(key=lambda segment: segment.value, reverse=True)
    remaining_total = sum(segment.value for segment in segments)
    visible_segments = compact_donut_segments(segments)
    used_value = max(0.0, total - remaining_total)
    used_percent = (used_value / total) * 100
    return MenuBarDonutSummary(
        title="5h Remaining",
        center_label="REMAINING",
        center_value=format_donut_value(remaining_total),
        total_label=f"Total {format_donut_value(total)} · {format_used_percent(used_percent)} used",
        used_label="Used",
        used_value=used_value,
        total_value=total,
        segments=visible_segments,
    )


def compact_donut_segments(segments: list[MenuBarDonutSegment], *, limit: int = 5) -> tuple[MenuBarDonutSegment, ...]:
    if len(segments) <= limit:
        return tuple(segments)
    visible_count = max(1, limit - 1)
    visible = segments[:visible_count]
    other_value = sum(segment.value for segment in segments[visible_count:])
    return (
        *visible,
        MenuBarDonutSegment(account_id="__other__", label="Other", value=other_value),
    )


def build_account_cards(
    accounts: list[object],
    *,
    current_subject_id: str | None = None,
    limit: int = 6,
) -> tuple[AccountMenuCard, ...]:
    cards: list[AccountMenuCard] = []
    for item in accounts:
        account = _as_dict(item)
        if not account:
            continue
        usage = _as_dict(account.get("usage"))
        account_id = str(account.get("accountId") or "")
        provider_kind = _display_text(account.get("providerKind"))
        is_platform = provider_kind == "openai_platform"
        title = (
            _display_text(account.get("displayName")) or _display_text(account.get("email")) or account_id or "Account"
        )
        plan_type = _display_text(account.get("planType"))
        status = _display_text(account.get("status")) or "unknown"
        subtitle = format_platform_subtitle(account) if is_platform else format_plan_label(plan_type)
        cards.append(
            AccountMenuCard(
                account_id=account_id,
                title=title,
                subtitle=subtitle,
                status_label=format_status_label(status),
                primary_percent=None if is_platform else remaining_percent(usage.get("primaryRemainingPercent")),
                secondary_percent=None if is_platform else remaining_percent(usage.get("secondaryRemainingPercent")),
                primary_reset="--" if is_platform else format_reset_label(account.get("resetAtPrimary")),
                secondary_reset="--" if is_platform else format_reset_label(account.get("resetAtSecondary")),
                details_path=f"/accounts?{urlencode({'selected': account_id})}" if account_id else "/accounts",
                shows_quota=not is_platform,
                is_current=account_matches_subject(account, current_subject_id),
            )
        )
        if len(cards) >= limit:
            break
    return tuple(cards)


def build_remaining_credit_index(window: dict[str, Any]) -> dict[str, float]:
    index: dict[str, float] = {}
    for item in _as_list(window.get("accounts")):
        entry = _as_dict(item)
        account_id = _display_text(entry.get("accountId"))
        remaining = finite_float(entry.get("remainingCredits"))
        if account_id is not None and remaining is not None:
            index[account_id] = max(0.0, remaining)
    return index


def account_label(account: dict[str, Any]) -> str:
    return (
        _display_text(account.get("displayName"))
        or _display_text(account.get("email"))
        or _display_text(account.get("accountId"))
        or "Account"
    )


def current_account_subject_id(request_logs_payload: dict[str, Any] | None) -> str | None:
    requests = _as_list(_as_dict(request_logs_payload).get("requests"))
    if not requests:
        return None
    request = _as_dict(requests[0])
    return _display_text(request.get("accountId")) or _display_text(request.get("routingSubjectId"))


def current_account_label(accounts: list[object], subject_id: str | None) -> str:
    if not subject_id:
        return "--"
    for item in accounts:
        account = _as_dict(item)
        if account_matches_subject(account, subject_id):
            return (
                _display_text(account.get("displayName"))
                or _display_text(account.get("email"))
                or _display_text(account.get("accountId"))
                or subject_id
            )
    return subject_id


def account_matches_subject(account: dict[str, Any], subject_id: str | None) -> bool:
    if not subject_id:
        return False
    return subject_id in {
        _display_text(account.get("accountId")),
        _display_text(account.get("routingSubjectId")),
    }


def remaining_percent(value: object) -> int | None:
    if not isinstance(value, int | float):
        return None
    if not _is_finite(value):
        return None
    return round(max(0.0, min(100.0, float(value))))


def format_percent(value: int | None) -> str:
    return "--" if value is None else f"{value}%"


def format_timestamp(value: object) -> str:
    if not isinstance(value, str) or not value:
        return "--"
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return value
    return parsed.astimezone().strftime("%H:%M:%S")


def format_reset_label(value: object, *, now: datetime | None = None) -> str:
    if not isinstance(value, str) or not value:
        return "--"
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return "--"
    parsed_local = parsed.astimezone()
    baseline = now.astimezone() if now else datetime.now(parsed_local.tzinfo)
    delta_seconds = int((parsed_local - baseline).total_seconds())
    if delta_seconds <= 0:
        return "now"
    days, remainder = divmod(delta_seconds, 86_400)
    hours, remainder = divmod(remainder, 3_600)
    minutes = remainder // 60
    if days > 0:
        return f"in {days}d {hours}h" if hours else f"in {days}d"
    if hours > 0:
        return f"in {hours}h {minutes}m" if minutes else f"in {hours}h"
    return f"in {minutes}m"


def format_plan_label(value: str | None) -> str:
    if not value:
        return "Account"
    return value.replace("_", " ").title()


def format_platform_subtitle(account: dict[str, Any]) -> str:
    base = "OpenAI Platform API key"
    routing_subject_id = _display_text(account.get("routingSubjectId"))
    return f"{base} | Subject {routing_subject_id}" if routing_subject_id else base


def format_status_label(value: str) -> str:
    if value == "quota_exceeded":
        return "Limited"
    return value.replace("_", " ").title()


def routing_label(strategy: object, sticky: object, prefer_earlier: object) -> str:
    sticky_enabled = bool(sticky)
    prefer_early = bool(prefer_earlier)
    if strategy == "round_robin":
        return "Round robin + Sticky threads" if sticky_enabled else "Round robin"
    if strategy == "capacity_weighted":
        if sticky_enabled and prefer_early:
            return "Capacity weighted + Sticky + Early reset"
        if sticky_enabled:
            return "Capacity weighted + Sticky threads"
        if prefer_early:
            return "Capacity weighted + Early reset"
        return "Capacity weighted"
    if sticky_enabled and prefer_early:
        return "Sticky + Early reset"
    if sticky_enabled:
        return "Sticky threads"
    if prefer_early:
        return "Early reset preferred"
    return "Usage weighted"


def count_account_statuses(accounts: list[object]) -> AccountStatusCounts:
    total = 0
    active = 0
    paused = 0
    limited = 0
    deactivated = 0
    for item in accounts:
        account = _as_dict(item)
        if not account:
            continue
        total += 1
        status = account.get("status")
        if status == "active":
            active += 1
        elif status == "paused":
            paused += 1
        elif status == "deactivated":
            deactivated += 1
        elif status in {"limited", "exceeded", "quota_exceeded"}:
            limited += 1
    return AccountStatusCounts(
        total=total,
        active=active,
        paused=paused,
        limited=limited,
        deactivated=deactivated,
    )


def format_compact_number(value: object) -> str:
    if not isinstance(value, int | float) or not _is_finite(value):
        return "--"
    numeric = float(value)
    abs_value = abs(numeric)
    if abs_value >= 1_000_000:
        return f"{numeric / 1_000_000:.1f}M".replace(".0M", "M")
    if abs_value >= 1_000:
        return f"{numeric / 1_000:.1f}K".replace(".0K", "K")
    return str(round(numeric))


def format_donut_value(value: object) -> str:
    numeric = finite_float(value)
    if numeric is None:
        return "--"
    abs_value = abs(numeric)
    if abs_value >= 1_000_000:
        return f"{numeric / 1_000_000:.2f}".rstrip("0").rstrip(".") + "M"
    if abs_value >= 1_000:
        return f"{numeric / 1_000:.2f}".rstrip("0").rstrip(".") + "K"
    if numeric.is_integer():
        return str(int(numeric))
    return f"{numeric:.2f}".rstrip("0").rstrip(".")


def format_used_percent(value: float) -> str:
    if value <= 0:
        return "0%"
    return f"{value:.1f}%" if value < 10 else f"{value:.0f}%"


def finite_float(value: object) -> float | None:
    if not isinstance(value, int | float) or not _is_finite(value):
        return None
    return float(value)


def format_currency(value: object) -> str:
    if not isinstance(value, int | float) or not _is_finite(value):
        return "--"
    return f"${float(value):,.2f}"


def format_rate(value: object) -> str:
    if not isinstance(value, int | float) or not _is_finite(value):
        return "--"
    return f"{float(value) * 100:.1f}%"


def _display_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _request_json(
    base_url: str,
    path: str,
    *,
    cookie_header: str | None,
    timeout_seconds: float,
) -> dict[str, Any]:
    url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    headers = {"Accept": "application/json"}
    if cookie_header:
        headers["Cookie"] = cookie_header
    request = Request(url, headers=headers)
    with urlopen(request, timeout=timeout_seconds) as response:
        payload = json.load(response)
    if not isinstance(payload, dict):
        raise ValueError("Dashboard returned a non-object JSON payload")
    return payload


def _http_error_message(exc: HTTPError) -> str:
    if exc.code in {401, 403}:
        return "Authentication required; pass --session-cookie"
    return f"Dashboard request failed: HTTP {exc.code}"


def _nested(payload: dict[str, Any], *keys: str) -> object:
    current: object = payload
    for key in keys:
        current = _as_dict(current).get(key)
    return current


def _as_dict(value: object) -> dict[str, Any]:
    return cast(dict[str, Any], value) if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return cast(list[object], value) if isinstance(value, list) else []


def _is_finite(value: int | float) -> bool:
    return float("-inf") < float(value) < float("inf")
