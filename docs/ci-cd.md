
# Stratégie CI/CD

Notre intégration continue repose sur GitHub Actions. À chaque push ou Pull Request :

1. **Linting** : `ruff` valide le formatage et les standards Python.
2. **Tests** : `pytest` vérifie la logique métier en isolation (fixtures).
3. **Build & Push** : Une image Docker multi-étapes sécurisée (non-root) est construite. Si le push a lieu sur `main`, l'image est poussée sur le registre ghcr.io avec un tag unique horodaté (`YYYYMMDDHHMMSS-sha`).
   La branche `main` reste ainsi perpétuellement déployable.

L'image est construite en deux étapes : la première compile les dépendances (avec `gcc`), la seconde ne garde que les paquets installés. L'image finale ne contient pas les outils de compilation.

`main` est protégée sur GitHub : pas de push direct, une Pull Request avec une approbation et la CI `build-and-test` verte sont obligatoires pour merger. On a vérifié qu'un test cassé rend la CI rouge et bloque le merge.

Pas de déploiement automatique pour l'instant (prévu au TD 7).
