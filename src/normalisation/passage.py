"""Passage de nettoyage : zone Bronze -> zone Silver (TD 4).

Ordre : normalisation, règles à un item, règles de lot (R03 puis R07).
Sortie : table PostgreSQL `articles_propres` (gardés uniquement), table
`metriques_passage` (historique par passage et par source), et le rapport
du jour dans le bucket MinIO `rapports`. Les rejets ne sont pas stockés en
Silver : ils se lisent dans le rapport et dans les métriques.
"""

import io
import json
from collections import Counter
from datetime import datetime, timezone

import psycopg2.extras

from src.normalisation import regles
from src.normalisation.texte import (
    extrait_borne,
    normaliser_espaces,
    reparer_mojibake,
    retirer_balises,
)

BUCKET_BRONZE = "bronze"
BUCKET_RAPPORTS = "rapports"
COLONNES_ARTICLE = (
    "id", "source", "lien", "titre", "extrait",
    "publie_le", "recupere_le", "rubrique", "passage",
)
# Au-delà de ce taux de rejet, une source déclenche une alerte (docs/qualite.md).
SEUIL_ALERTE_REJET = 0.80


def normaliser(item: dict) -> dict:
    titre = normaliser_espaces(reparer_mojibake(item.get("titre", "")))
    resume = normaliser_espaces(retirer_balises(reparer_mojibake(item.get("resume", ""))))
    propre = {k: v for k, v in item.items() if k not in ("resume", "payload")}
    propre["titre"] = titre
    propre["extrait"] = extrait_borne(resume)
    return propre


def regle_item(item: dict) -> str | None:
    """Première règle à un item qui l'écarte, dans l'ordre documenté."""
    controles = [
        ("R04_titre_vide", regles.r04_titre_vide),
        ("R05_date_future", regles.r05_date_future),
        ("R06_encodage", regles.r06_encodage),
        ("R01_publi", regles.r01_publi),
        ("R02_rubrique_hors_sujet", regles.r02_rubrique_hors_sujet),
    ]
    for nom, controle in controles:
        if controle(item):
            return nom
    return None


def appliquer_lot(items, nom, fonction):
    ecartes = fonction(items)
    gardes = [i for i in items if i["id"] not in ecartes]
    rejets = [
        {"id": i["id"], "source": i["source"], "regle": nom}
        for i in items
        if i["id"] in ecartes
    ]
    return gardes, rejets


def traiter(items_bruts: list[dict], passage: str) -> tuple[list[dict], list[dict]]:
    """Renvoie (articles gardés, rejets). Fonction pure : aucune écriture."""
    items = [normaliser(i) for i in items_bruts]
    gardes, rejets = [], []
    for item in items:
        regle = regle_item(item)
        if regle:
            rejets.append({"id": item["id"], "source": item["source"], "regle": regle})
        else:
            gardes.append(item)
    gardes, rej = appliquer_lot(gardes, "R03_depeche_reprise", regles.r03_depeche_reprise)
    rejets += rej
    gardes, rej = appliquer_lot(gardes, "R07_doublon", regles.r07_doublon)
    rejets += rej
    for item in gardes:
        item["passage"] = passage
    for rejet in rejets:
        rejet["passage"] = passage
    return gardes, rejets


def _ecrire(client, bucket: str, cle: str, contenu: bytes, type_contenu: str):
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)
    client.put_object(
        bucket, cle, io.BytesIO(contenu), length=len(contenu), content_type=type_contenu
    )


def ecrire_articles(conn, gardes: list[dict]) -> None:
    """Upsert dans articles_propres : relancer un passage ne crée pas de doublon."""
    lignes = [{c: g.get(c) for c in COLONNES_ARTICLE} for g in gardes]
    with conn, conn.cursor() as cur:
        psycopg2.extras.execute_batch(
            cur,
            """
            INSERT INTO articles_propres
                (id, source, lien, titre, extrait, publie_le, recupere_le, rubrique, passage)
            VALUES
                (%(id)s, %(source)s, %(lien)s, %(titre)s, %(extrait)s,
                 %(publie_le)s, %(recupere_le)s, %(rubrique)s, %(passage)s)
            ON CONFLICT (id) DO UPDATE
            SET titre = EXCLUDED.titre,
                extrait = EXCLUDED.extrait,
                passage = EXCLUDED.passage
            """,
            lignes,
        )


