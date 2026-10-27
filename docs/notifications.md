# Bilans Teams du pipeline

La tâche Airflow `notifier_bilan` attend la fin de la collecte, du nettoyage et
des thèmes. Elle envoie une carte à Teams, en succès comme en échec, avec :

- environnement (`local`, `production`…), identifiant et durée du pipeline ;
- sources consultées, sources en erreur et mises en sommeil ;
- articles reçus des flux, nouveaux articles Bronze et doublons ignorés ;
- stock Bronze contrôlé, articles gardés et rejets du nettoyage ;
- articles des dernières 24 h analysés, thèmes, bruit et identifiant du run ML ;
- étapes non réussies, le cas échéant.

Les compteurs de collecte et de nettoyage sont conservés dans XCom avant les
alertes métier. Un compteur absent après un plantage est affiché « Indisponible »
et non zéro. Le nettoyage relit le stock : ses compteurs ne désignent pas
uniquement les nouveaux articles. Des erreurs partielles de sources peuvent
produire un avertissement même si les tâches terminent avec succès.
Une fenêtre de 24 h sans article récent est également signalée comme
avertissement, pour distinguer un pipeline fonctionnel d'une collecte fraîche.

## Configuration locale ou production

Dans Teams > Workflows, créer **Send webhook alerts to a channel** pour un canal
d'équipe, ou **Send webhook alerts to a chat** pour une conversation privée de
groupe. Choisir le modèle sans authentification interactive de l'appelant.
Ces possibilités dépendent des politiques de l'organisation.

Référence officielle : [webhooks Workflows, conversations et canaux](https://support.microsoft.com/en-gb/workflows/send-messages-in-teams-using-incoming-webhooks).

Copier `.env.example` vers `.env` et renseigner :

```dotenv
TEAMS_WEBHOOK_URL=URL_FOURNIE_PAR_TEAMS
GAZETTE_ENV=local
```

Le fichier `.env` est ignoré par Git et exclu du build Docker. L'URL ne doit pas
être publiée dans une PR, un journal ou une capture. En production, injecter ces
variables avec la configuration de déploiement en utilisant `GAZETTE_ENV=production`.
Après changement, recréer les conteneurs pour actualiser leurs variables :

```bash
docker compose up -d airflow-scheduler airflow-webserver
```

Une URL vide désactive l'envoi sans bloquer le pipeline. Le message utilise le
format Adaptive Card 1.4 et inclut uniquement des compteurs et identifiants.
Les demandes HTTPS ont un délai borné et trois tentatives au maximum pour les
erreurs réseau, HTTP 429 ou HTTP 5xx. Une erreur permanente ou persistante rend
la tâche de notification rouge ; elle ne relance pas les traitements de données.
Un délai réseau après acceptation peut entraîner un doublon à la tentative
suivante : l'identifiant du pipeline permet de le reconnaître.

La tâche finale préserve les échecs des étapes précédentes : une carte envoyée
avec succès ne transforme pas un pipeline en échec en pipeline vert. L'envoi
est limité aux passages Airflow ; les scripts de diagnostic et les expériences
de paramètres n'envoient pas chacun une notification.

## Première validation locale

Pipeline `validation-teams-20261023` : quatre tâches en succès, résultat de
`notifier_bilan` : `{"statut": "envoye", "pipeline": "succes"}`. Cela confirme
l'acceptation HTTP par le webhook ; l'affichage dans Teams dépend ensuite du
bon fonctionnement du Workflow configuré.
