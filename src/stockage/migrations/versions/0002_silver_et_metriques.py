"""Zone Silver en base (articles_propres) et historique des métriques qualité.

Revision ID: 0002
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "articles_propres",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("source", sa.Text, nullable=False),
        sa.Column("lien", sa.Text, nullable=False),
        sa.Column("titre", sa.Text, nullable=False),
        sa.Column("extrait", sa.Text, nullable=False, server_default=""),
        sa.Column("publie_le", sa.DateTime(timezone=True)),
        sa.Column("recupere_le", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rubrique", sa.Text),
        sa.Column("passage", sa.Text, nullable=False),
    )
    op.create_index("articles_propres_source", "articles_propres", ["source"])

    # Une ligne par passage et par source : l'historique des métriques qualité.
    op.create_table(
        "metriques_passage",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("passage", sa.Text, nullable=False),
        sa.Column("source", sa.Text, nullable=False),
        sa.Column("entres", sa.Integer, nullable=False),
        sa.Column("gardes", sa.Integer, nullable=False),
        sa.Column("rejetes", sa.Integer, nullable=False),
        sa.Column("taux_rejet", sa.Float, nullable=False),
        sa.Column(
            "mesure_le",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("passage", "source", name="metriques_passage_unique"),
    )


def downgrade():
    op.drop_table("metriques_passage")
    op.drop_index("articles_propres_source", table_name="articles_propres")
    op.drop_table("articles_propres")
