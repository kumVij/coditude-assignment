"""Encrypt legacy candidate contact fields and clear plaintext storage."""
from alembic import op
import sqlalchemy as sa

from app.services.security import encrypt_pii, pii_hash

revision = "002_encrypt_legacy_candidate_pii"
down_revision = "001_security"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    rows = connection.execute(sa.text("SELECT id, mobile_number, email FROM candidates")).mappings().all()
    for row in rows:
        mobile = row["mobile_number"] or ""
        email = row["email"]
        connection.execute(
            sa.text(
                "UPDATE candidates SET mobile_number_encrypted=:mobile_encrypted, "
                "mobile_number_hash=:mobile_hash, email_encrypted=:email_encrypted, "
                "mobile_number='', email=NULL WHERE id=:id"
            ),
            {
                "id": row["id"],
                "mobile_encrypted": encrypt_pii(mobile),
                "mobile_hash": pii_hash(mobile) if mobile else None,
                "email_encrypted": encrypt_pii(email),
            },
        )


def downgrade() -> None:
    raise NotImplementedError("PII downgrade would restore plaintext values")