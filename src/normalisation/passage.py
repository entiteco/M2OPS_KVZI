"""Passage de nettoyage : zone Bronze -> zone Silver (TD 4).

Ordre : normalisation, règles à un item, règles de lot (R03 puis R07).
Sortie : bucket `silver` (articles_propres/<id>.json, rejets/<passage>.json),
rapport dans le bucket `rapports` (qualite-<date>.md).
"""

import io
import json
from collections import Counter
from datetime import datetime, timezone

from src.normalisation import regles
from src.normalisation.texte import (
    extrait_borne,
    normaliser_espaces,
    reparer_mojibake,
    retirer_balises,
)

BUCKET_BRONZE = "bronze"
BUCKET_SILVER = "silver"
BUCKET_RAPPORTS = "rapports"
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


def lire_bronze(client, bucket=BUCKET_BRONZE):
    for objet in client.list_objects(bucket, prefix="articles_bruts/", recursive=True):
        reponse = client.get_object(bucket, objet.object_name)
        try:
            yield json.loads(reponse.read())
        finally:
            reponse.close()
            reponse.release_conn()


def _ecrire(client, bucket: str, cle: str, contenu: bytes, type_contenu: str):
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)
    client.put_object(
        bucket, cle, io.BytesIO(contenu), length=len(contenu), content_type=type_contenu
    )


def executer(client, passage: str | None = None) -> dict:
    """Un passage complet : lit Bronze, écrit Silver, rejets et rapport."""
    maintenant = datetime.now(timezone.utc)
    passage = passage or maintenant.strftime("%Y%m%dT%H%M%SZ")
    bruts = list(lire_bronze(client))
    gardes, rejets = traiter(bruts, passage)
    for item in gardes:
        _ecrire(
            client,
            BUCKET_SILVER,
            f"articles_propres/{item['id']}.json",
            json.dumps(item, ensure_ascii=False, indent=2).encode("utf-8"),
            "application/json",
        )
    _ecrire(
        client,
        BUCKET_SILVER,
        f"rejets/{passage}.json",
        json.dumps(rejets, ensure_ascii=False, indent=2).encode("utf-8"),
        "application/json",
    )
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
