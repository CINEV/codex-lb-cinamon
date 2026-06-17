"""merge v1.20 integration heads

Revision ID: 20260617_000000_merge_v1_20_integration_heads
Revises:
- 20260512_000000_merge_v1_16_integration_heads
- 20260611_000000_merge_dashboard_guest_and_weekly_useragent_heads
Create Date: 2026-06-17 00:00:00.000000
"""

from __future__ import annotations

revision = "20260617_000000_merge_v1_20_integration_heads"
down_revision = (
    "20260512_000000_merge_v1_16_integration_heads",
    "20260611_000000_merge_dashboard_guest_and_weekly_useragent_heads",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
