"""Un rejeu historique ne remplace pas les thèmes de la fenêtre courante."""

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE OR REPLACE VIEW themes_courants AS SELECT t.* FROM themes t
        WHERE t.run_id = (SELECT id FROM runs WHERE statut = 'succes'
            ORDER BY reference DESC, commence_le DESC, id DESC LIMIT 1)""")
    op.execute("""CREATE INDEX runs_fenetre ON runs (reference DESC, commence_le DESC)
        WHERE statut = 'succes'""")


def downgrade():
    op.execute("DROP INDEX runs_fenetre")
    op.execute("""CREATE OR REPLACE VIEW themes_courants AS SELECT t.* FROM themes t
        WHERE t.run_id = (SELECT id FROM runs WHERE statut = 'succes'
            ORDER BY commence_le DESC, id DESC LIMIT 1)""")
