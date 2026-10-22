from src.normalisation.passage import appliquer_lot, rapport, regle_item, traiter
from src.normalisation import regles

RECUPERE_LE = "2026-10-20T12:00:00+00:00"


def brut(**champs):
    base = {
        "id": "p1",
        "source": "Le Monde",
        "lien": "https://example.fr/a",
        "titre": "Un titre",
        "resume": "Un extrait",
        "publie_le": "2026-10-20T11:00:00+00:00",
        "recupere_le": RECUPERE_LE,
        "rubrique": None,
        "payload": {"links": []},
    }
    base.update(champs)
    return base


def test_publi_marqueur_explicite_et_pas_publique():
    assert regles.r01_publi(brut(rubrique="Publi-reportage"))
    assert not regles.r01_publi(brut(titre="Enquête sur le ministère public"))


def test_horoscope_et_jeux_ecartes_concours_gardes():
    assert regles.r02_rubrique_hors_sujet(brut(rubrique="Horoscope"))
    assert regles.r02_rubrique_hors_sujet(brut(titre="La Dépêche lance son espace jeux"))
    assert not regles.r02_rubrique_hors_sujet(brut(titre="Concours de saut d'obstacles"))


def test_regle_item_renvoie_la_premiere_regle_qui_ecarte():
    assert regle_item(brut(titre="  ", rubrique="Publi-reportage")) == "R04_titre_vide"
    assert regle_item(brut()) is None


def test_traiter_separe_gardes_et_rejets():
    items = [
        brut(id="a", titre="Article propre"),
        brut(id="b", titre="", source="Le Figaro"),
        brut(id="c", titre="Pub", rubrique="Publi-reportage"),
    ]
    gardes, rejets = traiter(items, "P1")
    assert [g["id"] for g in gardes] == ["a"]
    assert {r["id"]: r["regle"] for r in rejets} == {
        "b": "R04_titre_vide",
        "c": "R01_publi",
    }


def test_traiter_normalise_titre_et_extrait():
    gardes, _ = traiter([brut(titre="  Un   titre ", resume="<b>Court</b>")], "P1")
    assert gardes[0]["titre"] == "Un titre"
    assert gardes[0]["extrait"] == "Court"
    assert "resume" not in gardes[0] and "payload" not in gardes[0]


def test_appliquer_lot_marque_les_ecartes():
    items = [brut(id="x", titre="T"), brut(id="y", titre="T")]
    gardes, rejets = appliquer_lot(items, "R07_doublon", lambda _: {"y"})
    assert [g["id"] for g in gardes] == ["x"]
    assert rejets == [{"id": "y", "source": "Le Monde", "regle": "R07_doublon"}]


def test_rapport_compte_par_regle_et_par_source():
    rejets = [
        {"id": "1", "source": "A", "regle": "R01_publi"},
        {"id": "2", "source": "A", "regle": "R01_publi"},
        {"id": "3", "source": "B", "regle": "R04_titre_vide"},
    ]
    texte = rapport(5, [{"source": "C"}, {"source": "C"}], rejets, "2026-10-22")
    assert "- Entrés : 5" in texte
    assert "| R01_publi | 2 |" in texte
    assert "| A | R01_publi | 2 |" in texte
    assert "1. R01_publi (2)" in texte
