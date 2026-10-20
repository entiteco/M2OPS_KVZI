
# Contribuer au projet

## Branches

`main` doit toujours fonctionner : on ne pousse jamais directement dessus (la branche est protégée).

1. Partir de `main` à jour : `git switch main && git pull`
2. Créer une branche par sujet : `git switch -c <type>/<sujet>`, par exemple `feat/collecte-rss` ou `fix/readme`.

Types : `feat` (fonctionnalité), `fix` (correction), `docs`, `test`, `chore` (config, ménage).

## Commits

Format : `type(périmètre): message court`, par exemple :

- `feat(collecte): première source RSS (L'Humanité) + tests`
- `fix(readme): identifiants Airflow`

## Avant de pousser

Lancer `./bin/test` (lint + tests). Chaque nouveau code arrive avec ses tests dans `tests/`.

## Pull Request et merge

1. Pousser la branche et ouvrir une Pull Request vers `main`.
2. La CI doit être verte et une autre personne de l'équipe doit approuver : sans ça, GitHub bloque le merge.
3. C'est l'auteur·e de la PR qui merge, une fois l'approbation obtenue, puis supprime la branche.
