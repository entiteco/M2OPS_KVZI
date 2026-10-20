import sys
from pathlib import Path

# src/ est à la racine du dépôt en local et en CI, mais monté dans
# /opt/airflow/dags/ dans le conteneur Airflow (bin/test).
for racine in (Path(__file__).resolve().parents[1], Path("/opt/airflow/dags")):
    if (racine / "src").is_dir() and str(racine) not in sys.path:
        sys.path.insert(0, str(racine))
