FROM apache/airflow:2.8.1-python3.10

# L'image officielle Airflow utilise déjà l'utilisateur non-root 'airflow'
USER root
RUN apt-get update \
  && apt-get install -y --no-install-recommends gcc \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

USER airflow
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copie du code source dans le dossier des DAGs
COPY --chown=airflow:root src/ /opt/airflow/dags/src/
COPY --chown=airflow:root tests/ /opt/airflow/tests/