def metriques_par_source(
    entres: list[dict], gardes: list[dict], rejets: list[dict], passage: str
) -> list[dict]:
    """Une ligne par source : entrés, gardés, rejetés et taux de rejet du passage."""
    total = Counter(i["source"] for i in entres)
    gardes_par_source = Counter(g["source"] for g in gardes)
    rejets_par_source = Counter(r["source"] for r in rejets)
    return [
        {
            "passage": passage,
            "source": source,
            "entres": n,
            "gardes": gardes_par_source[source],
            "rejetes": rejets_par_source[source],
            "taux_rejet": rejets_par_source[source] / n,
        }
        for source, n in sorted(total.items())
        if n
    ]


def ecrire_metriques(conn, lignes: list[dict]) -> None:
    """Upsert dans metriques_passage, clé (passage, source)."""
    with conn, conn.cursor() as cur:
        psycopg2.extras.execute_batch(
            cur,
            """
            INSERT INTO metriques_passage
                (passage, source, entres, gardes, rejetes, taux_rejet)
            VALUES
                (%(passage)s, %(source)s, %(entres)s, %(gardes)s, %(rejetes)s, %(taux_rejet)s)
            ON CONFLICT (passage, source) DO UPDATE
            SET entres = EXCLUDED.entres,
                gardes = EXCLUDED.gardes,
                rejetes = EXCLUDED.rejetes,
                taux_rejet = EXCLUDED.taux_rejet,
                mesure_le = now()
            """,
            lignes,
        )


def lire_bronze(client, bucket=BUCKET_BRONZE):
    for objet in client.list_objects(bucket, prefix="articles_bruts/", recursive=True):
        reponse = client.get_object(bucket, objet.object_name)
        try:
            yield json.loads(reponse.read())
        finally:
            reponse.close()
            reponse.release_conn()


def executer(client, conn, passage: str | None = None) -> dict:
    """Un passage complet : lit Bronze, écrit articles_propres et metriques_passage,
    puis le rapport du jour dans MinIO."""
    maintenant = datetime.now(timezone.utc)
    passage = passage or maintenant.strftime("%Y%m%dT%H%M%SZ")
    bruts = list(lire_bronze(client))
    gardes, rejets = traiter(bruts, passage)
    ecrire_articles(conn, gardes)
    lignes = metriques_par_source(bruts, gardes, rejets, passage)
    ecrire_metriques(conn, lignes)
    texte = rapport(len(bruts), gardes, rejets, maintenant.date().isoformat())
    _ecrire(
        client,
        BUCKET_RAPPORTS,
        f"qualite-{maintenant.date().isoformat()}.md",
        texte.encode("utf-8"),
        "text/markdown",
    )
    taux = taux_rejet_par_source(bruts, rejets)
    return {
        "passage": passage,
        "entres": len(bruts),
        "gardes": len(gardes),
        "rejetes": len(rejets),
        "taux_rejet": {s: round(t, 3) for s, t in taux.items()},
        "alertes": sources_en_alerte(taux),
    }


def taux_rejet_par_source(entres: list[dict], rejets: list[dict]) -> dict[str, float]:
    total = Counter(i["source"] for i in entres)
    rejetes = Counter(r["source"] for r in rejets)
    return {source: rejetes[source] / n for source, n in total.items() if n}


def sources_en_alerte(taux: dict[str, float]) -> list[str]:
    return sorted(s for s, t in taux.items() if t > SEUIL_ALERTE_REJET)


def rapport(entres: int, gardes: list, rejets: list, date: str) -> str:
    par_regle = Counter(r["regle"] for r in rejets)
    par_source = Counter((r["source"], r["regle"]) for r in rejets)
    lignes = [
        f"# Rapport qualité — {date}",
        "",
        f"- Entrés : {entres}",
        f"- Gardés (articles_propres) : {len(gardes)}",
        f"- Rejetés : {len(rejets)}",
        "",
        "## Rejets par règle",
        "",
        "| Règle | Rejets |",
        "|---|---|",
    ]
    lignes += [f"| {regle} | {n} |" for regle, n in par_regle.most_common()]
    lignes += ["", "## Rejets par source", "", "| Source | Règle | Rejets |", "|---|---|---|"]
    lignes += [
        f"| {source} | {regle} | {n} |" for (source, regle), n in sorted(par_source.items())
    ]
    lignes += ["", "## Top 5 des rejets", ""]
    lignes += [f"{i}. {regle} ({n})" for i, (regle, n) in enumerate(par_regle.most_common(5), 1)]
    lignes.append("")
    return "\n".join(lignes)
