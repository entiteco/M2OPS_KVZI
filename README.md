
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

## Collecter une source

```bash
python -m src.collecte.rss
```

Lit le flux RSS de L'Humanité et écrit les items dans `data/collecte/` (nécessite Python 3.10+ avec `feedparser` et `requests`).

## Contribuer

Une branche par sujet, une Pull Request vers `main`, une relecture et une CI verte avant de merger. Les règles sont dans [CONTRIBUTING.md](CONTRIBUTING.md).
