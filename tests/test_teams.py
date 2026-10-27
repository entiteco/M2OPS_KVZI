from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
import requests

from src.notifications.teams import NotificationError, TACHES, carte, construire_bilan, envoyer, notifier_contexte


def bilan():
    return construire_bilan("test", dict.fromkeys(TACHES, "success"), {
        "collecter": {"recus": 20, "ecrits": 3, "ignores": 17},
        "controler_qualite": {"entres": 100, "gardes": 95, "rejetes": 5},
        "produire_themes": {"nb_articles": 30, "nb_themes": 4, "nb_bruit": 5},
    })


def test_bilan_distingue_nouveaux_articles_et_stock_total():
    resultat = bilan()
    faits = dict(resultat["faits"])
    assert faits["Nouveaux articles Bronze"] == "3"
    assert faits["Stock Bronze contrôlé"] == "100"
    assert resultat["statut"] == "succes"
    assert carte(resultat)["attachments"][0]["content"]["type"] == "AdaptiveCard"


def test_bilan_incomplet_affiche_indisponible_et_echec():
    resultat = construire_bilan("test", {"collecter": "failed"}, {})
    assert resultat["statut"] == "echec"
    assert dict(resultat["faits"])["Articles reçus des flux"] == "Indisponible"


def test_bilan_signale_absence_articles_recents():
    resultat = construire_bilan("vide", dict.fromkeys(TACHES, "success"),
                                {"produire_themes": {"nb_articles": 0}})
    assert resultat["statut"] == "avertissement"
    assert "Fraîcheur" in dict(resultat["faits"])


def test_absence_url_ne_fait_aucun_appel(monkeypatch):
    monkeypatch.delenv("TEAMS_WEBHOOK_URL", raising=False)
    assert envoyer(bilan()) == {"statut": "desactive"}


def test_envoi_carte_et_timeout(monkeypatch):
    def post(url, **options):
        assert url == "https://example.test/secret"
        assert options["json"]["type"] == "message"
        assert options["timeout"] == (5, 15) and not options["allow_redirects"]
        return SimpleNamespace(status_code=202)
    monkeypatch.setattr("src.notifications.teams.requests.post", post)
    assert envoyer(bilan(), "https://example.test/secret") == {"statut": "envoye"}


def test_erreur_reseau_ne_divulgue_pas_url(monkeypatch):
    def post(*args, **kwargs):
        raise requests.ConnectionError("URL secrète https://example.test/secret")
    monkeypatch.setattr("src.notifications.teams.requests.post", post)
    with pytest.raises(NotificationError) as erreur:
        envoyer(bilan(), "https://example.test/secret", tentatives=1)
    assert "secret" not in str(erreur.value)


def test_reessaie_erreur_transitoire(monkeypatch):
    reponses = iter([503, 202])
    monkeypatch.setattr("src.notifications.teams.requests.post",
                        lambda *a, **k: SimpleNamespace(status_code=next(reponses)))
    monkeypatch.setattr("src.notifications.teams.time.sleep", lambda secondes: None)
    assert envoyer(bilan(), "https://example.test/secret")["statut"] == "envoye"


def test_notification_ne_masque_pas_echec_pipeline(monkeypatch):
    monkeypatch.setattr("src.notifications.teams.envoyer", lambda b: {"statut": "envoye"})
    contexte = {
        "ti": SimpleNamespace(xcom_pull=lambda **kwargs: None), "run_id": "test",
        "dag_run": SimpleNamespace(start_date=datetime.now(timezone.utc), get_task_instances=lambda: [
            SimpleNamespace(task_id=t, state="failed" if t == "collecter" else "success") for t in TACHES
        ]),
    }
    with pytest.raises(RuntimeError, match="collecter"):
        notifier_contexte(contexte)
