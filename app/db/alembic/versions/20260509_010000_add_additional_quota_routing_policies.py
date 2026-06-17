from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260509_010000_add_additional_quota_routing_policies"
down_revision = "20260506_000000_add_account_routing_policy"
branch_labels = None
depends_on = None


def _columns(table_name: str) -> set[str] | None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table_name):
        return None
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    columns = _columns("dashboard_settings")
    if columns is None or "additional_quota_routing_policies_json" in columns:
        return

    with op.batch_alter_table("dashboard_settings") as batch_op:
        batch_op.add_column(
            sa.Column(
                "additional_quota_routing_policies_json",
                sa.Text(),
                server_default="{}",
                nullable=False,
            )
        )


def downgrade() -> None:
    columns = _columns("dashboard_settings")
    if columns is None or "additional_quota_routing_policies_json" not in columns:
        return

    with op.batch_alter_table("dashboard_settings") as batch_op:
        batch_op.drop_column("additional_quota_routing_policies_json")
