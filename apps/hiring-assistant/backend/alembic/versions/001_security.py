"""Add recruiter security and encrypted candidate fields."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "001_security"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    tables = set(inspect(connection).get_table_names())
    if "users" not in tables:
        op.create_table(
            "users",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("email", sa.String(), nullable=False),
            sa.Column("password_hash", sa.String(), nullable=False),
            sa.Column("is_active", sa.String(), nullable=False, server_default="true"),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
    if "webhook_events" not in tables:
        op.create_table(
            "webhook_events",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("event_key", sa.String(), nullable=False),
            sa.Column("event_type", sa.String(), nullable=True),
            sa.Column("received_at", sa.DateTime(), nullable=True),
        )
    existing_indexes = {
        index["name"]
        for table in ("users", "webhook_events")
        for index in inspect(connection).get_indexes(table)
    }
    if "ix_users_email" not in existing_indexes:
        op.create_index("ix_users_email", "users", ["email"], unique=True)
    if "ix_webhook_events_event_key" not in existing_indexes:
        op.create_index("ix_webhook_events_event_key", "webhook_events", ["event_key"], unique=True)
    existing_columns = {column["name"] for column in inspect(connection).get_columns("jobs")}
    with op.batch_alter_table("jobs") as batch:
        if "owner_id" not in existing_columns:
            batch.add_column(sa.Column("owner_id", sa.String(), nullable=True))
            batch.create_index("ix_jobs_owner_id", ["owner_id"])
    existing_columns = {column["name"] for column in inspect(connection).get_columns("candidates")}
    with op.batch_alter_table("candidates") as batch:
        if "mobile_number_encrypted" not in existing_columns:
            batch.add_column(sa.Column("mobile_number_encrypted", sa.Text(), nullable=True))
        if "mobile_number_hash" not in existing_columns:
            batch.add_column(sa.Column("mobile_number_hash", sa.String(), nullable=True))
        if "email_encrypted" not in existing_columns:
            batch.add_column(sa.Column("email_encrypted", sa.Text(), nullable=True))
        if "consent_obtained" not in existing_columns:
            batch.add_column(sa.Column("consent_obtained", sa.String(), nullable=False, server_default="false"))
        if "consent_at" not in existing_columns:
            batch.add_column(sa.Column("consent_at", sa.DateTime(), nullable=True))
        if "mobile_number_hash" not in existing_columns:
            batch.create_index("ix_candidates_mobile_number_hash", ["mobile_number_hash"])


def downgrade() -> None:
    raise NotImplementedError("Security migration downgrade is intentionally disabled")
