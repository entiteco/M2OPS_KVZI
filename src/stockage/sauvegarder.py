"""Export logique des objets MinIO vers un TAR sur stdout, sans données internes."""

import sys
import tarfile
from pathlib import PurePosixPath

from src.stockage.bronze import client_minio


def exporter_minio(client, sortie):
    with tarfile.open(fileobj=sortie, mode="w|") as archive:
        for bucket in client.list_buckets():
            for objet in client.list_objects(bucket.name, recursive=True):
                chemin = PurePosixPath(bucket.name) / objet.object_name
                if ".." in chemin.parts or chemin.is_absolute():
                    raise ValueError("Nom d'objet impropre à une archive TAR")
                info = tarfile.TarInfo(chemin.as_posix())
                info.size = objet.size
                info.mode = 0o600
                if objet.last_modified:
                    info.mtime = int(objet.last_modified.timestamp())
                reponse = client.get_object(bucket.name, objet.object_name)
                try:
                    archive.addfile(info, reponse)
                finally:
                    reponse.close()
                    reponse.release_conn()


if __name__ == "__main__":
    exporter_minio(client_minio(), sys.stdout.buffer)
