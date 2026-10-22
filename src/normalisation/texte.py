"""Transformations de texte. Chaque fonction est pure : une entrée, une sortie."""

import re
import unicodedata

MARQUEURS_MOJIBAKE = ("Ã", "Â", "â€")


def reparer_mojibake(texte: str) -> str:
    """Répare « Ã© » en « é » quand du UTF-8 a été décodé en latin-1."""
    if not any(marqueur in texte for marqueur in MARQUEURS_MOJIBAKE):
        return texte
    try:
        return texte.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return texte


def normaliser_espaces(texte: str) -> str:
    return " ".join(texte.split())


def extrait_borne(texte: str, longueur: int = 300) -> str:
    """Coupe l'extrait sur un mot, sans dépasser la longueur donnée."""
    if len(texte) <= longueur:
        return texte
    return texte[:longueur].rsplit(" ", 1)[0] + "…"


def cle_titre(titre: str) -> str:
    """Forme comparable d'un titre : sans accents, casse ni ponctuation."""
    sans_accents = (
        unicodedata.normalize("NFKD", titre).encode("ascii", "ignore").decode()
    )
    return " ".join(re.sub(r"[^a-z0-9]+", " ", sans_accents.lower()).split())
