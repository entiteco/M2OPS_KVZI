from src.normalisation.dates import est_dans_le_futur
from src.normalisation.regles import (
    SEUIL_REPRISE,
    r01_publi,
    r02_rubrique_hors_sujet,
    r03_depeche_reprise,
    r04_titre_vide,
    r05_date_future,
    r06_encodage,
    r07_doublon,
)
from src.normalisation.texte import (
    cle_titre,
    extrait_borne,
    normaliser_espaces,
    reparer_mojibake,
)

RECUPERE_LE = "2026-10-20T12:00:00+00:00"


def item(**champs):
    base = {
        "id": "a1",
        "source": "Le Monde",
        "lien": "https://example.fr/a",
        "titre": "Un titre",
        "resume": "Un extrait",
        "publie_le": "2026-10-20T11:00:00+00:00",
        "recupere_le": RECUPERE_LE,
        "rubrique": None,
    }
    base.update(champs)
    return base


# texte

def test_reparer_mojibake():
    assert reparer_mojibake("Ã©conomie") == "économie"


def test_reparer_mojibake_laisse_le_texte_sain():
    assert reparer_mojibake("économie") == "économie"


def test_normaliser_espaces():
    assert normaliser_espaces("  un   deux\n trois ") == "un deux trois"


def test_extrait_borne_coupe_sur_un_mot():
    assert extrait_borne("un deux trois", longueur=8) == "un deux…"


def test_extrait_borne_garde_un_texte_court():
    assert extrait_borne("court", longueur=300) == "court"


def test_cle_titre_ignore_accents_casse_et_ponctuation():
    assert cle_titre("Macron, à Paris !") == cle_titre("macron a paris")


# dates

def test_date_future_detectee():
    assert est_dans_le_futur("2026-10-25T00:00:00+00:00", RECUPERE_LE)


def test_date_passee_acceptee():
    assert not est_dans_le_futur("2026-10-19T00:00:00+00:00", RECUPERE_LE)


def test_date_absente_non_rejetee_par_cette_regle():
    assert not est_dans_le_futur(None, RECUPERE_LE)


# règles à un item

def test_r01_publi():
    assert r01_publi(item(rubrique="Publi-reportage"))
    assert not r01_publi(item(rubrique="Politique"))


def test_r02_rubrique_hors_sujet():
    assert r02_rubrique_hors_sujet(item(rubrique="Horoscope du jour"))
    assert not r02_rubrique_hors_sujet(item(rubrique="Économie"))


def test_r04_titre_vide():
    assert r04_titre_vide(item(titre="   "))
    assert not r04_titre_vide(item(titre="Un titre"))


def test_r05_date_future():
    assert r05_date_future(item(publie_le="2027-01-01T00:00:00+00:00"))
    assert not r05_date_future(item())


def test_r06_encodage_non_reparable():
    assert r06_encodage(item(titre="Texte � cassé"))
    assert not r06_encodage(item(titre="Ã©conomie"))  # réparable : gardé après correction


# règles de lot

def test_r03_depeche_reprise_a_partir_du_seuil():
    lot = [
        item(id=f"s{i}", source=f"Titre {i}", titre="Macron annonce une réforme")
        for i in range(SEUIL_REPRISE)
    ]
    assert r03_depeche_reprise(lot) == {f"s{i}" for i in range(SEUIL_REPRISE)}


def test_r03_depeche_sous_le_seuil_gardee():
    lot = [
        item(id="x1", source="A", titre="Même titre"),
        item(id="x2", source="B", titre="Même titre"),
    ]
    assert r03_depeche_reprise(lot) == set()


def test_r07_doublon_meme_source_garde_le_premier():
    lot = [
        item(id="d1", titre="Macron annonce"),
        item(id="d2", titre="Macron annonce !"),
    ]
    assert r07_doublon(lot) == {"d2"}


def test_r07_meme_titre_dans_deux_sources_non_doublon():
    lot = [
        item(id="e1", source="A", titre="Macron annonce"),
        item(id="e2", source="B", titre="Macron annonce"),
    ]
    assert r07_doublon(lot) == set()
