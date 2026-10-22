"""Table `sources` (PostgreSQL) : l'état de chaque flux suivi par la collecte."""

import csv
import os

import psycopg2
import psycopg2.extras

SEUIL_SOMMEIL = 3


def connexion(url: str | None = None):
    return psycopg2.connect(url or os.environ["GAZETTE_DB_URL"])


def lire_csv(chemin: str) -> list[dict]:
    """Lit docs/sources.csv. Une ligne avec plusieurs flux (« url + url »)
    donne une source par flux."""
    sources = []
    with open(chemin, encoding="utf-8") as fichier:
        for ligne in csv.DictReader(fichier):
            urls = [
                morceau.strip()
                for morceau in ligne["acces"].removeprefix("RSS - ").split("+")
            ]
            for numero, url in enumerate(urls, start=1):
                nom = ligne["nom"] if len(urls) == 1 else f"{ligne['nom']} ({numero})"
                sources.append({"nom": nom, "type": ligne["type"], "url_flux": url})
    return sources


def synchroniser(conn, sources: list[dict]) -> None:
    """Ajoute les nouvelles sources et met à jour type et URL des existantes,
    sans toucher à leur état (actif, échecs, ETag...)."""
    with conn, conn.cursor() as cur:
        psycopg2.extras.execute_batch(
            cur,
            """
            INSERT INTO sources (nom, type, url_flux)
            VALUES (%(nom)s, %(type)s, %(url_flux)s)
            ON CONFLICT (nom) DO UPDATE
            SET type = EXCLUDED.type, url_flux = EXCLUDED.url_flux
            """,
            sources,
        )


def sources_actives(conn) -> list[dict]:
    with conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT * FROM sources WHERE actif ORDER BY nom")
        return [dict(ligne) for ligne in cur.fetchall()]


def enregistrer_reussite(
    conn, nom: str, etag: str | None, last_modified: str | None
) -> None:
    """Remet le compteur d'échecs à zéro. Sur un 304, etag et last_modified
    valent None : on garde alors les valeurs déjà connues."""
    with conn, conn.cursor() as cur:
        cur.execute(
            """
            UPDATE sources
            SET derniere_reussite = now(),
                echecs_consecutifs = 0,
                etag = COALESCE(%s, etag),
                last_modified = COALESCE(%s, last_modified)
            WHERE nom = %s
            """,
            (etag, last_modified, nom),
        )


def enregistrer_echec(conn, nom: str, seuil: int = SEUIL_SOMMEIL) -> bool:
    """Incrémente le compteur d'échecs et met la source en sommeil au seuil.
    Renvoie True si la source vient d'être mise en sommeil."""
    with conn, conn.cursor() as cur:
        cur.execute(
            """
            UPDATE sources
            SET echecs_consecutifs = echecs_consecutifs + 1,
                actif = echecs_consecutifs + 1 < %s
            WHERE nom = %s
            RETURNING actif
            """,
            (seuil, nom),
        )
        (actif,) = cur.fetchone()
        return not actif
