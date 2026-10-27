"""BERTopic : UMAP, HDBSCAN et c-TF-IDF ; nom = titre le plus central."""

from collections import Counter
import re
from statistics import median

import numpy as np
from sklearn.metrics import silhouette_score

from src.themes.embeddings import texte
from src.normalisation.texte import cle_titre

PREFIXE_EDITORIAL = re.compile(
    r"^(?:(?:en direct|direct|vidéo|video|en images|portrait|entretien|décryptage|analyse)"
    r"\s*[.:–—-]\s*)+", re.IGNORECASE,
)


def titre_lisible(titre):
    return PREFIXE_EDITORIAL.sub("", titre).strip()


def caracteristiques(articles, vecteurs, config):
    poids = config.get("poids_lexical", 0.0)
    if not poids:
        return vecteurs
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.preprocessing import normalize

    try:
        lexical = TfidfVectorizer(
            ngram_range=(1, 2), stop_words=config["representation"]["stop_words"],
            min_df=2, sublinear_tf=True,
        ).fit_transform([a["titre"] for a in articles]).toarray().astype(np.float32)
    except ValueError as erreur:
        if "empty vocabulary" not in str(erreur) and "After pruning" not in str(erreur):
            raise
        return vecteurs
    return normalize(np.hstack((np.sqrt(1 - poids) * vecteurs, np.sqrt(poids) * lexical)))


def regrouper(articles: list[dict], vecteurs: np.ndarray, config: dict):
    n = len(articles)
    if n < max(4, config["hdbscan"]["min_cluster_size"]):
        return [-1] * n, {}, None, {"raison": "lot_trop_petit"}
    from bertopic import BERTopic
    from bertopic.dimensionality import BaseDimensionalityReduction
    from hdbscan import HDBSCAN
    from sklearn.feature_extraction.text import CountVectorizer
    from umap import UMAP

    umap_config = {
        **config["umap"],
        "n_neighbors": min(config["umap"]["n_neighbors"], n - 1),
        "n_components": min(config["umap"]["n_components"], n - 2),
        "init": "random", "n_jobs": 1,
    }
    representation = config["representation"]
    reduction = config.get("reduction", "umap")
    reducteur = UMAP(**umap_config) if reduction == "umap" else BaseDimensionalityReduction()
    modele = BERTopic(
        language=representation.get("language", "multilingual"),
        embedding_model=None,
        umap_model=reducteur,
        hdbscan_model=HDBSCAN(**config["hdbscan"], core_dist_n_jobs=1),
        vectorizer_model=CountVectorizer(
            stop_words=representation["stop_words"],
            ngram_range=tuple(representation["ngram_range"]),
            token_pattern=r"(?u)\b[^\W\d_][^\W\d_]+\b",
        ),
        top_n_words=representation["top_n_words"], calculate_probabilities=False,
        verbose=False,
    )
    documents = [texte(a) for a in articles]
    features = caracteristiques(articles, vecteurs, config)
    labels, _ = modele.fit_transform(documents, embeddings=features)
    nb_themes_initiaux = len(set(labels) - {-1})
    cible = config.get("themes_cible")
    if cible and nb_themes_initiaux > cible:
        # BERTopic compte aussi le groupe -1 dans nr_topics.
        modele.reduce_topics(documents, nr_topics=cible + int(-1 in labels),
                             use_ctfidf=config.get("reduction_themes_ctfidf", False))
        labels = list(modele.topics_)
    nb_reaffectes = 0
    seuil = config.get("reaffectation_seuil")
    if seuil is not None and -1 in labels and any(label >= 0 for label in labels):
        nouveaux = modele.reduce_outliers(documents, labels, strategy="embeddings",
                                          embeddings=features, threshold=seuil)
        nb_reaffectes = int(sum(a == -1 and b >= 0 for a, b in zip(labels, nouveaux)))
        if nb_reaffectes:
            modele.update_topics(documents, topics=nouveaux, vectorizer_model=modele.vectorizer_model,
                                 ctfidf_model=modele.ctfidf_model,
                                 top_n_words=representation["top_n_words"])
        labels = nouveaux
    mots = {
        int(label): [{"mot": mot, "score": float(score)} for mot, score in modele.get_topic(label) if mot]
        for label in set(labels) if label >= 0
    }
    return list(map(int, labels)), mots, modele, {
        "reduction": reduction, "umap": umap_config if reduction == "umap" else None,
        "hdbscan": config["hdbscan"],
        "poids_lexical": config.get("poids_lexical", 0.0),
        "poids_lexical_effectif": config.get("poids_lexical", 0.0)
        if features.shape[1] > vecteurs.shape[1] else 0.0,
        "reaffectation_seuil": seuil, "nb_reaffectes": nb_reaffectes,
        "themes_cible": cible, "nb_themes_initiaux": nb_themes_initiaux,
    }


