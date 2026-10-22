
# La Gazette - Projet M2Ops

Pipeline automatisé de lecture, stockage et synthèse thématique de la presse quotidienne.

## Prérequis

- Docker (avec Docker Compose)
- Git (sous Windows, lancer les scripts depuis Git Bash)

## Lancement rapide

```bash
git clone https://github.com/entiteco/M2OPS_KVZI.git && cd M2OPS_KVZI
./bin/dev
```

Services exposés :

- Airflow : http://localhost:8080 (airflow/airflow)
- MinIO : http://localhost:9001 (minioadmin/minioadmin)

## Tests

```bash
./bin/test
```

Lance le lint (ruff) puis les tests (pytest) dans le conteneur Airflow, comme la CI.

## Lancer une collecte à la main

```bash
docker compose exec airflow-scheduler bash -c "cd /opt/airflow/dags && python -m src.collecte.collecteur"
```

Passe sur toutes les sources actives de `docs/sources.csv` et écrit les nouveaux items dans MinIO (`bronze/articles_bruts/`, console sur http://localhost:9001). Le détail des données est dans [docs/donnees.md](docs/donnees.md).

## Contribuer

Une branche par sujet, une Pull Request vers `main` et une CI verte avant de merger. Les règles sont dans [CONTRIBUTING.md](CONTRIBUTING.md).
