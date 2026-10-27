"""Nom de grand thème, titre illustratif et provenance du nommage."""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE themes ADD COLUMN titre_representant text")
    op.execute("UPDATE themes SET titre_representant = nom")
    op.execute("ALTER TABLE themes ALTER COLUMN titre_representant SET NOT NULL")
    op.execute("ALTER TABLE themes ADD COLUMN nommage jsonb NOT NULL DEFAULT '{}'::jsonb")
    # PostgreSQL fige les colonnes d'une vue SELECT * à sa création.
    op.execute("DROP VIEW themes_courants")
    op.execute("""CREATE VIEW themes_courants AS SELECT t.* FROM themes t WHERE t.run_id = (
        SELECT id FROM runs WHERE statut = 'succes' ORDER BY commence_le DESC, id DESC LIMIT 1
    )""")


def downgrade():
    op.execute("DROP VIEW themes_courants")
    op.execute("ALTER TABLE themes DROP COLUMN nommage, DROP COLUMN titre_representant")
    op.execute("""CREATE VIEW themes_courants AS SELECT t.* FROM themes t WHERE t.run_id = (
        SELECT id FROM runs WHERE statut = 'succes' ORDER BY commence_le DESC, id DESC LIMIT 1
    )""")
