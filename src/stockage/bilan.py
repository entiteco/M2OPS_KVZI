"""Bilan de la collecte : articles par source dans articles_bruts/ et état
de chaque source (actif / en sommeil, dernière réussite, échecs).

Usage : python -m src.stockage.bilan
"""

from collections import Counter

from src.stockage import sources as table_sources
from src.stockage.bronze import PREFIXE, Bronze, slug


def articles_par_dossier(bronze: Bronze) -> Counter:
    objets = bronze.client.list_objects(
        bronze.bucket, prefix=f"{PREFIXE}/", recursive=True
    )
    return Counter(objet.object_name.split("/")[1] for objet in objets)


def main() -> None:
    compte = articles_par_dossier(Bronze())
    conn = table_sources.connexion()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                "SELECT nom, actif, echecs_consecutifs, derniere_reussite"
                " FROM sources ORDER BY nom"
            )
            lignes = cur.fetchall()
    finally:
        conn.close()

    print(f"{'source':30} {'articles':>8}  {'état':10} {'échecs':>6}  dernière réussite")
    for nom, actif, echecs, derniere in lignes:
        etat = "actif" if actif else "EN SOMMEIL"
        quand = f"{derniere:%d/%m %H:%M} UTC" if derniere else "jamais"
        print(f"{nom:30} {compte[slug(nom)]:>8}  {etat:10} {echecs:>6}  {quand}")
    print(f"{'TOTAL':30} {sum(compte.values()):>8}")


if __name__ == "__main__":
    main()
