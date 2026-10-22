# Qualité : règles d'exclusion

Chaque règle écarte un item de la zone Bronze avant qu'il n'entre dans `articles_propres`.
Un item rejeté va dans `rejets` avec l'identifiant de la règle. Le rapport quotidien compte les rejets par règle et par source.

Les seuils sont écrits ici, pas seulement dans le code : si un seuil change, ce fichier change avec lui.

| Identifiant | Ce qu'elle écarte | Pourquoi | Exemple | Seuil | Code |
|---|---|---|---|---|---|
| `R01_publi` | Publi-reportages, « contenus partenaires » | Pas de l'information éditoriale | rubrique « Publi-reportage » | regex `publi\|partenai\|sponsor` | `regles.r01_publi` |
| `R02_rubrique_hors_sujet` | Horoscopes, programme TV, jeux et concours | Hors du périmètre de la gazette | rubrique « Horoscope du jour » | regex `horoscope\|programme tv\|jeux\|concours` | `regles.r02_rubrique_hors_sujet` |
| `R03_depeche_reprise` | Dépêches d'agence reprises à l'identique | Même contenu répété sur plusieurs titres | même titre dans 6 sources ou plus | 6 sources | `regles.r03_depeche_reprise` |
| `R04_titre_vide` | Titre vide ou réduit à des espaces | Impossible à afficher ou à regrouper | `titre = ""` | — | `regles.r04_titre_vide` |
| `R05_date_future` | Date de publication postérieure à la collecte | Date erronée | publié le 2027-01-01, collecté le 2026-10-20 | 1 h de tolérance | `regles.r05_date_future` |
| `R06_encodage` | Texte encore illisible après réparation | Inexploitable | « Ã » ou « � » restant après correction | — | `regles.r06_encodage` |
| `R07_doublon` | Même titre dans une même source, casse et ponctuation ignorées | Doublon approximatif | « Macron annonce » puis « Macron annonce ! » | — | `regles.r07_doublon` |

## Ordre d'application

1. Correction de l'encodage et normalisation des espaces (`texte.py`), avant toute règle.
2. Règles à un item : R01, R02, R04, R05, R06.
3. Règles de lot : R03 (sur tout le passage), puis R07 (dans chaque source).

Un item écarté par une règle n'est pas examiné par les suivantes : il n'apparaît qu'une fois dans `rejets`.

## Ce qu'on ne fait pas

- Pas de modèle, pas de regroupement par thèmes : c'est le TD 5.
- Pas de résumé par un LLM.
- Pas de dédoublonnage entre liens différents d'une même dépêche : R03 couvre les reprises identiques, le reste relève du TD 5.

## Révision

À lire chaque matin pendant trois jours, puis à ajuster au moins une règle. Chaque changement de seuil ou de règle est noté ici avec sa date et sa raison.

| Date | Changement | Raison |
|---|---|---|
| 2026-10-22 | Création des règles R01 à R07 | Premier passage du TD 4 |
