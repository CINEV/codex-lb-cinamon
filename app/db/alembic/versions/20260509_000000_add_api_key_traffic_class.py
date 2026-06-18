from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260509_000000_add_api_key_traffic_class"
down_revision = "20260601_000000_merge_relative_availability_and_usage_raw_heads"
branch_labels = None
depends_on = None


def _columns(table_name: str) -> set[str] | None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table_name):
        return None
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    columns = _columns("api_keys")
    if columns is None or "traffic_class" in columns:
        return

    with op.batch_alter_table("api_keys") as batch_op:
        batch_op.add_column(
            sa.Column(
                "traffic_class",
                sa.String(),
                server_default="foreground",
                nullable=False,
            )
        )


def downgrade() -> None:
    columns = _columns("api_keys")
    if columns is None or "traffic_class" not in columns:
        return

    with op.batch_alter_table("api_keys") as batch_op:
        batch_op.drop_column("traffic_class")
