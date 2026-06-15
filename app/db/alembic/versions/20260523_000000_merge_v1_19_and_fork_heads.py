"""merge v1.19 upstream and fork heads

Revision ID: 20260523_000000_merge_v1_19_and_fork_heads
Revises: 20260512_000000_merge_v1_16_integration_heads, 20260513_000000_add_accounts_alias
Create Date: 2026-05-23
"""

from __future__ import annotations

revision = "20260523_000000_merge_v1_19_and_fork_heads"
down_revision = (
    "20260512_000000_merge_v1_16_integration_heads",
    "20260513_000000_add_accounts_alias",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    return


def downgrade() -> None:
    return
