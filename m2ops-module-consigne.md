## Slide 1
**M2 Data Engineering & IA · Efrei · 2026-2027**  
*PROJET M2OPS · 35 H · 10 TD*

# La gazette
Un pipeline de données qui lit la presse tous les matins, tourne seul, et dont vous savez dire qu'il a tourné.

## Slide 2
👋 **Bonjour, je suis Paul Gabriel**
- **avant** : SRE chez 37signals — Basecamp et HEY, sur nos propres machines : la sortie du cloud
- **maintenant** : Directeur technique de Data for Good — des outils open source, auto-hébergés, sans big tech
- **aussi** : SRE indépendant depuis 2021 : des plateformes qui tournent et qui grandissent — parfois le code derrière les lives de Domingo (ZEvent)
- **@pagbrl** partout où ça compte

## Slide 3
**PQR · régionale**
- Ouest-France
- La Voix du Nord
- Sud Ouest
- Le Télégramme
- …

## Slide 4
**PQN · nationale**
- Le Monde
- Libération
- Le Figaro
- Les Échos
- La Croix
- …

## Slide 5
> La question n'est pas « est-ce que ça marche sur mon poste ? »  
> Mais « a-t-elle tourné tous les matins pendant que personne ne regardait ? »

Entre deux séances, votre gazette tourne : incidents et correctifs vont dans un journal de bord. C'est ce journal, autant que le code, qui sera lu.

**La question M2Ops : Et comment le savez-vous ?**
- Métriques, alertes, journal de bord : la réponse est écrite, pas dans vos souvenirs.

## Slide 6
Chaque TD en construit une ou deux. À la fin du module, l'ensemble tourne seul, tous les matins. Observé et reproductible.  
*Aujourd'hui : on le dessine. Au TD 2, le socle.*

- **Collecte** (TD 3) : va chercher ce que chaque source publie, poliment, avec reprise → *items*
- **Stockage brut** (TD 3) : chaque item tel quel, sans doublon, avec sa provenance → *articles bruts*
- **Nettoyage et qualité** (TD 4) : normalise, écarte selon des règles documentées, produit un rapport → *articles propres*
- **Thèmes** (TD 5–6) : regroupe, nomme ; chaque run tracé, évalué, versionné → *thèmes du jour*
- **Livraison** (TD 7) : génère, vérifie, publie et archive l'édition de 7 h
- **Supervision** (TD 8 · infra dès le TD 2) : métriques, alertes, runbook ; l'infra décrite en code → *observe*

> Le socle (dépôt, conteneurs, CI) vient avant tout : TD 2.  
> Le cadrage avant le socle : TD 1, aujourd'hui.

## Slide 7
Cadrage, CI/CD, traitements et stockage, MLOps, monitoring, infrastructure as code, mise en situation.

| TD | Sujet | Compétences |
| :--- | :--- | :--- |
| **TD 1** | Cadrage et bornage | C7.1 |
| **TD 2** | Le socle : dépôt, conteneurs, première CI | C7.2 · C8.2 |
| **TD 3** | Collecter | C7.3 · C7.1 |
| **TD 4** | Nettoyer, contrôler, stocker | C7.3 |
| **TD 5** | Regrouper par thèmes (MLOps 1) | C7.4 |
| **TD 6** | Évaluer, versionner, déployer le modèle (MLOps 2) | C7.4 · C7.2 |
| **TD 7** | Livrer la gazette : l'édition de 7 h | C7.3 · C7.2 · C7.1 |
| **TD 8** | Surveiller et administrer | C8.1 |
| **TD 9** | L'infrastructure en code, consolidée | C8.2 · (dès le TD 2) |
| **TD 10** | Consolider et soutenir | C7.1 → C8.2 |

## Slide 8
- **On prend :** Titres, extraits, liens, dates. Ce que les éditeurs laissent lire aux machines — à vous de trouver comment.
- **On ne prend pas :** L'article entier, les images, les commentaires. Jamais. Ni le texte intégral, ni scraping.
- **Les éditeurs :** Leurs conditions. Respectées, et notées dans *sources.csv*.
- **Les personnes :** Aucune donnée personnelle. Pas de commentaires, pas de profils, pas d'abonné·es, pas de suivi.
- **L'argent :** Budget zéro. Vos machines pour l'instant. Une infrastructure de production vous sera fournie au TD 4 ou 6, pas avant.

