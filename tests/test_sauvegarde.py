import io
import tarfile
from types import SimpleNamespace

import pytest

from src.stockage.sauvegarder import exporter_minio


def test_export_logique_minio_preserve_contenu_et_libere_connexion():
    fermetures = []

    class Reponse(io.BytesIO):
        def release_conn(self):
            fermetures.append(True)

    client = SimpleNamespace(
        list_buckets=lambda: [SimpleNamespace(name="bronze")],
        list_objects=lambda *a, **k: [SimpleNamespace(object_name="articles/a.json", size=2, last_modified=None)],
        get_object=lambda *a: Reponse(b"{}"),
    )
    sortie = io.BytesIO()
    exporter_minio(client, sortie)
    with tarfile.open(fileobj=io.BytesIO(sortie.getvalue())) as archive:
        assert archive.extractfile("bronze/articles/a.json").read() == b"{}"
    assert fermetures == [True]


def test_export_refuse_traversee_repertoires():
    client = SimpleNamespace(
        list_buckets=lambda: [SimpleNamespace(name="bronze")],
        list_objects=lambda *a, **k: [SimpleNamespace(object_name="../secret", size=2)],
    )
    with pytest.raises(ValueError, match="TAR"):
        exporter_minio(client, io.BytesIO())
