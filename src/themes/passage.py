"""Exécution traçable du TD 5, en ligne de commande ou depuis Airflow."""

import argparse
import hashlib
import importlib.metadata
import io
import json
import logging
import platform
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
from psycopg2.extras import Json, RealDictCursor, execute_batch

from src.themes.configuration import CONFIG_DEFAUT, charger, empreinte, json_canonique
from src.themes.embeddings import vectoriser
from src.themes.regroupement import mesurer, nommer, regrouper

VERROU = 205005


def lire_articles(conn, debut: datetime, fin: datetime) -> list[dict]:
    with conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT id, source, lien, titre, extrait, publie_le, recupere_le
            FROM articles_propres WHERE publie_le >= %s AND publie_le < %s ORDER BY id
        """, (debut, fin))
        return [
            {k: v.isoformat() if isinstance(v, datetime) else v for k, v in dict(a).items()}
            for a in cur.fetchall()
        ]


def versions() -> dict:
    return {
        "python": platform.python_version(),
        "plateforme": platform.platform(),
        "dependances": {d.metadata["Name"]: d.version for d in importlib.metadata.distributions()},
    }


def sources_code() -> dict:
    racine = Path(__file__).resolve().parents[1]
    return {
        str(p.relative_to(racine)): p.read_text(encoding="utf-8")
        for p in sorted(racine.rglob("*.py"))
    }


def ecrire_artefact(client, bucket, prefixe, nom, contenu, manifeste, type_contenu="application/json"):
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)
    cle = prefixe + "/" + nom
    client.put_object(bucket, cle, io.BytesIO(contenu), len(contenu), content_type=type_contenu)
    manifeste[nom] = {
        "bucket": bucket, "cle": cle, "sha256": hashlib.sha256(contenu).hexdigest(),
        "octets": len(contenu),
    }


def publier(conn, run_id, articles, labels, themes, metriques, artefacts):
    """Publication atomique : les thèmes deviennent visibles uniquement au succès."""
    with conn, conn.cursor() as cur:
        execute_batch(cur, """
            INSERT INTO themes (run_id, theme_id, nom, mots_cles, taille, article_representant,
                                titre_representant, nommage)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, [
            (run_id, t["theme_id"], t["nom"], Json(t["mots_cles"]), t["taille"], t["article_representant"],
             t.get("titre_representant", t["nom"]), Json(t.get("nommage", {})))
            for t in themes
        ])
        execute_batch(cur, """
            INSERT INTO articles_themes (run_id, article_id, theme_id) VALUES (%s, %s, %s)
        """, [(run_id, a["id"], label if label >= 0 else None) for a, label in zip(articles, labels)])
        cur.execute("""
            UPDATE runs SET statut = 'succes', termine_le = now(), metriques = %s, artefacts = %s
            WHERE id = %s
        """, (Json(metriques), Json(artefacts), run_id))