## Slide 9
- **L'heure (7 h) :** L'édition sort à 7 h. Une par jour.
- **La fraîcheur (< 24 h) :** Un article de l'édition a moins de 24 h.

> 7 h et moins de 24 h : c'est votre objectif de service, et vous le mesurerez.

## Slide 10
**Ce qu'on ne fait PAS :**
- Faire du beau front.
- Résumer les articles avec un LLM.
- Scraper le texte intégral.

> Du temps en trop ? Il va dans la robustesse et l'observabilité, pas dans les fonctionnalités.

## Slide 11
- Des équipes de 3 ou 4 personnes, et le lien du dépôt sur la fiche de l'équipe.
- Un livrable par TD, commité avant la séance suivante.
- Dès le TD 7 : un journal de bord, un·e responsable d'exploitation par semaine.
- À chaque outil, deux alternatives et pourquoi pas elles. Aucun outil n'est imposé.
- L'infrastructure en code dès le premier jour : ce qui tourne est décrit, jamais cliqué. Le TD 9 consolide.

**Structure du dossier `docs/` :**
- `cadrage.md` (dès aujourd'hui)
- `ci-cd.md` (la stratégie retenue)
- `donnees.md` (le contrat, le dictionnaire)
- `qualite.md` (les règles, et pourquoi)
- `mlops.md` (modèles, runs, fiche modèle)
- `exploitation.md` (runbook, déploiement)
- `journal.md` (à partir du TD 7)

*Une documentation qui s'écrit au fil de l'eau. Le rapport final en sort presque tout seul.*

## Slide 12
On ouvre par un tour de reprise : la gazette a-t-elle tourné ? Il compte.
- Chaque séance a sa feuille de route sur la plateforme, ouverte la veille.
- Une question, quelque chose à montrer : l'équipe entre dans la file d'attente, et y voit qui est en cours et qui suit. Pendant que vous attendez, vous avancez.

**La plateforme :**
- `lessons.rempart.dev`
- Mot de passe de votre groupe : donné à l'oral.
- Les équipes, la file d'attente, les feuilles de route, le calendrier, la grille d'évaluation.

## Slide 13
La partie 2 de l'évaluation du bloc 3 : *La gazette* en est l'étude de cas. Collectif, puis individualisé : la note d'équipe est la base.
- La soutenance au TD 10, démo depuis votre production.
- Le rapport technique, remis 48 h avant.

| Compétence | Description |
| :--- | :--- |
| **C7.1** | CI, conteneurs, ordonnancement (●●●●) |
| **C7.2** | Pipelines CI/CD testés (●●●●) |
| **C7.3** | Traitements et stockage (●●●●) |
| **C7.4** | MLOps (●●●) |
| **C8.1** | Monitoring, administration (●●) |
| **C8.2** | Infrastructure as code (●●●) |

## Slide 14
Le dernier après-midi de votre groupe : TD 10. 20 minutes par équipe, démo en direct. Chaque membre répond sur une compétence et la partie qu'il ou elle a portée. Prévoyez un plan B si le réseau tombe.

**Ce qui sera démontré :**
- L'édition de ce matin, publiée sans vous
- Le tableau de bord
- Un commit qui déclenche la CI
- La version du modèle en service, et un retour arrière
- Une alerte
- Le journal de bord

## Slide 15
*Matin 09 h 10 – 12 h 40 · après-midi 13 h 40 – 17 h 10 (M2-DE1 : 18 h 10).*

| TD | Sujet | M2-DE1 | M2-DE3 | M2-DE2 |
| :--- | :--- | :--- | :--- | :--- |
| **1** | Cadrage et bornage | lun. 19 oct. matin | mar. 20 oct. matin | ven. 13 nov. matin |
| **2** | Le socle | lun. 19 oct. am | mar. 20 oct. am | ven. 13 nov. am |
| **3** | Collecter | mer. 21 oct. matin | jeu. 22 oct. matin | lun. 30 nov. matin |
| **4** | Nettoyer, contrôler, stocker | jeu. 12 nov. matin | jeu. 22 oct. am | lun. 30 nov. am |
| **5** | MLOps 1 | jeu. 12 nov. am | ven. 23 oct. am | mar. 1er déc. matin |
| **6** | MLOps 2 | mer. 20 janv. matin | jeu. 26 nov. am | mar. 1er déc. am |
| **7** | L'édition de 7 h | mer. 20 janv. am | lun. 8 févr. matin | lun. 18 janv. matin |
| **8** | Surveiller et administrer | mar. 9 févr. matin (avec 9)| lun. 8 févr. am | lun. 18 janv. am |
| **9** | L'infrastructure en code | mar. 9 févr. matin (avec 8)| jeu. 11 févr. matin| mer. 10 févr. matin |
| **10** | Consolider et soutenir | mar. 9 févr. am | jeu. 11 févr. am | mer. 10 févr. am |

## Slide 16
**Projet M2Ops · La gazette**
*TD 1 · 3 h 30 · Cadrage et bornage*

À la fin de la séance, votre équipe existe, sait ce qu'est *La gazette*, ce qu'elle a le droit de faire avec la presse, et a tranché une première architecture.
Rien ne tourne encore : on comprend et on borne.

## Slide 17
Dans cet ordre, à votre rythme : le temps est à vous, le livrable est pour la fin.

1. **Veille éclair, en binômes :** Six sujets, deux options chacun, leurs limites, votre reco. Puis 3 minutes par équipe devant les autres.
2. **Choix des sources :** Au moins 4 PQR et 4 PQN : comment vous les lirez, conditions, fréquence. `sources.csv`.
3. **Note de cadrage et schéma :** Une page : `docs/cadrage.md`. Les six boîtes, ce qui circule, où ça tourne.
4. **Le dépôt :** Créé, un premier commit, son lien sur la fiche de l'équipe.
5. **Tour des équipes :** En fin de séance, votre schéma en une minute.
6. **Livrable :** Tout commité (Note, schéma et sources.csv) dans le dépôt avant de partir.

## Slide 18
En binômes dans l'équipe, six sujets à se répartir. Par sujet, une diapo ou une demi-page : deux options, leurs limites, votre reco.

1. **Récupérer la presse :** comment on y accède, sous quelle forme, les pièges.
2. **Faire tourner chaque matin :** comment, où, et comment relancer.
3. **Stocker :** le brut, le propre, sous quelle forme.
4. **Regrouper des textes :** par thèmes, avec quelles approches.
5. **Surveiller :** métriques, alertes, journaux.
6. **Décrire l'infrastructure en code :** quelles options, pour quel hébergement.

## Slide 19
Au moins 4 PQR et 4 PQN. Pour chacune : comment vous la lirez, ses conditions, sa fréquence. Vérifiées à la main : ouvrez-la, regardez un item.

**`sources.csv`**
- `nom` : le titre de presse
- `type` : PQR ou PQN
- `region` : sa région
- `acces` : comment on la lit (l'adresse, le format)
- `conditions` : ses conditions d'utilisation
- `notes` : fréquence de mise à jour, ce que vous avez vu

*Commité dans le dépôt avec la note de cadrage.*

## Slide 20
Trois choses, toutes dans le dépôt avant de partir :

**1. Une page (`docs/cadrage.md`)**
- Le besoin avec vos mots
- Le périmètre : dedans, dehors
- Les contraintes
- La stack retenue, les alternatives écartées, pourquoi
- Les risques, les rôles dans l'équipe

**2. Le schéma (L'architecture)**
- Les six boîtes, ce qui circule entre elles, où ça tourne
- `docs/architecture.png` (ou `.svg` ou Mermaid)

**3. Le dépôt (Git)**
- Le dépôt créé
- Un premier commit
- Son lien sur la fiche de l'équipe, sur la plateforme

## Slide 21
Le livrable du TD 1, commité dans le dépôt de l'équipe.
Vous savez ce que vous construirez au TD 2 : le socle. Et au TD 3 : la collecte.

- [ ] Équipe formée et inscrite
- [ ] Dépôt créé et lié sur la plateforme
- [ ] `docs/cadrage.md` commité
- [ ] Le schéma d'architecture commité
- [ ] `sources.csv` commité

## Slide 22
- **L'équipe :** Relire la note de cadrage à tête reposée, et la corriger. C'est la première chose que la grille regarde — C7.1 : *« une veille technologique est utilisée pour identifier les solutions les plus efficaces »*.
- **Chacun·e :** Installer ce qu'il faut pour le TD 2 : Docker, Git, le langage choisi, un compte sur la forge de l'équipe avec accès au dépôt.

## Slide 23
**Maintenant**
Faites des équipes de 3 ou 4.
Sur `lessons.rempart.dev`, dans l'espace de votre groupe — mot de passe : [donné à l'oral].