"""Un vecteur par titre + extrait ; cache invalidé par texte/modèle/options."""

import numpy as np
from psycopg2.extras import execute_batch

from src.themes.configuration import empreinte


def texte(article: dict, config: dict | None = None) -> str:
    titre = article["titre"].strip()
    if config and config.get("champs") == "titre":
        return titre
    return titre + "\n" + (article.get("extrait") or "").strip()


def encoder(textes: list[str], config: dict) -> np.ndarray:
    import torch
    from sentence_transformers import SentenceTransformer

    torch.set_num_threads(config["threads"])
    modele = SentenceTransformer(config["modele"], revision=config["revision"], device="cpu")
    modele.max_seq_length = config["max_seq_length"]
    return modele.encode(
        textes, batch_size=config["batch_size"], normalize_embeddings=True,
        convert_to_numpy=True, show_progress_bar=False,
    )


def vectoriser(conn, articles: list[dict], config: dict, encodeur=None) -> tuple[np.ndarray, dict]:
    if not articles:
        return np.empty((0, 0), dtype=np.float32), {"cache_reutilises": 0, "cache_calcules": 0}
    textes = [texte(a, config) for a in articles]
    hashes = [empreinte(t) for t in textes]
    options_hash = empreinte({"normalisation": True, "max_seq_length": config["max_seq_length"]})
    cle_modele = (config["modele"], config["revision"], options_hash)
    with conn, conn.cursor() as cur:
        cur.execute(
            """SELECT texte_hash, vecteur FROM embeddings
               WHERE modele = %s AND revision = %s AND options_hash = %s
                 AND texte_hash = ANY(%s)""", (*cle_modele, hashes),
        )
        cache = {h: np.asarray(v, dtype=np.float32) for h, v in cur.fetchall()}
    reutilises = sum(h in cache for h in hashes)
    manquants = dict((h, t) for h, t in zip(hashes, textes) if h not in cache)
    if manquants:
        vecteurs = np.asarray((encodeur or encoder)(list(manquants.values()), config), dtype=np.float32)
        if vecteurs.ndim != 2 or len(vecteurs) != len(manquants) or not np.isfinite(vecteurs).all():
            raise ValueError("L'encodeur a renvoyé des vecteurs invalides")
        if vecteurs.shape[1] == 0 or np.any(np.linalg.norm(vecteurs, axis=1) == 0):
            raise ValueError("L'encodeur a renvoyé un vecteur vide ou nul")
        cache.update(zip(manquants, vecteurs))
        with conn, conn.cursor() as cur:
            execute_batch(cur, """
                INSERT INTO embeddings (texte_hash, modele, revision, options_hash, vecteur)
                VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING
            """, [(h, *cle_modele, cache[h].tolist()) for h in manquants])
    resultat = np.stack([cache[h] for h in hashes])
    return resultat, {"cache_reutilises": reutilises, "cache_calcules": len(manquants)}
