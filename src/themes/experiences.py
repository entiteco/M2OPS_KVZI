"""Comparer des paramètres BERTopic sur l'instantané immuable d'un run.

Les expériences sont archivées dans MinIO et ne publient pas de thèmes courants.
"""

import argparse
import copy
import hashlib
import io
import json
import time
import uuid
from datetime import datetime, timezone

import numpy as np

from src.themes.configuration import empreinte, json_canonique
from src.themes.passage import ecrire_artefact, sources_code, versions
from src.themes.embeddings import vectoriser
from src.themes.regroupement import mesurer, nommer, regrouper


def variantes(config):
    # Une variante doit décrire ses propres réglages, indépendamment du run source.
    config = copy.deepcopy(config)
    config.pop("themes_cible", None)
    config.update(reduction="umap", poids_lexical=0., reaffectation_seuil=None)
    for nom, voisins, dimensions, taille, echantillons, lexical, seuil, ctfidf in [
        ("macro_15", 15, 5, 15, 3, 0., .45, False),
        ("macro_30", 30, 5, 20, 3, 0., .45, False),
        ("macro_30_10d", 30, 10, 25, 5, 0., .45, False),
        ("macro_45", 45, 5, 30, 5, 0., .45, False),
        ("macro_ctfidf", 30, 5, 15, 3, 0., .45, True),
        ("macro_lexical", 30, 5, 15, 3, .1, .45, False),
    ]:
        candidat = copy.deepcopy(config)
        candidat.update(reduction="umap", poids_lexical=lexical, reaffectation_seuil=seuil,
                         themes_cible=10, reduction_themes_ctfidf=ctfidf)
        candidat["umap"].update(n_neighbors=voisins, n_components=dimensions)
        candidat["hdbscan"].update(min_cluster_size=taille, min_samples=echantillons,
                                  cluster_selection_method="eom")
        yield nom, candidat
    for voisins, taille in ((15, 5), (30, 5), (30, 8)):
        candidat = copy.deepcopy(config)
        candidat.update(reduction="umap", poids_lexical=0., reaffectation_seuil=.45,
                         themes_cible=10, reduction_themes_ctfidf=False)
        candidat["umap"].update(n_neighbors=voisins, n_components=5)
        candidat["hdbscan"].update(min_cluster_size=taille, min_samples=3,
                                  cluster_selection_method="leaf")
        yield f"macro_leaf_{voisins}_{taille}", candidat
    grille = [
        ("reference", 15, 5, 5, 3, "eom"),
        ("local_5", 5, 5, 5, 3, "eom"),
        ("dimensions_10", 10, 10, 5, 3, "eom"),
        ("dimensions_15", 10, 15, 5, 3, "eom"),
        ("fin_5", 5, 15, 4, 2, "leaf"),
        ("fin_10", 10, 15, 4, 2, "leaf"),
        ("leaf_5", 10, 15, 5, 3, "leaf"),
        ("leaf_3", 10, 15, 3, 2, "leaf"),
        ("leaf_15", 15, 15, 5, 3, "leaf"),
        ("eom_4", 10, 15, 4, 2, "eom"),
        ("dimensions_30", 15, 30, 4, 2, "leaf"),
    ]
    for nom, voisins, dimensions, taille, echantillons, methode in grille:
        candidat = copy.deepcopy(config)
        candidat["umap"].update(n_neighbors=voisins, n_components=dimensions)
        candidat["hdbscan"].update(
            min_cluster_size=taille, min_samples=echantillons, cluster_selection_method=methode,
        )
        candidat["representation"]["language"] = "multilingual"
        yield nom, candidat
    for taille, echantillons in ((3, 1), (4, 2), (5, 3)):
        candidat = copy.deepcopy(config)
        candidat["reduction"] = "original"
        candidat["representation"]["language"] = "multilingual"
        candidat["hdbscan"].update(min_cluster_size=taille, min_samples=echantillons)
        yield f"original_{taille}", candidat
    for voisins, taille, methode in ((5, 4, "eom"), (10, 4, "eom"), (10, 4, "leaf"), (5, 5, "eom")):
        candidat = copy.deepcopy(config)
        candidat["embedding"]["champs"] = "titre"
        candidat["representation"]["language"] = "multilingual"
        candidat["umap"].update(n_neighbors=voisins, n_components=15)
        candidat["hdbscan"].update(min_cluster_size=taille, min_samples=2, cluster_selection_method=methode)
        yield f"titres_{voisins}_{taille}_{methode}", candidat
    for poids, voisins, methode in (
        (.3, 5, "eom"), (.5, 5, "eom"), (.7, 5, "eom"),
        (.3, 10, "eom"), (.5, 10, "eom"), (.5, 10, "leaf"),
    ):
        candidat = copy.deepcopy(config)
        candidat["poids_lexical"] = poids
        candidat["representation"]["language"] = "multilingual"
        candidat["umap"].update(n_neighbors=voisins, n_components=15)
        candidat["hdbscan"].update(min_cluster_size=4, min_samples=2, cluster_selection_method=methode)
        yield f"lexical_{poids}_{voisins}_{methode}", candidat
    for taille, poids, methode in ((2, 0., "eom"), (2, 0., "leaf"), (3, 0., "leaf"),
                                   (2, .2, "eom"), (3, .2, "eom"), (2, .4, "eom"), (3, .4, "eom")):
        candidat = copy.deepcopy(config)
        candidat["reduction"] = "original"
        candidat["poids_lexical"] = poids
        candidat["representation"]["language"] = "multilingual"
        candidat["hdbscan"].update(min_cluster_size=taille, min_samples=1, cluster_selection_method=methode)
        yield f"direct_{taille}_{poids}_{methode}", candidat
    for seuil in (.5, .55, .6, .65, .7, .75, .8):
        candidat = copy.deepcopy(config)
        candidat["reduction"] = "original"
        candidat["poids_lexical"] = .2
        candidat["reaffectation_seuil"] = seuil
        candidat["representation"]["language"] = "multilingual"
        candidat["hdbscan"].update(min_cluster_size=3, min_samples=1)
        yield f"reaffectation_{seuil}", candidat


