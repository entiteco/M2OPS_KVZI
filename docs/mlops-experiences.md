# Exploration du regroupement et du nommage — 23 octobre 2026

## Protocole

Entrée figée : run `themes-3d2e310119f1419f9a5574a992ddd5fe`, 647 articles,
11 sources, fenêtre terminant le 23 octobre à 14:29:41.830697 UTC.
Les JSON d'entrée et les embeddings sont chargés depuis les artefacts MinIO
et vérifiés par SHA-256. Aucun article des collectes suivantes n'entre dans
cette comparaison. Le modèle d'embeddings et sa révision restent identiques.

38 variantes de paramètres ont été explorées : UMAP plus local, dimensions
différentes, HDBSCAN `leaf`/`eom`, tailles minimales, vecteurs sans projection,
titre seul, combinaison sémantique/lexicale et seuils de réaffectation du bruit.
Les essais successifs incluent des variantes répétées pour conserver les
comparaisons complètes ; un essai ayant produit une erreur de sérialisation
d'entier NumPy a été tracé en échec, corrigé puis relancé.

Les critères examinés sont la taille des groupes, la couverture, la silhouette
cosinus dans les embeddings sémantiques d'origine et une lecture d'échantillons
(tempête, Trappes, Huchon, Sécu, sport, décès). La silhouette ne détermine pas à
elle seule le choix. Les repérages par noms dans les titres servent de sondes ;
ce ne sont pas des annotations de référence ni une mesure de précision.

## Résultats sur les 647 mêmes articles

| Variante | Thèmes | Taille max. | Sans thème | Silhouette |
|---|---:|---:|---:|---:|
| Initiale : UMAP 15 voisins, 5 dimensions, HDBSCAN 5/3 | 38 | 49 | 22,7 % | 0,129 |
| UMAP 5 voisins, mêmes autres réglages | 49 | 28 | 11,6 % | 0,102 |
| UMAP 5 voisins, 15 dimensions, HDBSCAN leaf 4/2 | 76 | 18 | 18,1 % | 0,117 |
| Titre seul, UMAP 5 voisins, HDBSCAN 4/2 | 67 | 25 | 9,6 % | 0,087 |
| Vecteurs originaux, HDBSCAN 3/1 | 46 | 22 | 57,8 % | 0,293 |
| Vecteurs + 20 % lexical, sans projection, HDBSCAN 3/1 | 53 | 19 | 55,5 % | 0,282 |
| Même configuration, réaffectation à 0,50 | 53 | 25 | 43,1 % | 0,225 |
| **Même configuration, réaffectation à 0,55 — retenue** | **53** | **22** | **48,5 %** | **0,253** |

Le réglage retenu privilégie la séparation au prix d'une couverture plus faible :
333 articles regroupés, 314 sans thème. Cette perte de couverture est explicite,
et les articles non regroupés ne sont pas supprimés.

### Observations

- Les 14 titres mentionnant explicitement Trappes/La Verrière sont réunis dans
  un groupe, contre deux groupes et un article sans groupe au départ. Le groupe
  compte 22 articles au total ; ces chiffres ne prouvent pas que tous ses membres
  sont pertinents. Des articles parasites restent possibles.
- Les six articles sur Huchon et les six titres repérés sur le budget de la Sécu
  restent chacun regroupés ensemble.
- Le groupe sport de 49 articles ne reste plus un seul grand ensemble ; une
  partie de ses articles reste sans thème faute de groupe assez dense.
- La tempête reste répartie entre un groupe principal et des angles secondaires
  (notamment les transports). Les réglages `leaf` très fins fragmentaient encore
  davantage cet événement, malgré leurs groupes plus petits.
- Le seuil 0,50 récupère davantage d'articles, mais réintroduit par exemple un
  fait divers de Nice dans le groupe de la fusillade de Trappes. Le seuil 0,55
  est le compromis prudent retenu pour cette première journée.

Ce choix est provisoire et n'est pas validé sur une journée indépendante. Les
titres techniques encore en Silver et les petits événements isolés restent des
limites connues. Les paramètres ne sont pas ajustés à partir du nom d'un sujet
particulier : aucune règle « Trappes », « Austen » ou « sport » n'est codée.

## Nommage

Le nom reste extrait d'un titre réel. Parmi les titres proches du centre, le
score favorise ceux qui couvrent les mots-clés et pénalise les très longs titres.
Le préfixe éditorial est retiré sans enlever le lieu ou le sujet. Une phrase
n'est jamais coupée pour atteindre une longueur arbitraire.

Exemple de nom sélectionné sur le groupe Trappes :
« Yvelines. Un mort et au moins quatre blessés : ce que l'on sait après la
fusillade dans la rue à Trappes ».

Sur les 53 groupes retenus, la longueur moyenne passe d'environ 119 à 113
caractères. C'est une amélioration modeste de lisibilité ; elle ne garantit pas
qu'un titre particulier couvre tous les articles du groupe.

## Où retrouver et reproduire les essais

Dans MinIO, bucket `mlops`, notamment :

- `experiences/comparaison-88dbb5d0bae74e74a68a7d7f10caecd5/` : comparaison élargie ;
- `experiences/comparaison-58ab73c09d194931996bc97f3dc0e71a/` : seuils de réaffectation.

Chaque comparaison conserve l'entrée, les vecteurs, le code, les versions et
pour chaque variante sa configuration, ses affectations, ses thèmes et ses
métriques. Le bilan contient aussi les erreurs. Les résultats locaux de cette
session sont dans `data/experiences/` (ignorés par Git).

```bash
docker compose exec airflow-scheduler bash -ec 'cd /opt/airflow/dags && python -m src.themes.experiences --source-run themes-3d2e310119f1419f9a5574a992ddd5fe'
```

Pour limiter aux seuils : ajouter `--filtre reaffectation`. Le script ne modifie
pas les thèmes courants et n'envoie pas de carte Teams par essai. Le réglage
retenu est appliqué dans `config/clustering.yaml`, puis utilisé automatiquement
par le pipeline normal, dont chaque run reste tracé séparément.

## Vérification après activation

Run réel `themes-261d62ad16924ba4aabf28c8aa19e133` : 658 articles de la fenêtre
courante, 52 thèmes, 331 articles sans thème (50,3 %), silhouette 0,263.
48 articles ont été rattachés à un groupe lors de la seconde étape.
Ce run n'est pas directement comparable à l'instantané de 647 articles : la
collecte et la fenêtre ont évolué. Les nouveaux noms sont présents en base.
Lint et 85 tests réussis ; le test optionnel qui télécharge le modèle n'a pas
été relancé, le modèle et son encodeur étant inchangés dans la configuration
retenue.

Validation de bout en bout : pipeline Airflow `validation-affinage-20261023`,
quatre tâches en succès, notification Teams comprise. Le run ML associé
`themes-afa9dfd8d3ef4902a55611f49bd6aca9` traite la fenêtre courante (670
articles) : 54 thèmes, 338 articles sans groupe et silhouette 0,2654.
