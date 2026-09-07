"""Add screening batches and dead-letter records."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "003_reliability"
down_revision = "002_encrypt_legacy_candidate_pii"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    tables = set(inspect(connection).get_table_names())
    if "screening_batches" not in tables:
        op.create_table(
            "screening_batches", sa.Column("id", sa.String(), primary_key=True),
            sa.Column("job_id", sa.String(), nullable=False), sa.Column("owner_id", sa.String(), nullable=True),
            sa.Column("status", sa.String(), nullable=False, server_default="QUEUED"),
            sa.Column("candidate_count", sa.String(), nullable=False, server_default="0"),
            sa.Column("candidate_ids", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("error", sa.Text(), nullable=True), sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
    else:
        existing_columns = {column["name"] for column in inspect(connection).get_columns("screening_batches")}
        if "candidate_ids" not in existing_columns:
            with op.batch_alter_table("screening_batches") as batch:
                batch.add_column(sa.Column("candidate_ids", sa.Text(), nullable=False, server_default="[]"))
    if "dead_letters" not in tables:
        op.create_table(
            "dead_letters", sa.Column("id", sa.String(), primary_key=True), sa.Column("batch_id", sa.String(), nullable=True),
            sa.Column("job_id", sa.String(), nullable=True), sa.Column("candidate_id", sa.String(), nullable=True),
            sa.Column("reason", sa.String(), nullable=False), sa.Column("payload", sa.JSON(), nullable=True),
            sa.Column("attempts", sa.String(), nullable=False, server_default="1"), sa.Column("created_at", sa.DateTime(), nullable=True),
        )
    existing_indexes = {index["name"] for table in ("screening_batches", "dead_letters") for index in inspect(connection).get_indexes(table)}
    for name, table, column in (("ix_screening_batches_job_id", "screening_batches", "job_id"), ("ix_screening_batches_owner_id", "screening_batches", "owner_id"), ("ix_dead_letters_batch_id", "dead_letters", "batch_id"), ("ix_dead_letters_job_id", "dead_letters", "job_id"), ("ix_dead_letters_candidate_id", "dead_letters", "candidate_id")):
        if name not in existing_indexes:
            op.create_index(name, table, [column])


def downgrade() -> None:
    raise NotImplementedError("Reliability migration downgrade is intentionally disabled")