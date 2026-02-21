"""Add Notion support — generalize destination platform

Revision ID: 002
Revises: 001
Create Date: 2026-02-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create the destination platform enum
    destination_platform_enum = sa.Enum(
        "confluence", "notion", name="destinationplatform"
    )
    destination_platform_enum.create(op.get_bind(), checkfirst=True)

    # Add destination_platform column with default 'confluence'
    op.add_column(
        "repositories",
        sa.Column(
            "destination_platform",
            destination_platform_enum,
            server_default="confluence",
            nullable=False,
        ),
    )

    # Add destination_config JSON column
    op.add_column(
        "repositories",
        sa.Column("destination_config", sa.JSON(), server_default="{}", nullable=False),
    )

    # Migrate existing confluence_space_key data into destination_config
    op.execute(
        """
        UPDATE repositories
        SET destination_config = jsonb_build_object('space_key', confluence_space_key)
        WHERE confluence_space_key IS NOT NULL AND confluence_space_key != ''
        """
    )

    # Drop the old confluence_space_key column
    op.drop_column("repositories", "confluence_space_key")

    # Rename confluence_page_id → destination_page_id in page_mappings
    op.alter_column(
        "page_mappings",
        "confluence_page_id",
        new_column_name="destination_page_id",
    )


def downgrade() -> None:
    # Rename destination_page_id back to confluence_page_id
    op.alter_column(
        "page_mappings",
        "destination_page_id",
        new_column_name="confluence_page_id",
    )

    # Re-add confluence_space_key column
    op.add_column(
        "repositories",
        sa.Column("confluence_space_key", sa.String(50), nullable=True),
    )

    # Migrate data back from destination_config
    op.execute(
        """
        UPDATE repositories
        SET confluence_space_key = destination_config->>'space_key'
        WHERE destination_config->>'space_key' IS NOT NULL
        """
    )

    # Drop the new columns
    op.drop_column("repositories", "destination_config")
    op.drop_column("repositories", "destination_platform")

    # Drop the enum
    op.execute("DROP TYPE IF EXISTS destinationplatform")
