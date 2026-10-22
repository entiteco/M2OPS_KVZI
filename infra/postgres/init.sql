-- Exécuté par l'image postgres au premier démarrage (volume vide).
-- Base des données de la gazette, séparée de la base interne d'Airflow.
CREATE USER gazette WITH PASSWORD 'gazette';
CREATE DATABASE gazette OWNER gazette;
-- Base jetable pour les tests (bin/test)
CREATE DATABASE gazette_test OWNER gazette;
