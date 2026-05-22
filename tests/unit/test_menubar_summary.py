from __future__ import annotations

from datetime import datetime, timezone

from app.menubar_summary import (
    build_account_cards,
    build_cookie_header,
    build_menu_bar_snapshot,
    build_primary_donut_summary,
    build_unavailable_snapshot,
    count_account_statuses,
    format_compact_number,
    format_donut_value,
    format_reset_label,
    remaining_percent,
)


def test_build_menu_bar_snapshot_formats_5h_remaining_without_suffix() -> None:
    snapshot = build_menu_bar_snapshot(
        {
            "lastSyncAt": "2026-01-01T12:34:56Z",
            "accounts": [
                {"status": "active"},
                {"status": "paused"},
                {"status": "exceeded"},
            ],
            "summary": {
                "primaryWindow": {"remainingPercent": 72},
                "secondaryWindow": {"remainingPercent": 55.2},
                "cost": {"totalUsd": 1.82},
                "metrics": {
                    "requests": 228,
                    "tokens": 45_000,
                    "errorRate": 0.028,
                },
            },
        },
        {
            "routingStrategy": "usage_weighted",
            "stickyThreadsEnabled": True,
            "preferEarlierResetAccounts": False,
        },
        version="1.2.3",
    )

    assert snapshot.title == "5h 72%"
    assert "left" not in snapshot.title
    assert "used" not in snapshot.title
    assert ("5h remaining", "72%") in snapshot.rows
    assert ("7d remaining", "55%") in snapshot.rows
    assert ("Routing", "Sticky threads") in snapshot.rows
    assert ("Version", "1.2.3") in snapshot.rows
    assert ("Accounts", "3 total / 1 active / 1 paused / 1 limited / 0 deactivated") in snapshot.rows
    assert ("Tokens", "45K") in snapshot.rows
    assert ("Cost", "$1.82") in snapshot.rows
    assert ("Error rate", "2.8%") in snapshot.rows


def test_build_menu_bar_snapshot_uses_accounts_payload_when_provided() -> None:
    snapshot = build_menu_bar_snapshot(
        {
            "accounts": [],
            "summary": {
                "primaryWindow": {"remainingPercent": 72},
                "secondaryWindow": {"remainingPercent": 55},
                "metrics": {},
            },
        },
        {},
        accounts_payload={
            "accounts": [
                {
                    "accountId": "platform",
                    "displayName": "시나몬",
                    "providerKind": "openai_platform",
                    "routingSubjectId": "subject-platform-1",
                    "status": "active",
                },
            ],
        },
    )

    assert len(snapshot.account_cards) == 1
    assert snapshot.account_cards[0].title == "시나몬"
    assert snapshot.account_cards[0].subtitle == "OpenAI Platform API key | Subject subject-platform-1"


def test_build_menu_bar_snapshot_marks_current_account_from_recent_request_log() -> None:
    snapshot = build_menu_bar_snapshot(
        {
            "accounts": [],
            "summary": {
                "primaryWindow": {"remainingPercent": 72},
                "secondaryWindow": {"remainingPercent": 55},
                "metrics": {},
            },
        },
        {},
        accounts_payload={
            "accounts": [
                {
                    "accountId": "acc_team",
                    "displayName": "jacob@vonvon.me",
                    "planType": "team",
                    "status": "active",
                    "usage": {},
                },
                {
                    "accountId": "platform",
                    "displayName": "시나몬",
                    "providerKind": "openai_platform",
                    "routingSubjectId": "subject-platform-1",
                    "status": "active",
                },
            ],
        },
        request_logs_payload={
            "requests": [
                {
                    "accountId": None,
                    "routingSubjectId": "subject-platform-1",
                    "status": "ok",
                }
            ]
        },
    )

    assert ("Current", "시나몬") in snapshot.rows
    assert snapshot.account_cards[0].is_current is False
    assert snapshot.account_cards[1].is_current is True


def test_build_primary_donut_summary_matches_dashboard_remaining_breakdown() -> None:
    summary = build_primary_donut_summary(
        {
            "summary": {
                "primaryWindow": {
                    "capacityCredits": 2480,
                },
            },
            "windows": {
                "primary": {
                    "accounts": [
                        {"accountId": "acc_plus", "remainingCredits": 1260},
                        {"accountId": "acc_team", "remainingCredits": 222.75},
                        {"accountId": "platform", "remainingCredits": 999},
                    ],
                },
                "secondary": {
                    "accounts": [
                        {"accountId": "acc_plus", "remainingCredits": 2000},
                        {"accountId": "acc_team", "remainingCredits": 500},
                    ],
                },
            },
        },
        [
            {
                "accountId": "acc_plus",
                "email": "dkfhddla@gmail.com",
                "displayName": "",
                "providerKind": "chatgpt_web",
            },
            {
                "accountId": "acc_team",
                "email": "jacob@vonvon.me",
                "displayName": "Jacob",
                "providerKind": "chatgpt_web",
            },
            {
                "accountId": "platform",
                "displayName": "시나몬",
                "providerKind": "openai_platform",
            },
        ],
    )

    assert summary is not None
    assert summary.title == "5h Remaining"
    assert summary.center_value == "1.48K"
    assert summary.total_label == "Total 2.48K · 40% used"
    assert summary.used_value == 997.25
    assert [segment.label for segment in summary.segments] == ["dkfhddla@gmail.com", "Jacob"]
    assert [segment.value for segment in summary.segments] == [1260, 222.75]


