"""Add resume, duplicate, and screening-round fields."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "004_hiring_depth"
down_revision = "003_reliability"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    candidates = {column["name"] for column in inspect(connection).get_columns("candidates")}
    with op.batch_alter_table("candidates") as batch:
        if "resume_text_encrypted" not in candidates:
            batch.add_column(sa.Column("resume_text_encrypted", sa.Text(), nullable=True))
        if "resume_skills" not in candidates:
            batch.add_column(sa.Column("resume_skills", sa.JSON(), nullable=True))
        if "resume_experience_years" not in candidates:
            batch.add_column(sa.Column("resume_experience_years", sa.Float(), nullable=True))
        if "identity_hash" not in candidates:
            batch.add_column(sa.Column("identity_hash", sa.String(), nullable=True))
    screening_calls = {column["name"] for column in inspect(connection).get_columns("screening_calls")}
    with op.batch_alter_table("screening_calls") as batch:
        if "round_number" not in screening_calls:
            batch.add_column(sa.Column("round_number", sa.String(), nullable=False, server_default="1"))
    batches = {column["name"] for column in inspect(connection).get_columns("screening_batches")}
    with op.batch_alter_table("screening_batches") as batch:
        if "round_number" not in batches:
            batch.add_column(sa.Column("round_number", sa.String(), nullable=False, server_default="1"))
    indexes = {index["name"] for index in inspect(connection).get_indexes("candidates")}
    if "ix_candidates_identity_hash" not in indexes:
        op.create_index("ix_candidates_identity_hash", "candidates", ["identity_hash"])


def downgrade() -> None:
    raise NotImplementedError("Hiring-depth migration downgrade is intentionally disabled")
