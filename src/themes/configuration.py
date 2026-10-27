"""Configuration versionnée et empreintes canoniques."""

import hashlib
import json
from pathlib import Path

import yaml

CONFIG_DEFAUT = Path(__file__).resolve().parents[2] / "config" / "clustering.yaml"


def json_canonique(valeur) -> str:
    return json.dumps(valeur, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def empreinte(valeur) -> str:
    return hashlib.sha256(json_canonique(valeur).encode("utf-8")).hexdigest()


def charger(chemin=CONFIG_DEFAUT) -> dict:
    chemin = Path(chemin)
    config = yaml.safe_load(chemin.read_text(encoding="utf-8"))
    for section in ("embedding", "umap", "hdbscan", "representation", "silhouette"):
        if not isinstance(config.get(section), dict):
            raise ValueError(f"Section de configuration absente : {section}")
    if config["fenetre_heures"] != 24:
        raise ValueError("Le TD 5 traite uniquement les dernières 24 heures")
    if config.get("reduction", "umap") not in ("umap", "original"):
        raise ValueError("Réduction inconnue")
    if config.get("themes_cible") is not None and (
        not isinstance(config["themes_cible"], int) or isinstance(config["themes_cible"], bool)
        or config["themes_cible"] < 2
    ):
        raise ValueError("themes_cible doit être un entier >= 2")
    if config["embedding"].get("champs", "titre_extrait") not in ("titre", "titre_extrait"):
        raise ValueError("Champs d'embedding inconnus")
    if not 0 <= config.get("poids_lexical", 0.) < 1:
        raise ValueError("Le poids lexical doit être entre 0 inclus et 1 exclu")
    if config.get("reaffectation_seuil") is not None and not 0 < config["reaffectation_seuil"] <= 1:
        raise ValueError("Le seuil de réaffectation doit être entre 0 exclu et 1 inclus")
    if "nommage" in config:
        nommage = config["nommage"]
        if nommage["longueur_cible"] < 1 or any(
            not 0 <= nommage[k] <= 1
            for k in ("tolerance_centralite", "poids_mots_cles", "penalite_longueur")
        ):
            raise ValueError("Paramètres de nommage invalides")
        if nommage.get("libelles"):
            nommage["libelles"] = yaml.safe_load(
                (chemin.parent / nommage["libelles"]).read_text(encoding="utf-8")
            )
            if not nommage["libelles"] or any(
                not libelle.get("nom") or not libelle.get("description") for libelle in nommage["libelles"]
            ):
                raise ValueError("Les libellés doivent avoir un nom et une description")
    revision = config["embedding"]["revision"]
    if len(revision) != 40 or any(c not in "0123456789abcdef" for c in revision):
        raise ValueError("La révision du modèle doit être un commit SHA exact")
    for section, cles in {
        "embedding": ("batch_size", "max_seq_length", "threads"),
        "umap": ("n_neighbors", "n_components"),
        "hdbscan": ("min_cluster_size", "min_samples"),
        "representation": ("top_n_words",),
        "silhouette": ("sample_size",),
    }.items():
        if any(not isinstance(config[section][c], int) or isinstance(config[section][c], bool)
               or config[section][c] < 1 for c in cles):
            raise ValueError(f"Les tailles de {section} doivent être des entiers positifs")
    if config["hdbscan"]["min_cluster_size"] < 2 or config["umap"]["n_neighbors"] < 2:
        raise ValueError("min_cluster_size et n_neighbors doivent être >= 2")
    if config["silhouette"]["sample_size"] < 3:
        raise ValueError("sample_size doit être >= 3")
    mots = chemin.parent / config["representation"].pop("stop_words")
    config["representation"]["stop_words"] = [
        m.strip() for m in mots.read_text(encoding="utf-8").splitlines() if m.strip()
    ]
    return config
