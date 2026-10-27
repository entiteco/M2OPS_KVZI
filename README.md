
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
- Grafana : http://localhost:3000 (admin/admin)

## Initialiser depuis les dumps

Avec `gazette.sql` et `bronze-json.zip` à la racine :

```bash
./bin/init
```

Cette commande démarre PostgreSQL et MinIO, restaure le SQL **si la base gazette
est vide**, applique les migrations, importe les JSON Bronze via l'API MinIO,
puis lance la stack. Si Silver contient déjà des articles (par exemple ceux du
dump SQL en révision `0002`), ils sont conservés ; sinon elle est régénérée depuis Bronze.
Les chemins Windows du ZIP sont pris en charge. Ne pas dézipper directement
dans le répertoire interne de MinIO.

Une relance conserve les tables existantes et les objets Bronze déjà présents.
Lorsqu'une régénération est nécessaire, le nettoyage relit tout le stock Bronze
et met à jour Silver par identifiant.
Lancer l'initialisation avant de démarrer les collectes ; si le scheduler tourne
déjà, l'arrêter avec `docker compose stop airflow-scheduler` avant `./bin/init`.
Les dumps et exports locaux sont ignorés par Git et exclus du build Docker.

Pour préparer un export Silver **sans Docker**, avec Python 3.10 ou plus :

```bash
python3 -m venv .venv
.venv/bin/python -m pip install minio==7.2.7 psycopg2-binary==2.9.9
.venv/bin/python -m src.stockage.restaurer
```

Sorties dans `data/restauration/` : `articles_propres.jsonl`, `rejets.jsonl`,
`qualite.md` et `bilan.json`. Cet export utilise les mêmes règles que le DAG,
sans écrire dans PostgreSQL ou MinIO. Options : `--archive chemin.zip` et
`--sortie dossier`. Les dates historiques de collecte/publication sont conservées.

## Tests

Pour une petite machine, lancer `./bin/dev --light` et `./bin/test --light`.
Ce profil limite les ressources et garde Grafana facultatif. Le démarrage de
Docker reste manuel. Voir [docs/exploitation.md](docs/exploitation.md) pour les
mesures mémoire, les sauvegardes et le fonctionnement sur plusieurs jours.

```bash
./bin/test
```

Lance le lint (ruff) puis les tests (pytest) dans le conteneur Airflow, comme la CI.

## Collecte automatique

Le DAG Airflow `collecte_rss` (`src/dags/collecte_rss.py`) collecte toutes les sources **toutes les 30 minutes**, dès `./bin/dev`, sans rien activer à la main. Il tourne tant que la machine et Docker restent allumés.

- Suivi : http://localhost:8080, DAG `collecte_rss`. Le journal de la tâche contient une ligne JSON par source.
- Un passage **rouge** signale qu'une source vient d'être mise en sommeil (3 échecs d'affilée).
- Bilan (articles par source, sources en sommeil) :

```bash
docker compose exec airflow-scheduler bash -c "cd /opt/airflow/dags && python -m src.stockage.bilan"
```

## Lancer une collecte à la main

```bash
docker compose exec airflow-scheduler bash -c "cd /opt/airflow/dags && python -m src.collecte.collecteur"
```

Passe sur toutes les sources actives de `docs/sources.csv` et écrit les nouveaux items dans MinIO (`bronze/articles_bruts/`, console sur http://localhost:9001). Le détail des données est dans [docs/donnees.md](docs/donnees.md).

## Thèmes du jour (TD 5)

Après chaque nettoyage réussi, Airflow lance `produire_themes` : embeddings CPU
en cache, regroupement BERTopic en dix grands thèmes au maximum et nommage
général à partir des mots-clés et des descriptions éditoriales. Un titre
d'article représentatif est conservé séparément.
Les thèmes et leurs articles sont reliés à un run dans PostgreSQL ; les entrées,
paramètres, métriques et résultats sont archivés dans MinIO (`mlops`).
Les réglages sont dans `config/clustering.yaml` et les explications/commandes
dans [docs/mlops.md](docs/mlops.md).
Les résultats sur les fenêtres des 22, 23 et 27 octobre sont dans
[docs/validation-grands-themes.md](docs/validation-grands-themes.md).

Un bilan de fin de pipeline peut être envoyé dans Teams : renseigner
`TEAMS_WEBHOOK_URL` et `GAZETTE_ENV` dans `.env`, puis recréer les conteneurs.
Voir [docs/notifications.md](docs/notifications.md) pour les conversations privées,
les canaux et les compteurs envoyés.

## Contribuer

Une branche par sujet, une Pull Request vers `main` et une CI verte avant de merger. Les règles sont dans [CONTRIBUTING.md](CONTRIBUTING.md).
