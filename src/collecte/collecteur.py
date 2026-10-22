"""Collecteur multi-sources : un passage sur toutes les sources actives.

- une source après l'autre (pas de parallélisme sur les éditeurs) ;
- en-têtes conditionnels (ETag / Last-Modified) pour ne pas retélécharger ;
- erreur transitoire (5xx, 429, délai dépassé) : nouvel essai avec attente
  croissante ; erreur permanente (403, 404, flux illisible) : échec direct ;
- chaque échec incrémente echecs_consecutifs, à 3 la source est mise en sommeil ;
- une ligne de journal JSON par source, des compteurs pour tout le passage.

Usage : python -m src.collecte.collecteur
"""

import json
import logging
import os
import time
from datetime import datetime, timezone

import requests

from src.collecte.rss import parser
from src.stockage import sources as table_sources
from src.stockage.bronze import Bronze

USER_AGENT = "LaGazette/0.1 (projet etudiant M2 Efrei; collecte RSS)"
TIMEOUT_SECONDES = 15
TENTATIVES = 3
ATTENTE_SECONDES = 5  # puis 10, 20... (backoff exponentiel)
STATUTS_TRANSITOIRES = {429, 500, 502, 503, 504}

journal = logging.getLogger("collecte")


class EchecCollecte(Exception):
    def __init__(self, message: str, http: int | None = None):
        super().__init__(message)
        self.http = http


def telecharger(
    source: dict, tentatives: int = TENTATIVES, attente: float = ATTENTE_SECONDES
) -> requests.Response:
    """GET conditionnel avec nouveaux essais sur erreur transitoire.
    Renvoie la réponse (200 ou 304), lève EchecCollecte sinon."""
    entetes = {"User-Agent": USER_AGENT}
    if source.get("etag"):
        entetes["If-None-Match"] = source["etag"]
    if source.get("last_modified"):
        entetes["If-Modified-Since"] = source["last_modified"]

    for essai in range(1, tentatives + 1):
        try:
            reponse = requests.get(
                source["url_flux"], headers=entetes, timeout=TIMEOUT_SECONDES
            )
        except (requests.Timeout, requests.ConnectionError) as erreur:
            echec = EchecCollecte(f"réseau : {type(erreur).__name__}")
        else:
            if reponse.status_code in (200, 304):
                return reponse
            echec = EchecCollecte(f"HTTP {reponse.status_code}", reponse.status_code)
            if reponse.status_code not in STATUTS_TRANSITOIRES:
                raise echec  # permanent : inutile d'insister
        if essai < tentatives:
            time.sleep(attente * 2 ** (essai - 1))
    raise echec


def collecter_source(source: dict, bronze: Bronze, conn, **options) -> dict:
    """Collecte une source et met à jour son état. Renvoie la ligne de journal."""
    debut = time.monotonic()
    ligne = {"source": source["nom"], "recus": 0, "ecrits": 0, "ignores": 0}
    try:
        reponse = telecharger(source, **options)
        ligne["http"] = reponse.status_code
        if reponse.status_code == 304:
            ligne["statut"] = "inchange"
        else:
            items = parser(reponse.content, source["nom"])
            ligne["recus"] = len(items)
            for item in items:
                if bronze.ecrire_si_absent(item):
                    ligne["ecrits"] += 1
                else:
                    ligne["ignores"] += 1
            ligne["statut"] = "ok"
        table_sources.enregistrer_reussite(
            conn,
            source["nom"],
            reponse.headers.get("ETag"),
            reponse.headers.get("Last-Modified"),
        )
    except Exception as erreur:  # une source en erreur ne bloque pas les autres
        ligne["http"] = getattr(erreur, "http", None)
        ligne["erreur"] = str(erreur)
        endormie = table_sources.enregistrer_echec(conn, source["nom"])
        ligne["statut"] = "mise_en_sommeil" if endormie else "echec"
    ligne["duree_s"] = round(time.monotonic() - debut, 2)

    niveau = logging.INFO if ligne["statut"] in ("ok", "inchange") else logging.WARNING
    journal.log(niveau, json.dumps(ligne, ensure_ascii=False))
    return ligne


def collecter_tout(
    conn, bronze: Bronze, sources_csv: str | None = None, **options
) -> dict:
    """Un passage complet. Renvoie les compteurs du passage."""
    debut = datetime.now(timezone.utc).isoformat()
    if sources_csv:
        table_sources.synchroniser(conn, table_sources.lire_csv(sources_csv))

    lignes = [
        collecter_source(source, bronze, conn, **options)
        for source in table_sources.sources_actives(conn)
    ]
    compteurs = {
        "debut": debut,
        "sources": len(lignes),
        "ok": sum(ligne["statut"] == "ok" for ligne in lignes),
        "inchanges": sum(ligne["statut"] == "inchange" for ligne in lignes),
        "echecs": sum(ligne["statut"] == "echec" for ligne in lignes),
        "mises_en_sommeil": [
            ligne["source"] for ligne in lignes if ligne["statut"] == "mise_en_sommeil"
        ],
        "recus": sum(ligne["recus"] for ligne in lignes),
        "ecrits": sum(ligne["ecrits"] for ligne in lignes),
        "ignores": sum(ligne["ignores"] for ligne in lignes),
    }
    journal.info(json.dumps({"passage": compteurs}, ensure_ascii=False))
    return compteurs


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    conn = table_sources.connexion()
    try:
        collecter_tout(conn, Bronze(), os.environ.get("SOURCES_CSV"))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
