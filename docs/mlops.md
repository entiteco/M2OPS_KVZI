# Thèmes du jour — TD 5

Après le nettoyage, la tâche Airflow `produire_themes` lit `titre + extrait` des
articles publiés dans `[fin du passage - 24 h, fin du passage[`. Les publications
sans date sont exclues. Les dates de récupération ne remplacent pas une date de
publication absente. L'heure de référence est `data_interval_end` d'Airflow,
en UTC ; elle est conservée avec chaque run.

## Choix et limites

- **Embeddings** : `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`,
  révision exacte `e8f8c211226b894fcb81acc59f3b34ba3efd5f42`, sur CPU.
  Chaque texte produit 384 valeurs normalisées. Limite de 128 tokens : le modèle
  peut tronquer les longs titres/extraits. Aucun fine-tuning, aucune API payante.
- **BERTopic 0.16.4** : UMAP (30 voisins, cinq dimensions, graine 42), HDBSCAN
  (`min_cluster_size=20`, `min_samples=3`), puis réduction à dix grands thèmes
  au maximum. Les groupes proches sont fusionnés selon leur représentation
  sémantique. Si moins de dix groupes sont trouvés, on les conserve. Les articles
  sans groupe ne sont réaffectés qu'avec une similarité >= 0,45. Les lots de moins
  de 20 articles restent sans thème avec ces réglages. Un lot vide est tracé.
- **Nommage** : choix d'un libellé général à partir des embeddings et des
  mots-clés du groupe, parmi les descriptions de `config/libelles_themes.yaml`.
  Ces descriptions servent uniquement au nommage ; elles ne classent pas les
  articles et ne forcent pas les groupes. Un titre représentatif est conservé
  séparément avec son article et sa centralité. Il sert aussi de nom de secours
  si aucun libellé n'est suffisamment étayé. Les noms ne sont pas générés par un
  LLM. Les mots-clés français conservent leurs accents ; nombres et mots de date
  génériques sont écartés de la représentation c-TF-IDF.
- **Suivi** : tables PostgreSQL et fichiers MinIO, adaptés aux services déjà en
  place. MLflow faciliterait une interface de comparaison mais ajouterait un
  service ; des journaux seuls ne permettraient pas de relier les thèmes à leur
  entrée exacte. Le suivi est systématique, y compris en cas d'échec.

Alternatives de regroupement : K-means impose un nombre de thèmes et affecte
tous les articles ; HDBSCAN seul exige d'assembler le nommage séparément.
BERTopic fournit déjà cette chaîne. Ces alternatives ne sont pas exécutées dans
le pipeline et aucune comparaison expérimentale avec elles n'est revendiquée.

Les paramètres sont dans [config/clustering.yaml](../config/clustering.yaml),
les mots vides français dans [config/mots_vides_fr.txt](../config/mots_vides_fr.txt).
Le nom du modèle et sa révision, les bibliothèques ML principales et PyTorch CPU
sont figés. Le premier passage télécharge les poids, conservés dans le volume
Docker `model-cache`. Il nécessite l'accès à Hugging Face. Les passages suivants
réutilisent les poids locaux et les embeddings déjà en base.

Le choix actuel et ses résultats sont décrits dans
[validation-grands-themes.md](validation-grands-themes.md). Les premières
explorations vers des groupes fins restent dans
[mlops-experiences.md](mlops-experiences.md). La comparaison utilise exactement
l'instantané et les vecteurs d'un run précédent, pas une fenêtre glissante qui
changerait entre deux essais. Les essais sont archivés sous `mlops/experiences/`
et ne remplacent pas les thèmes courants.

## Cache et historique

`embeddings` est indexée par empreinte du texte exact, modèle, révision et
empreinte des options de vectorisation. Une correction de titre/extrait, un
changement de modèle ou de longueur maximale invalide l'entrée correspondante.
Deux articles au texte identique peuvent réutiliser le même vecteur. Le cache
est indépendant des runs : une relance crée un nouveau run sans recalculer les
textes identiques.

