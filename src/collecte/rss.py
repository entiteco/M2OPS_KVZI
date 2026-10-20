"""Collecte d'un flux RSS : lecture, parsing, écriture des items en JSON.
"""

import argparse
import html
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import feedparser
import requests

USER_AGENT = "LaGazette/0.1 (projet etudiant M2 Efrei; collecte RSS)"
TIMEOUT_SECONDES = 10
DOSSIER_SORTIE = os.environ.get("COLLECTE_OUTPUT_DIR", "data/collecte")

_BALISES_HTML = re.compile(r"<[^>]+>")


def telecharger(url: str) -> bytes:
    """Récupère le contenu brut du flux ; lève une exception si HTTP != 2xx."""
    reponse = requests.get(
        url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT_SECONDES
    )
    reponse.raise_for_status()
    return reponse.content


def _nettoyer_texte(texte: str) -> str:
    sans_balises = _BALISES_HTML.sub("", texte)
    return " ".join(html.unescape(sans_balises).split())


def _date_iso(entree) -> str | None:
    date = entree.get("published_parsed") or entree.get("updated_parsed")
    if date is None:
        return None
    # feedparser normalise les dates en UTC
    return datetime(*date[:6], tzinfo=timezone.utc).isoformat()


def parser(contenu: bytes, source: str) -> list[dict]:
    """Transforme un flux RSS/Atom en liste d'items."""
    flux = feedparser.parse(contenu)
    items = []
    for entree in flux.entries:
        lien = entree.get("link")
        titre = entree.get("title")
        if not lien or not titre:
            continue
        items.append(
            {
                "source": source,
                "guid": entree.get("id") or lien,
                "titre": _nettoyer_texte(titre),
                "extrait": _nettoyer_texte(entree.get("summary", "")),
                "lien": lien,
                "date_publication": _date_iso(entree),
            }
        )
    return items


def ecrire_json(
    items: list[dict], source: str, url: str, dossier: str | Path = DOSSIER_SORTIE
) -> Path:
    """Écrit les items dans <dossier>/<source>_<horodatage UTC>.json."""
    maintenant = datetime.now(timezone.utc)
    dossier = Path(dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    chemin = dossier / f"{source}_{maintenant:%Y%m%dT%H%M%SZ}.json"
    document = {
        "source": source,
        "url": url,
        "collecte_le": maintenant.isoformat(),
        "nb_items": len(items),
        "items": items,
    }
    chemin.write_text(
        json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return chemin


def collecter(source: str, url: str, dossier: str | Path = DOSSIER_SORTIE) -> Path:
    """Lit une source de bout en bout et renvoie le chemin du JSON produit."""
    items = parser(telecharger(url), source)
    return ecrire_json(items, source, url, dossier)


def main() -> None:
    arguments = argparse.ArgumentParser(description="Collecte d'un flux RSS")
    arguments.add_argument("--source", default="humanite")
    arguments.add_argument("--url", default="https://www.humanite.fr/feed")
    arguments.add_argument("--dossier", default=DOSSIER_SORTIE)
    args = arguments.parse_args()
    chemin = collecter(args.source, args.url, args.dossier)
    print(f"Items écrits dans {chemin}")


if __name__ == "__main__":
    main()
