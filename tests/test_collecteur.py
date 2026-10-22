import http.server
import json
import logging
import threading
from pathlib import Path

import pytest

from src.collecte.collecteur import collecter_tout
from src.stockage import sources
from src.stockage.bronze import Bronze

FIXTURE = (Path(__file__).parent / "fixtures" / "humanite.xml").read_bytes()


@pytest.fixture
def serveur():
    """Serveur HTTP local : etat["reponse"] décide de ce qu'il renvoie."""
    etat = {"requetes": [], "reponse": lambda entetes: (200, {}, FIXTURE)}

    class Gestionnaire(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            etat["requetes"].append(dict(self.headers))
            statut, entetes, corps = etat["reponse"](self.headers)
            self.send_response(statut)
            for nom, valeur in entetes.items():
                self.send_header(nom, valeur)
            self.send_header("Content-Length", str(len(corps)))
            self.end_headers()
            self.wfile.write(corps)

        def log_message(self, *args):
            pass

    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Gestionnaire)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    etat["url"] = f"http://127.0.0.1:{httpd.server_port}/flux"
    yield etat
    httpd.shutdown()
    httpd.server_close()


def une_source(db, serveur, nom="Test"):
    sources.synchroniser(db, [{"nom": nom, "type": "PQN", "url_flux": serveur["url"]}])


def test_source_en_panne_reessaie_puis_s_endort(db, serveur, faux_minio):
    serveur["reponse"] = lambda entetes: (503, {}, b"indisponible")
    une_source(db, serveur, "Panne")
    bronze = Bronze(faux_minio, "bronze")

    premier = collecter_tout(db, bronze, attente=0)
    assert len(serveur["requetes"]) == 3  # 503 transitoire : 3 essais
    assert premier["echecs"] == 1
    assert sources.sources_actives(db)[0]["echecs_consecutifs"] == 1

    collecter_tout(db, bronze, attente=0)
    troisieme = collecter_tout(db, bronze, attente=0)
    assert troisieme["mises_en_sommeil"] == ["Panne"]
    assert sources.sources_actives(db) == []

    serveur["requetes"].clear()
    assert collecter_tout(db, bronze, attente=0)["sources"] == 0
    assert serveur["requetes"] == []  # en sommeil : on ne la sollicite plus


def test_erreur_permanente_sans_nouvel_essai(db, serveur, faux_minio):
    serveur["reponse"] = lambda entetes: (404, {}, b"introuvable")
    une_source(db, serveur)
    compteurs = collecter_tout(db, Bronze(faux_minio, "bronze"), attente=0)
    assert len(serveur["requetes"]) == 1
    assert compteurs["echecs"] == 1


def test_flux_casse_compte_comme_un_echec(db, serveur, faux_minio):
    serveur["reponse"] = lambda entetes: (200, {}, b"<html>maintenance</html")
    une_source(db, serveur)
    assert collecter_tout(db, Bronze(faux_minio, "bronze"), attente=0)["echecs"] == 1


def test_deux_passages_zero_doublon(db, serveur, faux_minio):
    une_source(db, serveur)
    bronze = Bronze(faux_minio, "bronze")

    premier = collecter_tout(db, bronze, attente=0)
    second = collecter_tout(db, bronze, attente=0)

    assert (premier["recus"], premier["ecrits"], premier["ignores"]) == (20, 20, 0)
    assert (second["recus"], second["ecrits"], second["ignores"]) == (20, 0, 20)
    assert len(faux_minio.buckets["bronze"]) == 20


def test_etag_evite_de_retelecharger(db, serveur, faux_minio):
    def reponse(entetes):
        if entetes.get("If-None-Match") == '"v1"':
            return 304, {}, b""
        return 200, {"ETag": '"v1"'}, FIXTURE

    serveur["reponse"] = reponse
    une_source(db, serveur)
    bronze = Bronze(faux_minio, "bronze")

    assert collecter_tout(db, bronze, attente=0)["ok"] == 1
    assert collecter_tout(db, bronze, attente=0)["inchanges"] == 1
    assert serveur["requetes"][1]["If-None-Match"] == '"v1"'
    assert sources.sources_actives(db)[0]["echecs_consecutifs"] == 0


def test_journal_une_ligne_par_source(db, serveur, faux_minio, caplog):
    une_source(db, serveur, "A")
    une_source(db, serveur, "B")
    with caplog.at_level(logging.INFO, logger="collecte"):
        collecter_tout(db, Bronze(faux_minio, "bronze"), attente=0)

    lignes = [json.loads(message) for message in caplog.messages]
    par_source = [ligne for ligne in lignes if "source" in ligne]
    assert [ligne["source"] for ligne in par_source] == ["A", "B"]
    for ligne in par_source:
        assert {"recus", "ecrits", "ignores", "duree_s", "statut"} <= set(ligne)
    assert lignes[-1]["passage"]["sources"] == 2