`runs` contient : statut (`en_cours`, `succes`, `echec`), déclencheur Airflow ou
manuel, fenêtre UTC, nombre et hash des articles, configuration effective,
versions Python/bibliothèques, empreinte SHA-256 du code source, métriques,
liens et checksums des artefacts, dates et erreur éventuelle.

`themes` contient `(run_id, theme_id, nom, mots_cles, taille,
article_representant, titre_representant, nommage)`. Un identifiant de thème est local à un run : le thème 0
d'aujourd'hui ne désigne pas nécessairement celui d'hier.

`articles_themes` contient une ligne pour chaque article de l'entrée, avec
`theme_id = NULL` pour le bruit. Les articles restent en Silver. Ces identifiants
ne bloquent pas une future purge de Silver ; les textes historiques sont
conservés dans l'artefact d'entrée.

Les thèmes, affectations et le succès du run sont publiés dans une transaction
unique, après l'archivage. `themes_courants` sélectionne le run réussi de la
fenêtre la plus récente, même s'il n'a aucun thème. Un rejeu historique ne
remplace pas une fenêtre plus récente. Un échec ne remplace pas les résultats du
dernier succès. Un verrou PostgreSQL empêche deux regroupements simultanés.

Un processus brutalement tué peut laisser un run `en_cours` : ce statut ne
désigne jamais un résultat publié. Vérifier alors l'état de la tâche Airflow et
son journal. Les exceptions ordinaires sont enregistrées en `echec`, puis
remontées à Airflow.

## Où regarder

- Airflow : <http://localhost:8080>, DAG `collecte_rss`, tâche `produire_themes`.
  Elle s'exécute après chaque nettoyage réussi, toutes les 30 minutes : cela
  couvre le fonctionnement quotidien demandé. Un nettoyage en échec la bloque.
- MinIO : <http://localhost:9001>, bucket `mlops`, préfixe
  `runs/YYYY-MM-DD/<run_id>/`.
- PostgreSQL : base `gazette`, tables ci-dessus et vue `themes_courants`.

Les artefacts de chaque run sont `entree.json` (textes et provenance),
`config.json` (incluant les mots vides), `environnement.json`, `code.json`
(instantané des sources Python), `embeddings.npy`
(lignes dans l'ordre d'`entree.json`), `themes.json`, `affectations.json`,
`metriques.json`, `parametres_effectifs.json`, `run.json` et `modele/`.
Quand les libellés sont utilisés, `libelles_embeddings.npy` conserve aussi leurs
vecteurs dans l'ordre de la configuration. Les descriptions et mots-clés de
nommage sont intégralement présents dans `config.json`.
`run.json` référence les checksums des autres artefacts ; sa propre empreinte
est enregistrée dans PostgreSQL. Les petits lots n'ont pas de modèle entraîné.

Le modèle BERTopic est exporté en **safetensors**, avec le c-TF-IDF. Cet export
léger ne conserve pas les estimateurs UMAP/HDBSCAN : le recharger pour affecter
de nouveaux articles utilise une autre procédure. Pour reproduire le
regroupement initial, réexécuter avec l'entrée, les vecteurs, les paramètres et
les versions archivés. La reproductibilité numérique entre matériels et versions
différents n'est pas garantie. Les fichiers NPY sont sans pickle.

Afficher les derniers runs et les thèmes courants :

```bash
docker compose exec postgres psql -U gazette -d gazette
```

```sql
SELECT id, statut, reference, nb_articles, metriques, erreur
FROM runs ORDER BY commence_le DESC LIMIT 10;

SELECT run_id, theme_id, nom, taille, mots_cles
FROM themes_courants ORDER BY taille DESC;

SELECT a.article_id, a.theme_id, t.nom
FROM articles_themes a
LEFT JOIN themes t USING (run_id, theme_id)
WHERE a.run_id = 'REMPLACER_PAR_LE_RUN_ID';
```

## Métriques et lecture humaine

- Nombre de thèmes et taille médiane : repérer une fragmentation excessive ou
  un seul grand groupe qui mélange des sujets.