def lire_objet(client, objet):
    reponse = client.get_object(objet["bucket"], objet["cle"])
    try:
        contenu = reponse.read()
    finally:
        reponse.close()
        reponse.release_conn()
    if hashlib.sha256(contenu).hexdigest() != objet["sha256"]:
        raise ValueError("L'artefact d'entrée ne correspond pas à son empreinte")
    return contenu


def comparer(conn, client, source_run, filtre=""):
    with conn, conn.cursor() as cur:
        cur.execute("SELECT config, artefacts, hash_entree FROM runs WHERE id = %s AND statut = 'succes'",
                    (source_run,))
        ligne = cur.fetchone()
    if ligne is None:
        raise ValueError("Run source réussi introuvable")
    config, artefacts, hash_entree = ligne
    articles = json.loads(lire_objet(client, artefacts["entree.json"]))
    if empreinte(articles) != hash_entree:
        raise ValueError("L'instantané des articles a changé")
    contenu_vecteurs = lire_objet(client, artefacts["embeddings.npy"])
    vecteurs = np.load(io.BytesIO(contenu_vecteurs), allow_pickle=False)
    identifiant = "comparaison-" + uuid.uuid4().hex
    bucket = config["artefacts_bucket"]
    prefixe = "experiences/" + identifiant
    manifeste = {}

    def archiver(nom, valeur):
        ecrire_artefact(client, bucket, prefixe, nom, json_canonique(valeur).encode(), manifeste)

    rapport = {
        "id": identifiant, "source_run": source_run, "hash_entree": hash_entree,
        "nb_articles": len(articles), "commence_le": datetime.now(timezone.utc).isoformat(),
        "versions": versions(), "code_hash": empreinte(sources_code()), "resultats": [],
    }
    archiver("entree.json", articles)
    archiver("code.json", sources_code())
    ecrire_artefact(client, bucket, prefixe, "embeddings.npy", contenu_vecteurs,
                   manifeste, "application/octet-stream")
    for nom, candidat in variantes(config):
        if filtre and not nom.startswith(filtre):
            continue
        debut = time.monotonic()
        archiver(nom + "/config.json", candidat)
        try:
            vecteurs_candidat = vecteurs
            if candidat["embedding"].get("champs") == "titre":
                vecteurs_candidat, _ = vectoriser(conn, articles, candidat["embedding"])
                tampon = io.BytesIO()
                np.save(tampon, vecteurs_candidat, allow_pickle=False)
                ecrire_artefact(client, bucket, prefixe, nom + "/embeddings.npy",
                               tampon.getvalue(), manifeste, "application/octet-stream")
            labels, mots, _, effectifs = regrouper(articles, vecteurs_candidat, candidat)
            themes = nommer(articles, vecteurs_candidat, labels, mots, candidat.get("nommage"))
            resultat = {
                "nom": nom, "statut": "succes", **mesurer(vecteurs_candidat, labels, config["silhouette"]),
                "taille_max": max((t["taille"] for t in themes), default=0),
                "duree_s": round(time.monotonic() - debut, 2),
            }
            archiver(nom + "/themes.json", themes)
            archiver(nom + "/affectations.json", labels)
            archiver(nom + "/parametres_effectifs.json", effectifs)
        except Exception as erreur:
            resultat = {"nom": nom, "statut": "echec", "erreur": f"{type(erreur).__name__}: {erreur}"}
        rapport["resultats"].append(resultat)
        rapport["artefacts"] = {k: v for k, v in manifeste.items() if k != "rapport.json"}
        archiver("rapport.json", rapport)
        print(json.dumps(resultat, ensure_ascii=False), flush=True)
    rapport["termine_le"] = datetime.now(timezone.utc).isoformat()
    archiver("rapport.json", rapport)
    print(json.dumps({"comparaison": identifiant, "bucket": bucket, "prefixe": prefixe}, ensure_ascii=False))
    return rapport


def main():
    from src.stockage.bronze import client_minio
    from src.stockage.sources import connexion

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-run", required=True)
    parser.add_argument("--filtre", default="", help="Préfixe des variantes à exécuter")
    args = parser.parse_args()
    conn = connexion()
    try:
        comparer(conn, client_minio(), args.source_run, args.filtre)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
