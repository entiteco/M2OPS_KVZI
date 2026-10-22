"""Zone Bronze : un fichier JSON par item brut dans MinIO, sous articles_bruts/.

La clé du fichier est calculée à partir de (source, lien) : un item déjà
écrit a déjà sa clé, on ne l'écrit pas une deuxième fois.
"""

import hashlib
import io
import json
import os
import re
import unicodedata

from minio import Minio
from minio.error import S3Error

PREFIXE = "articles_bruts"


def identifiant(source: str, lien: str) -> str:
    """Identifiant stable d'un item, dérivé de la clé naturelle (source, lien)."""
    return hashlib.sha256(f"{source}\n{lien}".encode("utf-8")).hexdigest()[:16]


def slug(texte: str) -> str:
    sans_accents = (
        unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode()
    )
    return re.sub(r"[^a-z0-9]+", "-", sans_accents.lower()).strip("-")


def cle(source: str, lien: str) -> str:
    return f"{PREFIXE}/{slug(source)}/{identifiant(source, lien)}.json"


def client_minio() -> Minio:
    return Minio(
        os.environ.get("MINIO_ENDPOINT", "localhost:9000"),
        access_key=os.environ.get("MINIO_ACCESS_KEY", "minioadmin"),
        secret_key=os.environ.get("MINIO_SECRET_KEY", "minioadmin"),
        secure=False,
    )


class Bronze:
    def __init__(self, client=None, bucket: str | None = None):
        self.client = client or client_minio()
        self.bucket = bucket or os.environ.get("BRONZE_BUCKET", "bronze")
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)

    def existe(self, cle_objet: str) -> bool:
        try:
            self.client.stat_object(self.bucket, cle_objet)
            return True
        except S3Error as erreur:
            if erreur.code in ("NoSuchKey", "NoSuchObject"):
                return False
            raise

    def ecrire_si_absent(self, item: dict) -> bool:
        """Écrit l'item s'il n'existe pas encore. Renvoie True s'il a été écrit."""
        cle_objet = cle(item["source"], item["lien"])
        if self.existe(cle_objet):
            return False
        contenu = json.dumps(item, ensure_ascii=False, indent=2).encode("utf-8")
        self.client.put_object(
            self.bucket,
            cle_objet,
            io.BytesIO(contenu),
            length=len(contenu),
            content_type="application/json",
        )
        return True
