FROM apache/airflow:2.8.1-python3.10 AS build

# gcc sert uniquement à compiler les dépendances : il reste dans cette étape
USER root
RUN apt-get update \
  && apt-get install -y --no-install-recommends gcc \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

USER airflow
COPY requirements*.txt /tmp/
RUN pip wheel --no-cache-dir -r /tmp/requirements.txt -w /tmp/wheels


FROM apache/airflow:2.8.1-python3.10

# L'image officielle Airflow utilise déjà l'utilisateur non-root 'airflow'
USER airflow
RUN mkdir -p /opt/airflow/.cache/huggingface
COPY requirements*.txt /tmp/
# Les wheels sont montés le temps de l'installation, pas copiés dans l'image
RUN --mount=type=bind,from=build,source=/tmp/wheels,target=/tmp/wheels \
  pip install --no-cache-dir --no-index --find-links=/tmp/wheels -r /tmp/requirements.txt

# Copie du code source dans le dossier des DAGs
COPY --chown=airflow:root src/ /opt/airflow/dags/src/
COPY --chown=airflow:root tests/ /opt/airflow/tests/
COPY --chown=airflow:root docs/sources.csv /opt/airflow/sources.csv
COPY --chown=airflow:root config/ /opt/airflow/dags/config/
