import json
import os
from pathlib import Path

from src.stockage import sources
from src.stockage.bronze import Bronze, cle, identifiant

# Dans le conteneur, le CSV est monté ailleurs (cf. docker-compose.yml)
SOURCES_CSV = os.environ.get(
    "SOURCES_CSV", Path(__file__).resolve().parents[1] / "docs" / "sources.csv"
)


def item(lien="https://exemple.fr/a"):
    return {"source": "L'Humanité", "lien": lien, "titre": "Un titre"}


# --- Zone Bronze ---------------------------------------------------------


def test_identifiant_stable_et_propre_a_la_source():
    assert identifiant("Le Monde", "https://x/a") == identifiant("Le Monde", "https://x/a")
    assert identifiant("Le Monde", "https://x/a") != identifiant("Le Figaro", "https://x/a")


def test_cle_range_par_source():
    assert cle("L'Humanité", "https://exemple.fr/a").startswith(
        "articles_bruts/l-humanite/"
    )


def test_bronze_cree_le_bucket(faux_minio):
    Bronze(faux_minio, "bronze")
    assert faux_minio.bucket_exists("bronze")


def test_bronze_n_ecrit_pas_deux_fois_le_meme_item(faux_minio):
    bronze = Bronze(faux_minio, "bronze")
    assert bronze.ecrire_si_absent(item()) is True
    assert bronze.ecrire_si_absent(item()) is False
    assert bronze.ecrire_si_absent(item("https://exemple.fr/b")) is True
    assert len(faux_minio.buckets["bronze"]) == 2


def test_bronze_ecrit_le_json_tel_quel(faux_minio):
    bronze = Bronze(faux_minio, "bronze")
    bronze.ecrire_si_absent(item())
    (contenu,) = faux_minio.buckets["bronze"].values()
    assert json.loads(contenu) == item()


# --- Table sources -------------------------------------------------------


def test_lire_csv_separe_les_flux_multiples():
    lues = sources.lire_csv(SOURCES_CSV)
    noms = [source["nom"] for source in lues]
    assert "Les Échos (1)" in noms and "Les Échos (2)" in noms
    assert all(source["url_flux"].startswith("https://") for source in lues)
    assert {source["type"] for source in lues} == {"PQN", "PQR"}


def test_synchroniser_ne_reinitialise_pas_l_etat(db):
    sources.synchroniser(db, sources.lire_csv(SOURCES_CSV))
    sources.enregistrer_echec(db, "Le Monde")
    sources.synchroniser(db, sources.lire_csv(SOURCES_CSV))
    le_monde = next(s for s in sources.sources_actives(db) if s["nom"] == "Le Monde")
    assert le_monde["echecs_consecutifs"] == 1


def test_mise_en_sommeil_au_troisieme_echec(db):
    sources.synchroniser(db, [{"nom": "A", "type": "PQN", "url_flux": "https://a"}])
    assert sources.enregistrer_echec(db, "A") is False
    assert sources.enregistrer_echec(db, "A") is False
    assert sources.enregistrer_echec(db, "A") is True
    assert sources.sources_actives(db) == []


def test_reussite_remet_les_echecs_a_zero_et_garde_l_etag(db):
    sources.synchroniser(db, [{"nom": "A", "type": "PQN", "url_flux": "https://a"}])
    sources.enregistrer_echec(db, "A")
    sources.enregistrer_reussite(db, "A", '"abc"', "Tue, 20 Oct 2026 12:00:00 GMT")
    sources.enregistrer_reussite(db, "A", None, None)  # 304 : rien de nouveau
    (a,) = sources.sources_actives(db)
    assert a["echecs_consecutifs"] == 0
    assert a["derniere_reussite"] is not None
    assert a["etag"] == '"abc"'