- Part et nombre d'articles sans thème : bruit, sans suppression de l'article.
- Silhouette : distance cosinus dans les embeddings originaux, bruit exclu,
  échantillon déterministe de 2 000 articles maximum. `NULL` avec une raison si
  moins de deux groupes, uniquement des singletons ou échantillon inexploitable.
- Nombre de vecteurs calculés et d'articles servis depuis le cache.

Une bonne silhouette ne prouve pas une bonne qualité éditoriale. Au TD 6,
relire deux journées : vérifier la cohérence des articles de chaque groupe,
les événements séparés à tort, les thèmes fusionnés et la pertinence du titre
choisi. Ne pas interpréter deux passages de la même journée comme deux journées.

## Lancer et vérifier

Après mise à jour de l'image et des migrations :

```bash
./bin/dev
./bin/test
```

Le pipeline déclenche les thèmes automatiquement. Pour un diagnostic ou rejouer
une fenêtre historique explicitement :

```bash
docker compose exec airflow-scheduler bash -ec 'cd /opt/airflow/dags && python -m src.themes.passage --reference 2026-10-23T13:00:00+00:00'
```

Un test avec le vrai modèle sur dix articles vérifie la dimension, la
normalisation et la réutilisation intégrale du cache. Il télécharge les poids
si nécessaire et utilise uniquement `gazette_test` :

```bash
docker compose run --rm -e GAZETTE_TEST_MODELE=1 --entrypoint bash airflow-scheduler -ec 'pytest tests/test_themes.py -k modele_reel'
```

Les tests habituels n'exigent pas de téléchargement de poids : ils vérifient le
cache sur dix textes, son invalidation, le nommage, les fenêtres temporelles,
BERTopic sur des groupes synthétiques, les runs vides et les erreurs de calcul.

## Observations des journées

À compléter après lecture humaine, sans inventer de résultats :

| Journée UTC | Run examiné | Groupe cohérent | Groupe problématique | Hypothèse |
|---|---|---|---|---|
| À renseigner | | | | |

## Première exécution vérifiée — 23 octobre 2026

Fenêtre `[2026-10-22T14:12:26.378339Z, 2026-10-23T14:12:26.378339Z[`.
Run initial : `themes-396d6f682e7541da9240e485d38734a9`.
Relance : `themes-c098b232209a49dea301a1931f6bdbee`.

- 636 articles, 38 thèmes, taille médiane 10, 116 articles sans groupe (18,24 %).
- Silhouette cosinus hors bruit : 0,123 ; ce score appelle une lecture humaine.
- Premier passage : 631 textes uniques encodés pour 636 articles.
- Relance à heure de référence identique : 636 articles servis depuis le cache,
  aucun vecteur recalculé, mêmes affectations et mêmes thèmes (checksums vérifiés).
- Test séparé du vrai modèle sur dix articles : dimensions `(10, 384)`, normes
  unitaires et deuxième appel intégralement servi depuis le cache.
- Vérification Docker : lint réussi, 73 tests habituels réussis ; le test avec
  téléchargement du vrai modèle est ignoré dans cette suite et a réussi lors
  d'une exécution séparée explicite.

Chaîne complète validée dans Airflow avec `td5-validation-20261023` : collecte,
nettoyage et `produire_themes` en succès. Le run associé
`themes-261bbf7c6900431ebabcab5bdcb603e5`, référence `2026-10-23T14:00:00Z`,
traite 667 articles : 40 thèmes, 148 articles sans groupe, silhouette 0,1314,
636 articles servis depuis le cache et 31 nouveaux textes encodés. Le scheduler
reste actif pour les passages suivants.

Première observation humaine, limitée à quelques articles du thème 0 : le groupe
réunit football, rugby, basket et handball ; son titre représentatif porte sur
le Fenix Handball. Le groupe semble cohérent au niveau « sport » mais trop large
au niveau d'un événement, et le titre trop spécifique pour le couvrir. Hypothèse
à tester au TD 6 : les représentations et paramètres actuels privilégient la
proximité thématique générale. Il ne s'agit pas d'une évaluation complète ni de
deux journées relues.
