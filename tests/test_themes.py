import os
from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from src.themes.configuration import charger, empreinte
from src.themes.embeddings import texte, vectoriser
from src.themes.passage import executer, lire_articles
from src.themes.regroupement import caracteristiques, mesurer, nommer, regrouper, titre_lisible

REFERENCE = datetime(2026, 10, 23, 12, tzinfo=timezone.utc)


def article(numero=0, **champs):
    return {
        "id": f"article-{numero:02}", "source": "Le Monde",
        "lien": f"https://example.fr/{numero}", "titre": f"Actualité numéro {numero}",
        "extrait": "Les dernières informations", "publie_le": REFERENCE - timedelta(hours=1),
        "recupere_le": REFERENCE, "passage": "test", **champs,
    }


@pytest.fixture
def themes_db(db):
    with db, db.cursor() as cur:
        cur.execute("TRUNCATE articles_themes, themes, runs, embeddings, articles_propres")
    return db


def inserer(conn, articles):
    from src.normalisation.passage import ecrire_articles

    ecrire_articles(conn, articles)


def test_configuration_fige_modele_et_parametres():
    config = charger()
    assert config["fenetre_heures"] == 24
    assert len(config["embedding"]["revision"]) == 40
    assert "les" in config["representation"]["stop_words"]
    assert empreinte({"b": 1, "a": 2}) == empreinte({"a": 2, "b": 1})


def test_titre_et_extrait_constituent_le_texte():
    assert texte(article(titre=" Un titre ", extrait=" Extrait ")) == "Un titre\nExtrait"


def test_nom_est_le_titre_le_plus_proche_du_centre():
    articles = [article(i) for i in range(4)]
    vecteurs = np.array([[1., 0.], [.95, .05], [0., 1.], [0., -1.]])
    themes = nommer(articles, vecteurs, [0, 0, 0, -1], {0: [{"mot": "actualité", "score": .5}]})
    assert len(themes) == 1 and themes[0]["taille"] == 3
    assert themes[0]["article_representant"] == articles[1]["id"]
    assert themes[0]["nom"] == articles[1]["titre"]
    assert themes[0]["mots_cles"][0]["mot"] == "actualité"


@pytest.mark.parametrize("labels", [[], [-1, -1], [0, 0], [0, 1]])
def test_silhouette_non_calculable_expliquee(labels):
    resultat = mesurer(np.ones((len(labels), 2)), labels, charger()["silhouette"])
    assert resultat["silhouette"] is None
    assert resultat["silhouette_raison"]


def test_silhouette_exclut_bruit():
    vecteurs = np.array([[1., 0.], [.99, .01], [0., 1.], [.01, .99], [-1., -1.]])
    resultat = mesurer(vecteurs, [0, 0, 1, 1, -1], charger()["silhouette"])
    assert resultat["silhouette"] > .9
    assert resultat["nb_themes"] == 2 and resultat["part_bruit"] == .2


def test_petit_lot_reste_bruit_sans_entrainer_bertopic():
    labels, mots, modele, effectifs = regrouper([article()], np.ones((1, 3)), charger())
    assert labels == [-1] and mots == {} and modele is None
    assert effectifs["raison"] == "lot_trop_petit"