def test_build_primary_donut_summary_only_applies_secondary_constraint_with_percent() -> None:
    summary = build_primary_donut_summary(
        {
            "summary": {
                "primaryWindow": {
                    "capacityCredits": 225,
                },
            },
            "windows": {
                "primary": {
                    "accounts": [
                        {"accountId": "acc_plus", "remainingCredits": 202.5},
                    ],
                },
                "secondary": {
                    "accounts": [
                        {"accountId": "acc_plus", "remainingCredits": 0},
                    ],
                },
            },
        },
        [
            {
                "accountId": "acc_plus",
                "email": "plus@example.com",
                "providerKind": "chatgpt_web",
                "usage": {
                    "primaryRemainingPercent": 90,
                    "secondaryRemainingPercent": None,
                },
            },
        ],
    )

    assert summary is not None
    assert summary.center_value == "202.5"
    assert summary.used_value == 22.5
    assert [segment.value for segment in summary.segments] == [202.5]


def test_unavailable_snapshot_keeps_5h_placeholder() -> None:
    snapshot = build_unavailable_snapshot("Authentication required")

    assert snapshot.title == "5h --"
    assert snapshot.error_message == "Authentication required"


def test_account_cards_format_remaining_dropdown_summary_values() -> None:
    cards = build_account_cards(
        [
            {
                "accountId": "acc_team",
                "displayName": "jacob@vonvon.me",
                "planType": "team",
                "status": "active",
                "usage": {
                    "primaryRemainingPercent": 1,
                    "secondaryRemainingPercent": 96,
                },
                "resetAtPrimary": "2026-01-01T17:34:56Z",
                "resetAtSecondary": "2026-01-03T06:34:56Z",
            },
        ]
    )

    assert len(cards) == 1
    card = cards[0]
    assert card.title == "jacob@vonvon.me"
    assert card.subtitle == "Team"
    assert card.status_label == "Active"
    assert card.primary_percent == 1
    assert card.secondary_percent == 96
    assert card.details_path == "/accounts?selected=acc_team"


def test_account_cards_include_openai_platform_metadata() -> None:
    cards = build_account_cards(
        [
            {
                "accountId": "platform",
                "displayName": "시나몬",
                "providerKind": "openai_platform",
                "routingSubjectId": "subject-platform-1",
                "status": "active",
            },
        ]
    )

    assert len(cards) == 1
    card = cards[0]
    assert card.title == "시나몬"
    assert card.subtitle == "OpenAI Platform API key | Subject subject-platform-1"
    assert card.shows_quota is False
    assert card.details_path == "/accounts?selected=platform"


def test_reset_label_formats_relative_time() -> None:
    now = datetime(2026, 1, 1, 12, 35, tzinfo=timezone.utc)

    assert format_reset_label("2026-01-01T17:34:56Z", now=now) == "in 4h 59m"
    assert format_reset_label("2026-01-03T06:34:56Z", now=now) == "in 1d 17h"
    assert format_reset_label("2026-01-01T12:34:56Z", now=now) == "now"


def test_remaining_percent_clamps_and_handles_missing_values() -> None:
    assert remaining_percent(72.4) == 72
    assert remaining_percent(-10) == 0
    assert remaining_percent(150) == 100
    assert remaining_percent(None) is None


def test_count_account_statuses_ignores_malformed_entries() -> None:
    counts = count_account_statuses(
        [
            {"status": "active"},
            {"status": "quota_exceeded"},
            {"status": "deactivated"},
            "bad",
        ]
    )

    assert counts.total == 3
    assert counts.active == 1
    assert counts.limited == 1
    assert counts.deactivated == 1


def test_cookie_header_accepts_session_id_or_raw_cookie_header() -> None:
    assert build_cookie_header("abc") == "codex_lb_dashboard_session=abc"
    assert build_cookie_header("codex_lb_dashboard_session=abc") == "codex_lb_dashboard_session=abc"
    assert build_cookie_header("  ") is None


def test_compact_number_formatting() -> None:
    assert format_compact_number(999) == "999"
    assert format_compact_number(1200) == "1.2K"
    assert format_compact_number(1_000_000) == "1M"


def test_donut_value_formatting_keeps_fractional_credits() -> None:
    assert format_donut_value(222.75) == "222.75"
    assert format_donut_value(1482.75) == "1.48K"
