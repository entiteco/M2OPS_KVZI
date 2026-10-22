# Données

Début du dictionnaire de données. Il sera complété à chaque TD (zones Silver et Gold).

## Zone Bronze : `articles_bruts/` (MinIO)

Conformément à l'architecture, la zone Bronze est dans MinIO (bucket `bronze`). Chaque item reçu d'un flux est écrit tel quel dans un fichier JSON :

```
bronze/articles_bruts/<source>/<id>.json      ex. bronze/articles_bruts/le-monde/3f9c0a1b2d4e5f60.json
```

Les fichiers sont visibles dans la console MinIO : http://localhost:9001.

| Champ | Type | Description |
|---|---|---|
| `id` | texte (16 car.) | Empreinte SHA-256 de `(source, lien)`, tronquée. Sert de nom de fichier |
| `source` | texte | Nom de la source, tel que dans la table `sources` |
| `lien` | texte (URL) | Lien vers l'article chez l'éditeur |
| `titre` | texte | Titre de l'article, HTML retiré |
| `resume` | texte | Extrait fourni par le flux (`description` en RSS, `summary` en Atom), HTML retiré |
| `publie_le` | date ISO 8601 UTC ou `null` | Date de publication (`pubDate` en RSS, `published` / `updated` en Atom) |
| `recupere_le` | date ISO 8601 UTC | Moment où la collecte a lu l'item |
| `rubrique` | texte ou `null` | Première catégorie du flux (`category`), quand il y en a une |
| `payload` | objet | L'item tel que reçu (parsé par feedparser), **sans** le texte intégral (`content`), les images (`media_*`) ni l'auteur |

**Pas de doublon.** La clé naturelle est `(source, lien)` : le `guid` n'est pas fiable partout. Le nom du fichier est calculé à partir de cette clé : si le fichier existe déjà, l'item n'est pas réécrit. Lancer la collecte deux fois ne crée donc aucun doublon.

**Bornage.** On garde titres, extraits, liens, dates et rubriques. Jamais le texte intégral, les images, les commentaires ni de données personnelles (les auteurs sont retirés du `payload`).

## Table `sources` (PostgreSQL, base `gazette`)

Créée par une migration versionnée (Alembic, `src/stockage/migrations/`), appliquée automatiquement au démarrage (`airflow-init`). Elle est remplie à partir de `docs/sources.csv` : une ligne avec deux flux (Les Échos) donne deux sources.

| Champ | Type | Description |
|---|---|---|
| `nom` | texte, clé primaire | Nom de la source |
| `type` | `PQN` ou `PQR` | Presse nationale ou régionale |
| `url_flux` | texte (URL) | Adresse du flux RSS / Atom |
| `actif` | booléen | `false` = source en sommeil, elle n'est plus collectée |
| `derniere_reussite` | horodatage | Dernière collecte réussie (y compris un `304 Not Modified`) |
| `echecs_consecutifs` | entier | Échecs d'affilée, remis à 0 à la première réussite. **À 3, la source est mise en sommeil** |
| `etag` | texte | Dernier `ETag` renvoyé par la source, renvoyé en `If-None-Match` |
| `last_modified` | texte | Dernier `Last-Modified` renvoyé par la source, renvoyé en `If-Modified-Since` |

Mise à jour à chaque passage du DAG `collecte_rss` (toutes les 30 min). Quand une source passe en sommeil, le passage échoue (rouge dans Airflow) pour qu'on le voie.

Pour réveiller une source après correction : `UPDATE sources SET actif = true, echecs_consecutifs = 0 WHERE nom = '...';`

## Limites connues

- **Ouest-France** ne garde que 10 items dans son flux (~30 min d'actualité pour ~20 articles/h). Avec une collecte toutes les 30 min, une partie des articles est perdue. On garde la source (premier quotidien régional) et on accepte la perte : la gazette cherche les thèmes du jour, pas l'exhaustivité.
- **Le Progrès et DNA** (même groupe) publient les mêmes articles nationaux sous des liens différents : ce ne sont pas des doublons au sens de `(source, lien)`. Le dédoublonnage entre sources relève du nettoyage (TD 4).
- **Les Échos (2 flux), Le Télégramme, La Voix du Nord** répondent 403 à un client automatique (cf. `docs/sources.csv`). Elles restent dans la table et passent en sommeil après 3 échecs : on ne contourne pas leur refus.
- **Sud Ouest** passe par une protection anti-robots (Imperva) qui accepte aujourd'hui le collecteur : si elle se met à refuser, la source s'endormira comme les autres.

## Zone Silver : `articles_propres` et `rejets` (TD 4)

Les items de la zone Bronze passent par la normalisation et les règles de `docs/qualite.md`.

Stockage au TD 4 : pas de base SQL, les zones sont des buckets MinIO. `silver/articles_propres/<id>.json` pour chaque article gardé, `silver/rejets/<passage>.json` pour les rejets d'un passage, `rapports/qualite-YYYY-MM-DD.md` pour le rapport du jour.
Chaque article propre garde la trace de son item brut : son `id` est celui de la zone Bronze, et sa `source` est celle du flux.

### `articles_propres`

| Champ | Type | Description |
|---|---|---|
| `id` | texte (16 car.) | Identifiant de l'item brut (même valeur qu'en Bronze) |
| `source` | texte | Nom de la source |
| `lien` | texte (URL) | Lien vers l'article chez l'éditeur |
| `titre` | texte | Titre corrigé (encodage réparé, espaces normalisés) |
| `extrait` | texte | Extrait borné à 300 caractères, coupé sur un mot |
| `publie_le` | date ISO 8601 UTC ou `null` | Date de publication |
| `recupere_le` | date ISO 8601 UTC | Moment de la collecte |
| `rubrique` | texte ou `null` | Première catégorie du flux |
| `passage` | texte | Identifiant du passage de normalisation qui a produit la ligne |

### `rejets`

| Champ | Type | Description |
|---|---|---|
| `id` | texte | Identifiant de l'item brut rejeté |
| `source` | texte | Nom de la source |
| `regle` | texte | Identifiant de la règle (`R01_publi`, …) |
| `passage` | texte | Identifiant du passage |
| `rejete_le` | date ISO 8601 UTC | Moment du rejet |

### Rétention

- Zone Bronze : conservée tant que la source est active. Elle sert de preuve pour toute ligne propre.
- `articles_propres` : garder 90 jours glissants. Au-delà, la ligne est supprimée, son item brut reste disponible.
- `rejets` : garder 30 jours glissants, puis supprimer. Le rapport quotidien archivé reste la trace durable des rejets.
- Les rapports `rapports/qualite-YYYY-MM-DD.md` sont conservés sans limite, et ne contiennent aucune donnée personnelle.

Ce qu'on ne stocke pas, à aucune étape : le texte intégral, les images, les commentaires, les auteurs.
