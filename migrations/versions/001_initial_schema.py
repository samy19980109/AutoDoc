"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-02-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "repositories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("github_url", sa.String(500), nullable=False),
        sa.Column("default_branch", sa.String(100), server_default="main"),
        sa.Column("confluence_space_key", sa.String(50), nullable=True),
        sa.Column("config_json", sa.JSON(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id", name="pk_repositories"),
        sa.UniqueConstraint("github_url", name="uq_repositories_github_url"),
    )

    op.create_table(
        "page_mappings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("repo_id", sa.Integer(), nullable=False),
        sa.Column("code_path", sa.String(1000), nullable=False),
        sa.Column("doc_type", sa.Enum("api_reference", "architecture", "walkthrough", name="doctype"), nullable=False),
        sa.Column("confluence_page_id", sa.String(100), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["repo_id"], ["repositories.id"], name="fk_page_mappings_repo_id_repositories"),
        sa.PrimaryKeyConstraint("id", name="pk_page_mappings"),
    )

    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("repo_id", sa.Integer(), nullable=False),
        sa.Column("trigger_type", sa.Enum("webhook", "manual", "scheduled", name="triggertype"), nullable=False),
        sa.Column("status", sa.Enum("pending", "processing", "completed", "failed", name="jobstatus"), server_default="pending"),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["repo_id"], ["repositories.id"], name="fk_jobs_repo_id_repositories"),
        sa.PrimaryKeyConstraint("id", name="pk_jobs"),
    )

    op.create_table(
        "processing_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("step", sa.String(100), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], name="fk_processing_logs_job_id_jobs"),
        sa.PrimaryKeyConstraint("id", name="pk_processing_logs"),
    )


def downgrade() -> None:
    op.drop_table("processing_logs")
    op.drop_table("jobs")
    op.drop_table("page_mappings")
    op.drop_table("repositories")
    op.execute("DROP TYPE IF EXISTS doctype")
    op.execute("DROP TYPE IF EXISTS triggertype")
    op.execute("DROP TYPE IF EXISTS jobstatus")
