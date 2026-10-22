"""DAG Airflow : la collecte de toutes les sources, toutes les 30 minutes."""

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
        from src.collecte.collecteur import collecter_tout
        from src.stockage import sources
        from src.stockage.bronze import Bronze

        conn = sources.connexion()
        try:
            compteurs = collecter_tout(conn, Bronze(), os.environ.get("SOURCES_CSV"))
        finally:
            conn.close()

        if compteurs["mises_en_sommeil"]:
            raise AirflowException(
                "Sources mises en sommeil : "
                + ", ".join(compteurs["mises_en_sommeil"])
            )
        return compteurs

    collecter()


collecte_rss()
