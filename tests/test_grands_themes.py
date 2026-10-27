import numpy as np

from src.themes.configuration import charger
from src.themes.regroupement import nommer, regrouper


def test_nommage_general_et_titre_illustratif_distincts():
    config = {"tolerance_centralite": .1, "poids_mots_cles": .1,
              "longueur_cible": 110, "penalite_longueur": .08,
              "libelles": [
                  {"nom": "Le sport et les compétitions", "description": "football rugby match"},
                  {"nom": "La vie politique", "description": "élections gouvernement"},
              ]}
    articles = [{"id": "a", "titre": "Rugby : le match de Toulouse"},
                {"id": "b", "titre": "Football : un joueur rejoint son club"}]
    vecteurs = np.array([[1., 0.], [1., .01]])
    resultat = nommer(articles, vecteurs, [0, 0], {0: [{"mot": "rugby", "score": .5}]},
                      config, np.eye(2))[0]
    assert resultat["nom"] == "Le sport et les compétitions"
    assert resultat["titre_representant"] in [a["titre"] for a in articles]
    assert resultat["nommage"]["methode"] == "libelle_semantique"


def test_reduction_plafonne_sans_creer_des_themes_artificiels():
    config = charger()
    config.update(themes_cible=2, poids_lexical=0., reaffectation_seuil=None)
    config["hdbscan"].update(min_cluster_size=4, min_samples=2)
    config["umap"]["n_neighbors"] = 5
    rng = np.random.default_rng(8)
    vecteurs = np.vstack([v + rng.normal(0, .01, (10, 12)) for v in np.eye(4, 12)])
    articles = [{"id": str(i), "titre": ["Football rugby match", "Budget impôts finances",
                 "Livres culture romans", "Médecine patients hôpital"][i // 10], "extrait": ""}
                for i in range(40)]
    labels, _, _, effectifs = regrouper(articles, vecteurs, config)
    assert effectifs["nb_themes_initiaux"] >= 2
    assert len(set(labels) - {-1}) <= 2
    assert len(labels) == len(articles)
