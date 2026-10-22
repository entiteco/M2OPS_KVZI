import os
import sys
from pathlib import Path

import pytest

# src/ est à la racine du dépôt en local et en CI, mais monté dans
# /opt/airflow/dags/ dans le conteneur Airflow (bin/test).
for racine in (Path(__file__).resolve().parents[1], Path("/opt/airflow/dags")):
    if (racine / "src").is_dir() and str(racine) not in sys.path:
        sys.path.insert(0, str(racine))


class FauxMinio:
    """Remplace le client MinIO dans les tests : les objets restent en mémoire."""

    def __init__(self):
        self.buckets = {}

    def bucket_exists(self, bucket):
        return bucket in self.buckets

    def make_bucket(self, bucket):
        self.buckets[bucket] = {}

    def stat_object(self, bucket, cle):
        from minio.error import S3Error

        if cle not in self.buckets[bucket]:
            raise S3Error("NoSuchKey", "objet absent", cle, None, None, None)
        return cle

    def put_object(self, bucket, cle, data, length, content_type=None):
        self.buckets[bucket][cle] = data.read(length)


@pytest.fixture
def faux_minio():
    return FauxMinio()


@pytest.fixture
def db():
    """Connexion à une base de test migrée et vide. En CI et dans bin/test,
    GAZETTE_TEST_DB_URL est défini ; sinon les tests concernés sont ignorés."""
    url = os.environ.get("GAZETTE_TEST_DB_URL")
    if not url:
        pytest.skip("GAZETTE_TEST_DB_URL non défini : pas de base de test")

    from src.stockage.migrer import migrer
    from src.stockage.sources import connexion

    migrer(url)
    conn = connexion(url)
    with conn, conn.cursor() as cur:
        cur.execute("TRUNCATE sources")
    yield conn
    conn.close()
