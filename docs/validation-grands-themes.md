# Validation des grands thèmes — 27 octobre 2026

La remarque de l'enseignant change le niveau de lecture attendu : une dizaine de
grands sujets du jour, plutôt que cinquante petits groupes d'événements. Les
essais précédents restent décrits dans [mlops-experiences.md](mlops-experiences.md).

## Méthode retenue

Un seul modèle multilingue, une seule chaîne BERTopic, sans fine-tuning :

1. Embeddings normalisés des titres et extraits, avec le cache existant.
2. UMAP (30 voisins, cinq dimensions) et HDBSCAN (`min_cluster_size=20`,
   `min_samples=3`, sélection `eom`).
3. Si plus de dix groupes sont trouvés, réduction BERTopic fondée sur leurs
   représentations sémantiques. Dix est un plafond : aucun groupe artificiel
   n'est ajouté si le regroupement en trouve moins.
4. Réaffectation des articles sans groupe uniquement avec une similarité >= 0,45
   à un groupe existant. Des articles peuvent toujours rester sans thème.
5. Mots-clés c-TF-IDF et nom général choisi parmi des libellés éditoriaux décrits
   dans `config/libelles_themes.yaml`. Le choix combine similarité des embeddings
   et couverture des mots-clés. Ces libellés n'influencent pas le regroupement.
   En cas de score trop faible, le titre représentatif reste le nom de secours.

Le nom, la méthode, le score et le titre illustratif sont conservés en base et
dans les artefacts. Le titre illustratif est repris d'un article réel ; le nom
général provient d'une liste éditoriale explicite. Aucun LLM ne génère de texte.
Les libellés peuvent être révisés avec leur description et leurs mots-clés, en
conservant la version de configuration de chaque run. Le score n'est pas une
probabilité de justesse du nom.

## Comparaisons sur des instantanés figés

| Fenêtre / source | Articles | Thèmes | Sans thème | Couverture |
|---|---:|---:|---:|---:|
| 22 octobre, 00 h à 24 h UTC | 799 | 10 | 86 | 89,2 % |
| 22 octobre 14:29 au 23 octobre 14:29 UTC | 647 | 10 | 74 | 88,6 % |
| 27 octobre, fenêtre de 24 h terminant à 18:30 UTC | 382 | 6 | 96 | 74,9 % |

Les deux premières fenêtres se recouvrent partiellement ; elles ne constituent
pas deux tests indépendants. La troisième apporte des données d'une autre
journée. Les premiers chiffres sont calculés sur les entrées archivées, pas sur
une requête changeante pendant la comparaison.

Les variantes à petits groupes `leaf` ramenaient systématiquement dix thèmes,
mais créaient aussi des ensembles peu cohérents sur la fenêtre du 27 octobre
(sport mélangé à des sujets sans rapport, par exemple). Elles ont été écartées
malgré une silhouette parfois supérieure et une meilleure couverture.

Sur le 22 octobre, une réduction fondée uniquement sur le c-TF-IDF donnait un
groupe de 383 articles et une silhouette proche de zéro : elle a également été
écartée. La cohérence et la lisibilité passent avant le nombre exact de groupes
ou l'optimisation d'un seul score.

## Exemples de lecture

Sur une exécution historique de contrôle à 674 articles, les dix noms couvrent
les mobilisations sociales, la culture et les sorties, le sport, la littérature,
les faits divers, les technologies, les relations internationales, la météo et
la justice. Deux angles voisins peuvent recevoir le même libellé principal ;
des mots-clés permettent alors de les distinguer. Le titre d'un seul joueur de
rugby ne sert plus de nom à tout le groupe sport.

La sélection d'un libellé uniquement par embedding confondait parfois météo et
transports. L'appui des mots-clés corrige ce cas dans la fenêtre examinée. Des
erreurs de noms ou des mélanges restent possibles : il ne s'agit pas d'une
évaluation éditoriale exhaustive.

## Traces

Sources :

- `themes-40e26ded5aab4f0883e049f5d9c227fb` : instantané de 799 articles ;
- `themes-3d2e310119f1419f9a5574a992ddd5fe` : instantané de 647 articles ;
- `themes-d2ae80ebe86b48cdb70ad75c2d75fef9` : passage automatique à 382 articles.

Comparaisons dans MinIO (`mlops/experiences/`) :

- `comparaison-6e38b8f7814645479308d87c00313d16` ;
- `comparaison-6160f8b0826749a488687b14570b0596` ;
- `comparaison-dce5e9519cfa49fc9cf351dbf1f32a1b` ;
- `comparaison-c891a7c8d89d4dd3b8d88053f4f7f4f9` pour les variantes `leaf` du 27.

Rejouer seulement les comparaisons de grands thèmes :

```bash
docker compose -f docker-compose.yml -f docker-compose.light.yml run --rm --no-deps --entrypoint bash airflow-scheduler -ec 'cd /opt/airflow/dags && python -m src.themes.experiences --source-run themes-d2ae80ebe86b48cdb70ad75c2d75fef9 --filtre macro'
```

Ces expériences ne publient pas de thèmes courants et n'envoient pas une carte
Teams par variante. L'exploitation continue est décrite dans
[exploitation.md](exploitation.md).

## Vérification finale du pipeline local

`validation-grands-themes-20261027` : collecte, nettoyage, thèmes et notification
Teams en succès. Run ML `themes-eecedcef3003408bb74d8a44defac239` : 390 articles,
6 thèmes, 47 articles sans groupe (12,1 %), 382 vecteurs réutilisés et 8 calculés.
Les chiffres diffèrent de l'instantané à 382 articles : l'entrée a évolué.
Le regroupement reste sensible aux petits jeux de données ; sa stabilité doit
être examinée pendant l'observation sur plusieurs jours.

Lint et 91 tests réussis, un test réseau optionnel ignoré. Le vrai modèle a été
chargé et vérifié séparément sur dix textes dans le conteneur du profil léger.
Les quatre services permanents sont sains. Docker, son socket et containerd
sont toujours désactivés au démarrage du poste. Aucun déploiement VM n'a été fait.
