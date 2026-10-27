"""Import d'une archive Bronze et régénération Silver avec les règles du projet.

Sans --minio, produit des exports locaux dans data/restauration, sans services.
Avec --minio, importe les objets absents puis exécute le passage en PostgreSQL.
Ajouter --bronze-seul pour conserver la Silver déjà restaurée depuis SQL.
"""

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

from src.normalisation.passage import rapport, traiter
from src.stockage.bronze import cle


def lire_archive(chemin: Path) -> list[dict]:
    articles = {}
    with ZipFile(chemin) as archive:
        for entree in archive.infolist():
            # Les ZIP exportés sous Windows utilisent parfois des antislashs.
            nom = PurePosixPath(entree.filename.replace("\\", "/"))
            if nom.suffix != ".json":
                continue
            if nom.parts[:2] != ("bronze", "articles_bruts") or len(nom.parts) != 4:
                raise ValueError(f"Chemin Bronze inattendu : {entree.filename}")
            item = json.loads(archive.read(entree))
            attendue = PurePosixPath("bronze") / cle(item["source"], item["lien"])
            if nom != attendue or nom.stem != item["id"]:
                raise ValueError(f"Identifiant ou chemin incohérent : {entree.filename}")
            if item["id"] in articles:
                raise ValueError(f"Identifiant en double : {item['id']}")
            articles[item["id"]] = item
    if not articles:
        raise ValueError("L'archive ne contient aucun article Bronze")
    return list(articles.values())


def exporter(items: list[dict], sortie: Path) -> dict:
    maintenant = datetime.now(timezone.utc)
    passage = maintenant.strftime("%Y%m%dT%H%M%SZ")
    gardes, rejets = traiter(items, passage)
    sortie.mkdir(parents=True, exist_ok=True)
    for nom, lignes in (("articles_propres", gardes), ("rejets", rejets)):
        with (sortie / f"{nom}.jsonl").open("w", encoding="utf-8") as fichier:
            for ligne in lignes:
                fichier.write(json.dumps(ligne, ensure_ascii=False) + "\n")
    (sortie / "qualite.md").write_text(
        rapport(len(items), gardes, rejets, maintenant.date().isoformat()),
        encoding="utf-8",
    )
    bilan = {
        "passage": passage,
        "entres": len(items),
        "gardes": len(gardes),
        "rejetes": len(rejets),
        "sources": dict(Counter(i["source"] for i in items)),
    }
    (sortie / "bilan.json").write_text(
        json.dumps(bilan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return bilan


def restaurer_services(items: list[dict], bronze_seul: bool = False) -> dict:
    from src.normalisation.passage import executer
    from src.stockage.bronze import Bronze
    from src.stockage.sources import connexion

    bronze = Bronze()
    ajoutes = sum(bronze.ecrire_si_absent(item) for item in items)
    import_bronze = {
        "bronze_ajoutes": ajoutes, "bronze_deja_presents": len(items) - ajoutes,
    }
    if bronze_seul:
        return import_bronze
    conn = connexion()
    try:
        bilan = executer(bronze.client, conn)
    finally:
        conn.close()
    return {**bilan, **import_bronze}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=Path("bronze-json.zip"))
    parser.add_argument("--sortie", type=Path, default=Path("data/restauration"))
    parser.add_argument("--minio", action="store_true", help="Restaurer MinIO et PostgreSQL")
    parser.add_argument(
        "--bronze-seul", action="store_true",
        help="Avec --minio, importer Bronze sans modifier la Silver restaurée",
    )
    args = parser.parse_args()
    if args.bronze_seul and not args.minio:
        parser.error("--bronze-seul nécessite --minio")
    items = lire_archive(args.archive)
    bilan = (
        restaurer_services(items, args.bronze_seul)
        if args.minio else exporter(items, args.sortie)
    )
    print(json.dumps(bilan, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
