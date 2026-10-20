
# Stratégie CI/CD

Notre intégration continue repose sur GitHub Actions. À chaque push ou Pull Request :

1. **Linting** : `ruff` valide le formatage et les standards Python.
2. **Tests** : `pytest` vérifie la logique métier en isolation (fixtures).
3. **Build & Push** : Une image Docker multi-étapes sécurisée (non-root) est construite. Si le push a lieu sur `main`, l'image est poussée sur le registre ghcr.io avec un tag unique horodaté (`YYYYMMDDHHMMSS-sha`).
   La branche `main` reste ainsi perpétuellement déployable.
