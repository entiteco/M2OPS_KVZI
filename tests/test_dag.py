from pathlib import Path

from airflow.models import DagBag

DOSSIER_DAGS = Path(__file__).resolve().parents[1] / "src" / "dags"
if not DOSSIER_DAGS.is_dir():  # dans le conteneur (bin/test)
    DOSSIER_DAGS = Path("/opt/airflow/dags/src/dags")


def test_dag_collecte_se_charge_et_tourne_toutes_les_30_min():
    dagbag = DagBag(dag_folder=str(DOSSIER_DAGS), include_examples=False)
    assert dagbag.import_errors == {}

    # dagbag.dags plutôt que get_dag() : pas besoin de la base d'Airflow (absente en CI)
    dag = dagbag.dags["collecte_rss"]
    assert dag.schedule_interval == "*/30 * * * *"
    assert dag.catchup is False
    assert dag.max_active_runs == 1
    assert sorted(tache.task_id for tache in dag.tasks) == [
        "collecter", "controler_qualite", "notifier_bilan", "produire_themes",
    ]
    assert dag.get_task("controler_qualite").trigger_rule == "all_done"
    assert dag.get_task("produire_themes").upstream_task_ids == {"controler_qualite"}
    assert dag.get_task("produire_themes").trigger_rule == "all_success"
    assert dag.get_task("notifier_bilan").upstream_task_ids == {
        "collecter", "controler_qualite", "produire_themes",
    }
    assert dag.get_task("notifier_bilan").trigger_rule == "all_done"