def executer(conn, client, reference=None, chemin_config=CONFIG_DEFAUT, declencheur="manuel") -> dict:
    reference = reference or datetime.now(timezone.utc)
    if reference.tzinfo is None or reference.utcoffset() is None:
        raise ValueError("L'heure de référence doit préciser son fuseau horaire")
    reference = reference.astimezone(timezone.utc)
    run_id = "themes-" + uuid.uuid4().hex
    with conn, conn.cursor() as cur:
        cur.execute("SELECT pg_try_advisory_lock(%s)", (VERROU,))
        verrouille = cur.fetchone()[0]
    if not verrouille:
        raise RuntimeError("Un regroupement est déjà en cours")
    manifeste = {}
    try:
        environnement = versions()
        code = sources_code()
        code_hash = empreinte(code)
        with conn, conn.cursor() as cur:
            cur.execute("""
                INSERT INTO runs (id, statut, declencheur, reference, versions, code_hash)
                VALUES (%s, 'en_cours', %s, %s, %s, %s)
            """, (run_id, declencheur, reference, Json(environnement), code_hash))
        try:
            config = charger(chemin_config)
            debut = reference - timedelta(hours=config["fenetre_heures"])
            articles = lire_articles(conn, debut, reference)
            hash_entree = empreinte(articles)
            prefixe = f"runs/{reference.date().isoformat()}/{run_id}"
            with conn, conn.cursor() as cur:
                cur.execute("""
                    UPDATE runs SET fenetre_debut = %s, fenetre_fin = %s, nb_articles = %s,
                        hash_entree = %s, config = %s, artefacts = %s WHERE id = %s
                """, (debut, reference, len(articles), hash_entree, Json(config),
                      Json({"bucket": config["artefacts_bucket"], "prefixe": prefixe}), run_id))

            def archiver(nom, valeur):
                ecrire_artefact(client, config["artefacts_bucket"], prefixe, nom,
                               json_canonique(valeur).encode("utf-8"), manifeste)

            archiver("entree.json", articles)
            archiver("config.json", config)
            archiver("environnement.json", {**environnement, "code_hash": code_hash})
            archiver("code.json", code)
            vecteurs, cache = vectoriser(conn, articles, config["embedding"])
            tampon = io.BytesIO()
            np.save(tampon, vecteurs, allow_pickle=False)
            ecrire_artefact(client, config["artefacts_bucket"], prefixe, "embeddings.npy",
                           tampon.getvalue(), manifeste, "application/octet-stream")
            labels, mots, modele, effectifs = regrouper(articles, vecteurs, config)
            noms_config = config.get("nommage") or {}
            libelles_vecteurs = None
            if noms_config.get("libelles") and articles:
                libelles_vecteurs, _ = vectoriser(conn, [
                    {"titre": libelle["description"], "extrait": ""} for libelle in noms_config["libelles"]
                ], config["embedding"])
                tampon_libelles = io.BytesIO()
                np.save(tampon_libelles, libelles_vecteurs, allow_pickle=False)
                ecrire_artefact(client, config["artefacts_bucket"], prefixe, "libelles_embeddings.npy",
                               tampon_libelles.getvalue(), manifeste, "application/octet-stream")
            themes = nommer(articles, vecteurs, labels, mots, noms_config, libelles_vecteurs)
            metriques = {**mesurer(vecteurs, labels, config["silhouette"]), **cache,
                         "nb_reaffectes": effectifs.get("nb_reaffectes", 0)}
            affectations = [
                {"article_id": a["id"], "theme_id": label if label >= 0 else None}
                for a, label in zip(articles, labels)
            ]
            archiver("themes.json", themes)
            archiver("affectations.json", affectations)
            archiver("parametres_effectifs.json", effectifs)
            archiver("metriques.json", metriques)
            if modele is not None:
                with tempfile.TemporaryDirectory() as dossier:
                    modele.save(dossier, serialization="safetensors", save_ctfidf=True,
                                save_embedding_model=False)
                    for fichier in sorted(Path(dossier).rglob("*")):
                        if fichier.is_file():
                            ecrire_artefact(
                                client, config["artefacts_bucket"], prefixe,
                                "modele/" + fichier.relative_to(dossier).as_posix(),
                                fichier.read_bytes(), manifeste, "application/octet-stream",
                            )
            archiver("run.json", {
                "run_id": run_id, "reference": reference.isoformat(),
                "fenetre_debut": debut.isoformat(), "hash_entree": hash_entree,
                "nb_articles": len(articles), "code_hash": code_hash,
                "metriques": metriques, "artefacts": dict(manifeste),
            })
            publier(conn, run_id, articles, labels, themes, metriques, manifeste)
            return {"run_id": run_id, "nb_articles": len(articles), **metriques}
        except BaseException as erreur:
            conn.rollback()
            with conn, conn.cursor() as cur:
                cur.execute("""
                    UPDATE runs SET statut = 'echec', termine_le = now(), erreur = %s,
                        artefacts = artefacts || %s WHERE id = %s
                """, (f"{type(erreur).__name__}: {erreur}"[:8000], Json(manifeste), run_id))
            raise
    finally:
        conn.rollback()
        with conn, conn.cursor() as cur:
            cur.execute("SELECT pg_advisory_unlock(%s)", (VERROU,))


def main():
    from src.stockage.bronze import client_minio
    from src.stockage.sources import connexion

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG_DEFAUT)
    parser.add_argument("--reference", type=datetime.fromisoformat, help="Fin de fenêtre ISO avec fuseau")
    args = parser.parse_args()
    conn = connexion()
    try:
        bilan = executer(conn, client_minio(), args.reference, args.config)
        print(json.dumps(bilan, ensure_ascii=False, indent=2))
    except Exception:
        logging.exception("Échec de la production des thèmes")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