def nommer(articles: list[dict], vecteurs: np.ndarray, labels: list[int], mots: dict,
           config: dict | None = None, vecteurs_libelles=None) -> list[dict]:
    themes = []
    for label in sorted(set(labels) - {-1}):
        indices = [i for i, valeur in enumerate(labels) if valeur == label]
        groupe = vecteurs[indices]
        centre = groupe.mean(axis=0)
        # Cosinus avec le vecteur moyen ; argmax départagé par l'ordre stable des IDs.
        scores = (groupe @ centre) / (
            np.maximum(np.linalg.norm(groupe, axis=1), 1e-12) * max(np.linalg.norm(centre), 1e-12)
        )
        choix = scores.copy()
        if config:
            for j, i in enumerate(indices):
                if scores[j] < scores.max() - config["tolerance_centralite"]:
                    choix[j] = -np.inf
                    continue
                titre = titre_lisible(articles[i]["titre"])
                comparable = " " + cle_titre(titre) + " "
                termes = mots.get(label, [])
                total = sum(max(0, t["score"]) for t in termes)
                couverture = sum(
                    max(0, t["score"]) for t in termes
                    if " " + cle_titre(t["mot"]) + " " in comparable
                ) / max(total, 1e-12)
                longueur = min(1., max(0., len(titre) / config["longueur_cible"] - 1))
                choix[j] += config["poids_mots_cles"] * couverture - config["penalite_longueur"] * longueur
        selection = int(np.argmax(choix))
        representant = articles[indices[selection]]
        nom = titre_lisible(representant["titre"]) if config else representant["titre"]
        nommage = {"methode": "titre_representant"}
        if vecteurs_libelles is not None and config and config.get("libelles"):
            similarites = (vecteurs_libelles @ centre) / (
                np.maximum(np.linalg.norm(vecteurs_libelles, axis=1), 1e-12)
                * max(np.linalg.norm(centre), 1e-12)
            )
            termes = mots.get(label, [])
            total = sum(max(0., terme["score"]) for terme in termes)
            couvertures = []
            for libelle in config["libelles"]:
                texte_libelle = libelle["description"] + " " + " ".join(libelle.get("mots_cles", []))
                vocabulaire = {mot.rstrip("s") for mot in cle_titre(texte_libelle).split()}
                couverture = sum(
                    max(0., terme["score"]) for terme in termes
                    if any(mot.rstrip("s") in vocabulaire for mot in cle_titre(terme["mot"]).split())
                ) / max(total, 1e-12)
                couvertures.append(couverture)
            scores_libelles = similarites + config.get("poids_lexical_libelle", .4) * np.array(couvertures)
            meilleur = int(np.argmax(scores_libelles))
            confiance = float(similarites[meilleur])
            if confiance >= config.get("seuil_libelle", .25) or couvertures[meilleur] >= .25:
                nom = config["libelles"][meilleur]["nom"]
                # Un libellé peut correspondre à plusieurs angles distincts.
                if any(t["nom"] == nom for t in themes) and mots.get(label):
                    nom += " — " + ", ".join(t["mot"] for t in mots[label][:2])
                nommage = {"methode": "libelle_semantique", "similarite": confiance,
                           "couverture_mots_cles": couvertures[meilleur],
                           "libelle": config["libelles"][meilleur]["nom"]}
        themes.append({
            "theme_id": label, "nom": nom,
            "article_representant": representant["id"],
            "titre_representant": titre_lisible(representant["titre"]), "nommage": nommage,
            "mots_cles": mots.get(label, []), "taille": len(indices),
            "centralite_representant": float(scores[selection]),
        })
    return themes


def mesurer(vecteurs: np.ndarray, labels: list[int], config: dict) -> dict:
    tailles = Counter(label for label in labels if label >= 0)
    indices = [i for i, label in enumerate(labels) if label >= 0]
    metriques = {
        "nb_themes": len(tailles), "taille_mediane": median(tailles.values()) if tailles else 0,
        "part_bruit": labels.count(-1) / len(labels) if labels else 0.0,
        "nb_bruit": labels.count(-1), "silhouette": None,
        "silhouette_raison": "moins_de_deux_groupes_ou_tous_singletons",
    }
    if 2 <= len(tailles) < len(indices):
        try:
            metriques["silhouette"] = float(silhouette_score(
                vecteurs[indices], np.asarray(labels)[indices], metric="cosine",
                sample_size=min(config["sample_size"], len(indices)),
                random_state=config["random_state"],
            ))
            metriques["silhouette_raison"] = None
        except ValueError:
            metriques["silhouette_raison"] = "echantillon_sans_deux_groupes_valides"
    return metriques
