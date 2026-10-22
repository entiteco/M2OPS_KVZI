"""Lecture d'un flux RSS / Atom : transforme les entrées en items bruts.

feedparser gère les variantes RSS 2.0 / Atom (pubDate / updated,
description / summary, guid / id), les formats de date et les encodages.
"""

import html
import re
from datetime import datetime, timezone

import feedparser

from src.stockage.bronze import identifiant

_BALISES_HTML = re.compile(r"<[^>]+>")

# Retirés du payload : texte intégral, images, commentaires, auteurs.
_CHAMPS_EXCLUS = {
    "content",
    "author",
    "authors",
    "author_detail",
    "comments",
    "wfw_commentrss",
    "slash_comments",
}


def _nettoyer_texte(texte: str) -> str:
    sans_balises = _BALISES_HTML.sub("", texte)
    return " ".join(html.unescape(sans_balises).split())


def _date_iso(entree) -> str | None:
    date = entree.get("published_parsed") or entree.get("updated_parsed")
    if date is None:
        return None
    # feedparser normalise les dates en UTC
    return datetime(*date[:6], tzinfo=timezone.utc).isoformat()


def _payload(entree) -> dict:
    payload = {
        cle: valeur
        for cle, valeur in entree.items()
        if cle not in _CHAMPS_EXCLUS
        and not cle.startswith("media_")
        and not cle.endswith("_parsed")  # doublons non sérialisables des dates
    }
    if "links" in payload:
        # les « enclosures » sont les images jointes
        payload["links"] = [
            lien for lien in payload["links"] if lien.get("rel") != "enclosure"
        ]
    return payload


def parser(contenu: bytes, source: str, recupere_le: str | None = None) -> list[dict]:
    """Transforme un flux RSS/Atom en liste d'items au format articles_bruts.

    Lève ValueError si le contenu n'est pas un flux lisible."""
    flux = feedparser.parse(contenu)
    if flux.bozo and not flux.entries:
        raise ValueError(f"flux illisible : {flux.get('bozo_exception')}")
    recupere_le = recupere_le or datetime.now(timezone.utc).isoformat()
    items = []
    for entree in flux.entries:
        lien = entree.get("link")
        titre = entree.get("title")
        if not lien or not titre:
            continue
        tags = entree.get("tags") or []
        items.append(
            {
                "id": identifiant(source, lien),
                "source": source,
                "lien": lien,
                "titre": _nettoyer_texte(titre),
                "resume": _nettoyer_texte(entree.get("summary", "")),
                "publie_le": _date_iso(entree),
                "recupere_le": recupere_le,
                "rubrique": tags[0].get("term") if tags else None,
                "payload": _payload(entree),
            }
        )
    return items
