import json
from zipfile import ZipFile

import pytest

from src.stockage.bronze import cle, identifiant
from src.stockage.restaurer import exporter, lire_archive, restaurer_services


def article(**champs):
    source, lien = "Le Monde", "https://example.fr/article"
    return {
        "id": identifiant(source, lien),
        "source": source,
        "lien": lien,
        "titre": "Un titre",
        "resume": "Un extrait",
        "publie_le": "2026-10-23T10:00:00+00:00",
        "recupere_le": "2026-10-23T12:00:00+00:00",
        **champs,
    }


@pytest.mark.parametrize("separateur", ["/", "\\"])
def test_archive_accepte_chemins_linux_et_windows(tmp_path, separateur):
    item = article()
    chemin = tmp_path / "bronze.zip"
    nom = ("bronze/" + cle(item["source"], item["lien"])).replace("/", separateur)
    with ZipFile(chemin, "w") as archive:
        archive.writestr(nom, json.dumps(item))
    assert lire_archive(chemin) == [item]


@pytest.mark.parametrize("nom", ["../../article.json", "bronze/articles_bruts/le-monde/faux.json"])
def test_archive_refuse_chemins_et_identifiants_incoherents(tmp_path, nom):
    chemin = tmp_path / "bronze.zip"
    with ZipFile(chemin, "w") as archive:
        archive.writestr(nom, json.dumps(article()))
    with pytest.raises(ValueError):
        lire_archive(chemin)


def test_archive_vide_refusee(tmp_path):
    chemin = tmp_path / "bronze.zip"
    with ZipFile(chemin, "w"):
        pass
    with pytest.raises(ValueError, match="aucun article"):
        lire_archive(chemin)


def test_export_separe_rejets_et_silver_sans_payload_et_sans_accumuler(tmp_path):
    items = [article(), article(id="rejet", titre="")]
    for _ in range(2):
        bilan = exporter(items, tmp_path)
    assert (bilan["entres"], bilan["gardes"], bilan["rejetes"]) == (2, 1, 1)
    gardes = [json.loads(ligne) for ligne in (tmp_path / "articles_propres.jsonl").read_text().splitlines()]
    assert len(gardes) == 1
    assert "resume" not in gardes[0] and "payload" not in gardes[0]
    assert gardes[0]["extrait"] == "Un extrait"
    rejet = json.loads((tmp_path / "rejets.jsonl").read_text())
    assert rejet["regle"] == "R04_titre_vide"
    assert "- Gardés (articles_propres) : 1" in (tmp_path / "qualite.md").read_text()


def test_import_bronze_seul_preserve_silver_et_reste_idempotent(monkeypatch, faux_minio):
    from src.stockage.bronze import Bronze

    monkeypatch.setattr("src.stockage.bronze.Bronze", lambda: Bronze(client=faux_minio))

    def connexion_interdite():
        pytest.fail("Un import Bronze seul ne doit pas ouvrir PostgreSQL")

    monkeypatch.setattr("src.stockage.sources.connexion", connexion_interdite)
    assert restaurer_services([article()], bronze_seul=True) == {
        "bronze_ajoutes": 1, "bronze_deja_presents": 0,
    }
    assert restaurer_services([article()], bronze_seul=True) == {
        "bronze_ajoutes": 0, "bronze_deja_presents": 1,
    }
