"""Règles d'exclusion. Chaque règle est documentée dans docs/qualite.md.

Une règle à un item renvoie True si elle écarte l'item.
Une règle de lot (R03, R07) renvoie l'ensemble des identifiants écartés.
"""

import re
from collections import defaultdict

from src.normalisation.dates import est_dans_le_futur
from src.normalisation.texte import cle_titre, reparer_mojibake

RUBRIQUES_PUBLI = re.compile(r"publi|partenai|sponsor", re.IGNORECASE)
RUBRIQUES_HORS_SUJET = re.compile(
    r"horoscope|programme tv|jeux|concours", re.IGNORECASE
)
# Une dépêche reprise à l'identique par ce nombre de sources ou plus est écartée.
SEUIL_REPRISE = 6
RESTE_ILLISIBLE = ("Ã", "Â", "�")


def r01_publi(item: dict) -> bool:
    return bool(item.get("rubrique") and RUBRIQUES_PUBLI.search(item["rubrique"]))


def r02_rubrique_hors_sujet(item: dict) -> bool:
    return bool(
        item.get("rubrique") and RUBRIQUES_HORS_SUJET.search(item["rubrique"])
    )


def r04_titre_vide(item: dict) -> bool:
    return not item.get("titre", "").strip()


def r05_date_future(item: dict) -> bool:
    return est_dans_le_futur(item.get("publie_le"), item["recupere_le"])


def r06_encodage(item: dict) -> bool:
    texte = item.get("titre", "") + " " + item.get("resume", "")
    texte = reparer_mojibake(texte)
    return any(marque in texte for marque in RESTE_ILLISIBLE)


def r03_depeche_reprise(items: list[dict]) -> set[str]:
    """Titres identiques repris par SEUIL_REPRISE sources ou plus : on ne garde rien."""
    sources_par_titre = defaultdict(set)
    ids_par_titre = defaultdict(list)
    for item in items:
        cle = cle_titre(item.get("titre", ""))
        if not cle:
            continue
        sources_par_titre[cle].add(item["source"])
        ids_par_titre[cle].append(item["id"])
    return {
        identifiant
        for cle, sources in sources_par_titre.items()
        if len(sources) >= SEUIL_REPRISE
        for identifiant in ids_par_titre[cle]
    }


def r07_doublon(items: list[dict]) -> set[str]:
    """Même titre, à la casse et à la ponctuation près, dans une même source.

    Le premier item est gardé, les suivants sont écartés."""
    vus = set()
    ecartes = set()
    for item in items:
        cle = (item["source"], cle_titre(item.get("titre", "")))
        if not cle[1]:
            continue
        if cle in vus:
            ecartes.add(item["id"])
        else:
            vus.add(cle)
    return ecartes
