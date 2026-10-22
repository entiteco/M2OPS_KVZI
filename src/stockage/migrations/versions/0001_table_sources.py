"""Table sources : l'état de chaque flux suivi par la collecte.

Revision ID: 0001
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "sources",
        sa.Column("nom", sa.Text, primary_key=True),
        sa.Column("type", sa.Text, nullable=False),
        sa.Column("url_flux", sa.Text, nullable=False),
        sa.Column("actif", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("derniere_reussite", sa.DateTime(timezone=True)),
        sa.Column(
            "echecs_consecutifs", sa.Integer, nullable=False, server_default="0"
        ),
        sa.Column("etag", sa.Text),
        sa.Column("last_modified", sa.Text),
        sa.CheckConstraint("type IN ('PQN', 'PQR')", name="sources_type_valide"),
    )


def downgrade():
    op.drop_table("sources")