def test_bertopic_regroupe_des_vecteurs_separes():
    rng = np.random.default_rng(42)
    centres = np.eye(3, 12)
    vecteurs = np.vstack([centre + rng.normal(0, .01, (12, 12)) for centre in centres])
    titres = ["Grève trains SNCF", "Élections vote candidats", "Football championnat équipe"]
    articles = [article(i, titre=titres[i // 12]) for i in range(36)]
    config = charger()
    config["hdbscan"].update(min_cluster_size=5, min_samples=2)
    labels, mots, modele, _ = regrouper(articles, vecteurs, config)
    assert len(labels) == 36
    assert len(set(labels) - {-1}) >= 2
    assert mots and modele is not None
    assert any("élections" in terme["mot"] for liste in mots.values() for terme in liste)


def test_mots_titres_renforcent_vecteurs_sans_modifier_cache():
    config = charger()
    config["poids_lexical"] = .2
    vecteurs = np.array([[1., 0.], [1., 0.], [0., 1.]])
    copie = vecteurs.copy()
    features = caracteristiques([article(titre=t) for t in ("Tempête Austen", "Tempête Austen", "Budget national")],
                                vecteurs, config)
    assert features.shape[1] > 2
    assert np.allclose(np.linalg.norm(features, axis=1), 1.)
    assert np.array_equal(vecteurs, copie)


def test_absence_vocabulaire_commun_ne_bloque_pas():
    config = charger()
    config["poids_lexical"] = .2
    vecteurs = np.eye(3)
    assert np.array_equal(caracteristiques([article(titre=t) for t in ("alpha", "beta", "gamma")],
                                          vecteurs, config), vecteurs)


def test_nommage_prefere_titre_court_et_central_sans_tronquer():
    config = {"tolerance_centralite": .06, "poids_mots_cles": .1,
              "longueur_cible": 80, "penalite_longueur": .08}
    articles = [article(0, titre="EN DIRECT : Tempête Austen : " + "des informations détaillées " * 10),
                article(1, titre="Tempête Austen : des vents violents"),
                article(2, titre="La météo du jour")]
    vecteurs = np.array([[1., 0.], [1., 0.], [1., 0.]])
    mots = {0: [{"mot": "tempête austen", "score": 1.}]}
    resultat = nommer(articles, vecteurs, [0, 0, 0], mots, config)[0]
    assert resultat["nom"] == articles[1]["titre"]
    assert resultat["article_representant"] == articles[1]["id"]


def test_nommage_ne_choisit_pas_un_titre_court_hors_centre():
    config = {"tolerance_centralite": .01, "poids_mots_cles": 1.,
              "longueur_cible": 10, "penalite_longueur": 1.}
    articles = [article(0), article(1), article(2, titre="Court")]
    vecteurs = np.array([[1., 0.], [1., .01], [0., 1.]])
    assert nommer(articles, vecteurs, [0, 0, 0], {}, config)[0]["article_representant"] != articles[2]["id"]


def test_nettoyage_prefixe_ne_retire_pas_le_sujet():
    assert titre_lisible("VIDÉO. Tempête Austen : des dégâts") == "Tempête Austen : des dégâts"
    assert titre_lisible("Brest : un match reporté") == "Brest : un match reporté"


def test_fenetre_sur_publication_bornes_et_ordre(themes_db):
    debut = REFERENCE - timedelta(hours=24)
    inserer(themes_db, [
        article(0, publie_le=debut), article(1, publie_le=REFERENCE),
        article(2, publie_le=debut - timedelta(seconds=1)), article(3, publie_le=None), article(4),
    ])
    assert [a["id"] for a in lire_articles(themes_db, debut, REFERENCE)] == ["article-00", "article-04"]


def test_cache_dix_articles_invalidation_texte_et_modele(themes_db):
    config = charger()["embedding"]
    articles = [article(i) for i in range(10)]
    appels = []

    def encodeur(textes, config):
        appels.append(len(textes))
        return np.ones((len(textes), 4), dtype=np.float32)

    vecteurs, bilan = vectoriser(themes_db, articles, config, encodeur)
    assert vecteurs.shape == (10, 4) and bilan["cache_calcules"] == 10
    autres, bilan = vectoriser(themes_db, articles, config, encodeur)
    assert np.array_equal(vecteurs, autres) and bilan["cache_reutilises"] == 10
    articles[0]["extrait"] = "Un texte corrigé"
    _, bilan = vectoriser(themes_db, articles, config, encodeur)
    assert bilan == {"cache_reutilises": 9, "cache_calcules": 1}
    vectoriser(themes_db, articles, {**config, "revision": "a" * 40}, encodeur)
    vectoriser(themes_db, articles, {**config, "max_seq_length": 64}, encodeur)
    assert appels == [10, 1, 10, 10]


@pytest.mark.skipif(os.environ.get("GAZETTE_TEST_MODELE") != "1", reason="Modèle réel : test explicite")
def test_modele_reel_sur_dix_articles_et_cache(themes_db):
    config = charger()["embedding"]
    articles = [article(i) for i in range(10)]
    vecteurs, bilan = vectoriser(themes_db, articles, config)
    assert vecteurs.shape == (10, 384) and np.isfinite(vecteurs).all()
    assert np.allclose(np.linalg.norm(vecteurs, axis=1), 1., atol=1e-5)
    assert bilan["cache_calcules"] == 10

    def interdit(*args):
        pytest.fail("Le cache doit éviter un deuxième encodage")

    autres, bilan = vectoriser(themes_db, articles, config, interdit)
    assert np.array_equal(vecteurs, autres) and bilan["cache_reutilises"] == 10


def test_run_vide_archive_et_ne_garde_pas_anciens_themes(themes_db, faux_minio):
    bilan = executer(themes_db, faux_minio, REFERENCE)
    assert bilan["nb_articles"] == 0 and bilan["nb_themes"] == 0
    with themes_db, themes_db.cursor() as cur:
        cur.execute("SELECT statut, nb_articles, artefacts FROM runs WHERE id = %s", (bilan["run_id"],))
        statut, n, artefacts = cur.fetchone()
        assert statut == "succes" and n == 0
        assert "entree.json" in artefacts and "embeddings.npy" in artefacts
        cur.execute("SELECT count(*) FROM themes_courants")
        assert cur.fetchone()[0] == 0


def test_echec_trace_sans_publication_partielle(themes_db, faux_minio, monkeypatch):
    inserer(themes_db, [article()])

    def panne(*args):
        raise RuntimeError("encodeur indisponible")

    monkeypatch.setattr("src.themes.passage.vectoriser", panne)
    with pytest.raises(RuntimeError, match="indisponible"):
        executer(themes_db, faux_minio, REFERENCE)
    with themes_db, themes_db.cursor() as cur:
        cur.execute("SELECT statut, erreur, nb_articles FROM runs")
        statut, erreur, n = cur.fetchone()
        assert statut == "echec" and "indisponible" in erreur and n == 1
        cur.execute("SELECT count(*) FROM articles_themes")
        assert cur.fetchone()[0] == 0


def test_run_publie_themes_et_bruit_atomiquement(themes_db, faux_minio, monkeypatch):
    inserer(themes_db, [article(i) for i in range(3)])
    monkeypatch.setattr("src.themes.passage.vectoriser", lambda conn, items, config: (
        np.tile([[1., 0.]], (len(items), 1)), {"cache_calcules": len(items), "cache_reutilises": 0},
    ))
    monkeypatch.setattr("src.themes.passage.regrouper", lambda *args: (
        [0, 0, -1], {0: [{"mot": "actualités", "score": .5}]}, None, {},
    ))
    bilan = executer(themes_db, faux_minio, REFERENCE)
    with themes_db, themes_db.cursor() as cur:
        cur.execute("SELECT taille, nom, titre_representant FROM themes_courants")
        taille, nom, titre = cur.fetchone()
        assert taille == 2 and nom and titre.startswith("Actualité")
        cur.execute("SELECT count(*), count(theme_id) FROM articles_themes WHERE run_id = %s",
                    (bilan["run_id"],))
        assert cur.fetchone() == (3, 2)


def test_echec_archivage_conserve_dernier_succes(themes_db, faux_minio, monkeypatch):
    premier = executer(themes_db, faux_minio, REFERENCE)

    def panne(*args, **kwargs):
        raise RuntimeError("stockage indisponible")

    monkeypatch.setattr("src.themes.passage.ecrire_artefact", panne)
    with pytest.raises(RuntimeError, match="stockage indisponible"):
        executer(themes_db, faux_minio, REFERENCE)
    with themes_db, themes_db.cursor() as cur:
        cur.execute("SELECT id FROM runs WHERE statut = 'succes'")
        assert cur.fetchall() == [(premier["run_id"],)]
        cur.execute("SELECT count(*) FROM runs WHERE statut = 'echec'")
        assert cur.fetchone()[0] == 1


def test_rejeu_historique_ne_remplace_pas_fenetre_recente(themes_db):
    with themes_db, themes_db.cursor() as cur:
        for identifiant, reference, debut in [
            ("courant", REFERENCE, REFERENCE),
            ("rejeu", REFERENCE - timedelta(days=1), REFERENCE + timedelta(hours=1)),
        ]:
            cur.execute("""INSERT INTO runs (id, statut, declencheur, reference, commence_le, code_hash)
                VALUES (%s, 'succes', 'test', %s, %s, 'code')""", (identifiant, reference, debut))
            cur.execute("""INSERT INTO themes
                (run_id, theme_id, nom, mots_cles, taille, article_representant, titre_representant)
                VALUES (%s, 0, %s, '[]', 1, 'article', 'Un titre')""", (identifiant, identifiant))
        cur.execute("SELECT run_id FROM themes_courants")
        assert cur.fetchone() == ("courant",)
