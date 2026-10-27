"""DAG Airflow : la collecte de toutes les sources, toutes les 30 minutes."""

import json
import logging
import os
from datetime import timedelta

import pendulum
from airflow.decorators import dag, task
from airflow.exceptions import AirflowException


@dag(
    dag_id="collecte_rss",
    schedule="*/30 * * * *",
    start_date=pendulum.datetime(2026, 10, 1, tz="UTC"),
    catchup=False,  # pas de rattrapage des passages manqués
    max_active_runs=1,  # jamais deux collectes en même temps
    is_paused_upon_creation=False,  # tourne dès le démarrage, sans clic
    default_args={"retries": 0},  # le passage suivant (30 min) sert de reprise
    tags=["collecte"],
    doc_md="""
    Passe sur toutes les sources actives de `docs/sources.csv` et écrit les
    nouveaux items dans MinIO (`bronze/articles_bruts/`). Le détail de chaque
    source est dans le journal de la tâche (une ligne JSON par source).

    La tâche passe en **échec** quand une source vient d'être mise en sommeil
    (3 échecs d'affilée) : il faut regarder pourquoi. Voir `docs/donnees.md`.
    """,
)
def collecte_rss():
    @task(execution_timeout=timedelta(minutes=20))
    def collecter() -> dict:
        from airflow.operators.python import get_current_context

        from src.collecte.collecteur import collecter_tout
        from src.stockage import sources
        from src.stockage.bronze import Bronze

        conn = sources.connexion()
        try:
            compteurs = collecter_tout(conn, Bronze(), os.environ.get("SOURCES_CSV"))
        finally:
            conn.close()

        get_current_context()["ti"].xcom_push(key="bilan", value=compteurs)
        if compteurs["mises_en_sommeil"]:
            raise AirflowException(
                "Sources mises en sommeil : "
                + ", ".join(compteurs["mises_en_sommeil"])
            )
        return compteurs

    @task(trigger_rule="all_done", execution_timeout=timedelta(minutes=10))
    def controler_qualite() -> dict:
        """Passage de nettoyage après la collecte. Tourne même si la collecte a échoué :
        les sources saines doivent quand même être nettoyées."""
        from airflow.operators.python import get_current_context

        from src.normalisation.passage import executer
        from src.stockage import sources
        from src.stockage.bronze import client_minio

        conn = sources.connexion()
        try:
            bilan = executer(client_minio(), conn)
        finally:
            conn.close()
        logging.getLogger("qualite").info(json.dumps({"passage": bilan}, ensure_ascii=False))
        get_current_context()["ti"].xcom_push(key="bilan", value=bilan)
        if bilan["alertes"]:
            raise AirflowException(
                "Taux de rejet supérieur à 80 % : " + ", ".join(bilan["alertes"])
            )
        return bilan

    @task(execution_timeout=timedelta(minutes=20))
    def produire_themes() -> dict:
        from airflow.operators.python import get_current_context

        from src.stockage import sources
        from src.stockage.bronze import client_minio
        from src.themes.passage import executer

        contexte = get_current_context()
        conn = sources.connexion()
        try:
            bilan = executer(
                conn, client_minio(), reference=contexte["data_interval_end"],
                declencheur=f"airflow:{contexte['run_id']}",
            )
        finally:
            conn.close()
        logging.getLogger("themes").info(json.dumps(bilan, ensure_ascii=False))
        return bilan

    @task(trigger_rule="all_done", execution_timeout=timedelta(minutes=2))
    def notifier_bilan() -> dict:
        from airflow.operators.python import get_current_context

        from src.notifications.teams import notifier_contexte

        return notifier_contexte(get_current_context())

    collecte = collecter()
    controle = controler_qualite()
    themes = produire_themes()
    collecte >> controle >> themes
    notification = notifier_bilan()
    [collecte, controle, themes] >> notification


collecte_rss()


