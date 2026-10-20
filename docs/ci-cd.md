
# Stratégie CI/CD

Notre intégration continue repose sur GitHub Actions. À chaque push ou Pull Request :

1. **Linting** : `ruff` valide le formatage et les standards Python.
2. **Tests** : `pytest` vérifie la logique métier en isolation (fixtures).
3. **Build & Push** : Une image Docker multi-étapes sécurisée (non-root) est construite. Si le push a lieu sur `main`, l'image est poussée sur le registre ghcr.io avec un tag unique horodaté (`YYYYMMDDHHMMSS-sha`).
   La branche `main` reste ainsi perpétuellement déployable.

L'image est construite en deux étapes : la première compile les dépendances (avec `gcc`), la seconde ne garde que les paquets installés. L'image finale ne contient pas les outils de compilation.

`main` est protégée sur GitHub : pas de push direct, une Pull Request et la CI `build-and-test` verte sont obligatoires pour merger. On a vérifié qu'un test cassé rend la CI rouge et bloque le merge.

L'approbation d'un·e relecteur·rice n'est pas imposée par GitHub : on l'a retirée pour ne pas bloquer l'équipe quand personne n'est disponible. La CI reste le garde-fou obligatoire, la relecture se fait à la demande.

Pas de déploiement automatique pour l'instant (prévu au TD 7).
