"""align platform identity status with reauth_required account status

Revision ID: 20260617_010000_align_platform_identity_reauth_status
Revises: 20260617_000000_merge_v1_20_integration_heads
Create Date: 2026-06-17
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260617_010000_align_platform_identity_reauth_status"
down_revision = "20260617_000000_merge_v1_20_integration_heads"
branch_labels = None
depends_on = None

_ACCOUNT_STATUS_VALUES = (
    "active",
    "rate_limited",
    "quota_exceeded",
    "paused",
    "reauth_required",
    "deactivated",
)

_LEGACY_ACCOUNT_STATUS_VALUES = (
    "active",
    "rate_limited",
    "quota_exceeded",
    "paused",
    "deactivated",
)


def _account_status_enum(values: tuple[str, ...]) -> sa.Enum:
    return sa.Enum(
        *values,
        name="account_status",
        validate_strings=True,
        create_type=False,
    )


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        return

    with op.batch_alter_table("openai_platform_identities") as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=_account_status_enum(_LEGACY_ACCOUNT_STATUS_VALUES),
            type_=_account_status_enum(_ACCOUNT_STATUS_VALUES),
            existing_nullable=False,
            existing_server_default=sa.text("'active'"),
            server_default=sa.text("'active'"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        return

    op.execute(sa.text("UPDATE openai_platform_identities SET status = 'deactivated' WHERE status = 'reauth_required'"))
    with op.batch_alter_table("openai_platform_identities") as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=_account_status_enum(_ACCOUNT_STATUS_VALUES),
            type_=_account_status_enum(_LEGACY_ACCOUNT_STATUS_VALUES),
            existing_nullable=False,
            existing_server_default=sa.text("'active'"),
            server_default=sa.text("'active'"),
        )
