"""Carte Teams Workflows ; aucun secret ni URL n'est journalisé."""

import os
import time

import requests

TACHES = ("collecter", "controler_qualite", "produire_themes")


class NotificationError(RuntimeError):
    pass


def construire_bilan(run_id, etats, compteurs, environnement="local", duree_s=None):
    erreurs = [t for t in TACHES if etats.get(t) != "success"]
    collecte = compteurs.get("collecter") or {}
    qualite = compteurs.get("controler_qualite") or {}
    themes = compteurs.get("produire_themes") or {}
    statut = "echec" if erreurs else "succes"
    if statut == "succes" and collecte.get("echecs", 0):
        statut = "avertissement"
    if statut == "succes" and themes.get("nb_articles") == 0:
        statut = "avertissement"

    def nombre(donnees, cle):
        return str(donnees[cle]) if cle in donnees else "Indisponible"

    faits = [
        ("Environnement", environnement), ("Pipeline", run_id), ("État", statut),
        ("Durée", f"{duree_s:.0f} s" if duree_s is not None else "Indisponible"),
        ("Sources consultées", nombre(collecte, "sources")),
        ("Sources en erreur", nombre(collecte, "echecs")),
        ("Sources mises en sommeil", str(len(collecte["mises_en_sommeil"]))
         if "mises_en_sommeil" in collecte else "Indisponible"),
        ("Articles reçus des flux", nombre(collecte, "recus")),
        ("Nouveaux articles Bronze", nombre(collecte, "ecrits")),
        ("Articles déjà présents", nombre(collecte, "ignores")),
        ("Stock Bronze contrôlé", nombre(qualite, "entres")),
        ("Articles gardés au nettoyage", nombre(qualite, "gardes")),
        ("Articles rejetés au nettoyage", nombre(qualite, "rejetes")),
        ("Articles analysés sur 24 h", nombre(themes, "nb_articles")),
        ("Thèmes produits", nombre(themes, "nb_themes")),
        ("Articles sans thème", nombre(themes, "nb_bruit")),
        ("Run des thèmes", themes.get("run_id", "Indisponible")),
    ]
    if erreurs:
        faits.append(("Étapes non réussies", ", ".join(f"{t}: {etats.get(t, 'inconnu')}" for t in erreurs)))
    if themes.get("nb_articles") == 0:
        faits.append(("Fraîcheur", "Aucun article publié dans la fenêtre de 24 h"))
    return {"statut": statut, "erreurs": erreurs, "faits": faits}


def carte(bilan):
    return {
        "type": "message",
        "attachments": [{
            "contentType": "application/vnd.microsoft.card.adaptive",
            "contentUrl": None,
            "content": {
                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                "type": "AdaptiveCard", "version": "1.4",
                "body": [
                    {"type": "TextBlock", "text": "La Gazette — " + bilan["statut"],
                     "weight": "Bolder", "size": "Medium", "wrap": True},
                    {"type": "FactSet", "facts": [
                        {"title": titre, "value": valeur} for titre, valeur in bilan["faits"]
                    ]},
                ],
            },
        }],
    }


def envoyer(bilan, url=None, tentatives=3):
    url = url if url is not None else os.environ.get("TEAMS_WEBHOOK_URL", "")
    if not url:
        return {"statut": "desactive"}
    if not url.startswith("https://"):
        raise NotificationError("Le webhook Teams doit utiliser HTTPS")
    for tentative in range(tentatives):
        try:
            reponse = requests.post(url, json=carte(bilan), timeout=(5, 15), allow_redirects=False)
        except requests.RequestException:
            message = "Teams : connexion impossible ou délai dépassé"
        else:
            if 200 <= reponse.status_code < 300:
                return {"statut": "envoye"}
            message = f"Teams : HTTP {reponse.status_code}"
            if reponse.status_code != 429 and reponse.status_code < 500:
                raise NotificationError(message)
        if tentative + 1 < tentatives:
            time.sleep(2 ** tentative)
    raise NotificationError(message) from None


def notifier_contexte(contexte):
    ti = contexte["ti"]
    instances = contexte["dag_run"].get_task_instances()
    etats = {t.task_id: t.state for t in instances if t.task_id in TACHES}
    compteurs = {
        t: ti.xcom_pull(task_ids=t, key="bilan") or ti.xcom_pull(task_ids=t, key="return_value")
        for t in TACHES
    }
    debut = contexte["dag_run"].start_date
    from datetime import datetime, timezone

    duree = (datetime.now(timezone.utc) - debut).total_seconds() if debut else None
    bilan = construire_bilan(contexte["run_id"], etats, compteurs,
                             os.environ.get("GAZETTE_ENV", "local"), duree)
    resultat = envoyer(bilan)
    # Cette tâche est une feuille all_done : elle doit préserver les échecs amont.
    if bilan["erreurs"]:
        raise RuntimeError("Pipeline en échec : " + ", ".join(bilan["erreurs"]))
    return {**resultat, "pipeline": bilan["statut"]}
