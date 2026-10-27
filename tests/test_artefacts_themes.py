import hashlib

from src.themes.passage import ecrire_artefact


def test_manifeste_reference_contenu_exact(faux_minio):
    manifeste = {}
    ecrire_artefact(faux_minio, "mlops", "runs/test", "entree.json", b"[]", manifeste)
    objet = manifeste["entree.json"]
    contenu = faux_minio.buckets[objet["bucket"]][objet["cle"]]
    assert contenu == b"[]" and objet["octets"] == len(contenu)
    assert objet["sha256"] == hashlib.sha256(contenu).hexdigest()
