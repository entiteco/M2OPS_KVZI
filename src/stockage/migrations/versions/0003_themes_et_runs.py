"""Cache embeddings, thèmes et traçage MLOps (TD 5)."""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE embeddings (
            texte_hash text NOT NULL,
            modele text NOT NULL,
            revision text NOT NULL,
            options_hash text NOT NULL,
            vecteur real[] NOT NULL,
            cree_le timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (texte_hash, modele, revision, options_hash)
        );
        CREATE TABLE runs (
            id text PRIMARY KEY,
            statut text NOT NULL CHECK (statut IN ('en_cours', 'succes', 'echec')),
            declencheur text NOT NULL,
            reference timestamptz NOT NULL,
            fenetre_debut timestamptz,
            fenetre_fin timestamptz,
            nb_articles integer,
            hash_entree text,
            config jsonb NOT NULL DEFAULT '{}',
            versions jsonb NOT NULL DEFAULT '{}',
            code_hash text NOT NULL,
            metriques jsonb NOT NULL DEFAULT '{}',
            artefacts jsonb NOT NULL DEFAULT '{}',
            erreur text,
            commence_le timestamptz NOT NULL DEFAULT now(),
            termine_le timestamptz
        );
        CREATE TABLE themes (
            run_id text NOT NULL REFERENCES runs(id),
            theme_id integer NOT NULL CHECK (theme_id >= 0),
            nom text NOT NULL,
            mots_cles jsonb NOT NULL,
            taille integer NOT NULL CHECK (taille > 0),
            article_representant text NOT NULL,
            PRIMARY KEY (run_id, theme_id)
        );
        CREATE TABLE articles_themes (
            run_id text NOT NULL REFERENCES runs(id),
            article_id text NOT NULL,
            theme_id integer,
            PRIMARY KEY (run_id, article_id),
            FOREIGN KEY (run_id, theme_id) REFERENCES themes(run_id, theme_id)
        );
        CREATE INDEX runs_derniers ON runs (commence_le DESC) WHERE statut = 'succes';
        CREATE VIEW themes_courants AS
            SELECT t.* FROM themes t WHERE t.run_id = (
                SELECT id FROM runs WHERE statut = 'succes'
                ORDER BY commence_le DESC, id DESC LIMIT 1
            );
    """)


def downgrade():
    op.execute("""
        DROP VIEW themes_courants;
        DROP TABLE articles_themes;
        DROP TABLE themes;
        DROP TABLE runs;
        DROP TABLE embeddings;
    """)
