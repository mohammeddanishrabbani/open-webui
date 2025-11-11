"""add usage statistics table

Revision ID: f1c2d3e4f5a6
Revises: d31026856c01
Create Date: 2025-10-21 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from open_webui.migrations.util import get_existing_tables

# revision identifiers, used by Alembic.
revision: str = "f1c2d3e4f5a6"
down_revision: Union[str, None] = "d31026856c01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    existing_tables = set(get_existing_tables())

    if "usage_statistics" not in existing_tables:
        op.create_table(
            "usage_statistics",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("user_id", sa.String(), nullable=False),
            sa.Column("model_id", sa.String(), nullable=False),
            sa.Column("chat_type", sa.String(), nullable=False),
            sa.Column("message_count", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
            sa.Column("date_key", sa.String(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        
        # Create performance indexes
        op.create_index("usage_date_key_idx", "usage_statistics", ["date_key"])
        op.create_index("usage_user_model_date_idx", "usage_statistics", ["user_id", "model_id", "date_key"])
        op.create_index("usage_model_date_idx", "usage_statistics", ["model_id", "date_key"])
        op.create_index("usage_chat_type_idx", "usage_statistics", ["chat_type"])


def downgrade() -> None:
    op.drop_index("usage_chat_type_idx", table_name="usage_statistics")
    op.drop_index("usage_model_date_idx", table_name="usage_statistics")
    op.drop_index("usage_user_model_date_idx", table_name="usage_statistics")
    op.drop_index("usage_date_key_idx", table_name="usage_statistics")
    op.drop_table("usage_statistics")