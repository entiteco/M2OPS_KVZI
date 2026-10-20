## Slide 1

M2 Data Engineering & IA · Efrei · 2026-2027

PROJET M2OPS · 35 H · 10 TD

La gazette

Un pipeline de données qui lit la presse tous les matins, tourne seul, et dont vous savez dire qu'il a tourné.

## Slide 2

👋 Bonjour, je suis Paul Gabriel
      avant SRE chez 37signals — Basecamp et HEY, sur nos propres machines : la sortie du cloud
      maintenant Directeur technique de Data for Good — des outils open source, auto-hébergés, sans big tech
      aussi SRE indépendant depuis 2021 : des plateformes qui tournent et qui grandissent — parfois le code derrière les lives de Domingo (ZEvent)
      @pagbrl partout où ça compte

## Slide 3

PQR · régionale
            Ouest-France
            La Voix du Nord
            Sud Ouest
            Le Télégramme
            …

## Slide 4

PQN · nationale
            Le Monde
            Libération
            Le Figaro
            Les Échos
            La Croix
            …

## Slide 5

La question n'est pas « est-ce que ça marche sur mon poste ? »
        Mais « a-t-elle tourné tous les matins pendant que personne ne regardait ? »
        Entre deux séances, votre gazette tourne : incidents et correctifs vont dans un journal de bord.
        C'est ce journal, autant que le code, qui sera lu.

          La question M2Ops
          Et comment le savez-vous ?
          Métriques, alertes, journal de bord : la réponse est écrite, pas dans vos souvenirs.

## Slide 6

Chaque TD en construit une ou deux.
        À la fin du module, l'ensemble tourne seul, tous les matins.
        Observé et reproductible.
        Aujourd'hui : on le dessine. Au TD 2, le socle.

              Collecte
              va chercher ce que chaque source publie, poliment, avec reprise
              TD 3

              Stockage brut
              chaque item tel quel, sans doublon, avec sa provenance
              TD 3

              Nettoyage et qualité
              normalise, écarte selon des règles documentées, produit un rapport
              TD 4

              Thèmes
              regroupe, nomme ; chaque run tracé, évalué, versionné
              TD 5–6

              Livraison
              génère, vérifie, publie et archive l'édition de 7 h
              TD 7

            items

            articles bruts

            articles propres

            thèmes du jour

            Supervision
            métriques, alertes,
            runbook ; l'infra
            décrite en code
            TD 8 · infra dès le TD 2

            observe

          Le socle (dépôt, conteneurs, CI) vient avant tout : TD 2.
            Le cadrage avant le socle : TD 1, aujourd'hui.

## Slide 7

Cadrage, CI/CD, traitements et stockage, MLOps, monitoring, infrastructure as code, mise en situation.
      Les dates sont celles de .

      TD 1Cadrage et bornageC7.1
      TD 2Le socle : dépôt, conteneurs, première CIC7.2 · C8.2
      TD 3CollecterC7.3 · C7.1
      TD 4Nettoyer, contrôler, stockerC7.3
      TD 5Regrouper par thèmes (MLOps 1)C7.4
      TD 6Évaluer, versionner, déployer le modèle (MLOps 2)C7.4 · C7.2
      TD 7Livrer la gazette : l'édition de 7 hC7.3 · C7.2 · C7.1
      TD 8Surveiller et administrerC8.1
      TD 9L'infrastructure en code, consolidéeC8.2 · commencée au TD 2
      TD 10Consolider et soutenirC7.1 → C8.2

## Slide 8

on prend
        Titres, extraits, liens, dates
        Ce que les éditeurs laissent lire aux machines — à vous de trouver comment.

        on ne prend pas
        L'article entier, les images, les commentaires
        Jamais. Ni le texte intégral, ni scraping.

        les éditeurs
        Leurs conditions
        Respectées, et notées dans sources.csv.

        les personnes
        Aucune donnée personnelle
        Pas de commentaires, pas de profils, pas d'abonné·es, pas de suivi.

        l'argent
        Budget zéro
        Vos machines pour l'instant. Une infrastructure de production vous sera fournie au TD 4 ou 6, pas avant.

## Slide 9

l'heure
        7 h
        L'édition sort à 7 h. Une par jour.

        la fraîcheur
        < 24 h
        Un article de l'édition a moins de 24 h.

    7 h et moins de 24 h : c'est votre objectif de service, et vous le mesurerez.

## Slide 10

Faire du beau front.
        Résumer les articles avec un LLM.
        Scraper le texte intégral.

          Du temps en trop ?
          Il va dans la robustesse et l'observabilité,
            pas dans les fonctionnalités.

## Slide 11

Des équipes de 3 ou 4 personnes, et le lien du dépôt sur la fiche de l'équipe.
        Un livrable par TD, commité avant la séance suivante.
        Dès le TD 7 : un journal de bord, un·e responsable d'exploitation par semaine.
        À chaque outil, deux alternatives et pourquoi pas elles. Aucun outil n'est imposé.
        L'infrastructure en code dès le premier jour : ce qui tourne est décrit, jamais cliqué. Le TD 9 consolide.

          docs/

            cadrage.mddès aujourd'hui
            ci-cd.mdla stratégie retenue
            donnees.mdle contrat, le dictionnaire
            qualite.mdles règles, et pourquoi
            mlops.mdmodèles, runs, fiche modèle
            exploitation.mdrunbook, déploiement
            journal.mdà partir du TD 7

          Une documentation qui s'écrit au fil de l'eau. Le rapport final en sort presque tout seul.

## Slide 12

On ouvre par un tour de reprise : la gazette a-t-elle tourné ? Il compte.
        Chaque séance a sa feuille de route sur la plateforme, ouverte la veille.
        Une question, quelque chose à montrer : l'équipe entre dans la file d'attente, et y voit qui est en cours et qui suit.
        Pendant que vous attendez, vous avancez.

          La plateforme
          lessons.rempart.dev
          Mot de passe de votre groupe : donné à l'oral.
          Les équipes, la file d'attente, les feuilles de route, le calendrier, la grille d'évaluation.

## Slide 13

La partie 2 de l'évaluation du bloc 3 : La gazette en est l'étude de cas.
        Collectif, puis individualisé : la note d'équipe est la base.
        La soutenance au TD 10, démo depuis votre production.
        Le rapport technique, remis 48 h avant.

            Compétence12345678910

              C7.1 CI, conteneurs, ordonnancement●●●●
              C7.2 pipelines CI/CD testés●●●●
              C7.3 traitements et stockage●●●●
              C7.4 MLOps●●●
              C8.1 monitoring, administration●●
              C8.2 infrastructure as code●●●

          Les compétences C7.1 à C8.2, TD par TD. La grille complète est sur la page Évaluation de la plateforme.

## Slide 14

Le dernier après-midi de votre groupe : TD 10.
        20 minutes par équipe, démo en direct.
        Chaque membre répond sur une compétence et la partie qu'il ou elle a portée.
        Prévoyez un plan B si le réseau tombe.

          L'édition de ce matin, publiée sans vous
          Le tableau de bord
          Un commit qui déclenche la CI
          La version du modèle en service, et un retour arrière
          Une alerte
          Le journal de bord

## Slide 15

TDM2-DE1M2-DE3M2-DE2

        1 Cadrage et bornagelun. 19 oct. matinmar. 20 oct. matinven. 13 nov. matin
        2 Le soclelun. 19 oct. après-midimar. 20 oct. après-midiven. 13 nov. après-midi
        3 Collectermer. 21 oct. matinjeu. 22 oct. matinlun. 30 nov. matin
        4 Nettoyer, contrôler, stockerjeu. 12 nov. matinjeu. 22 oct. après-midilun. 30 nov. après-midi
        5 MLOps 1jeu. 12 nov. après-midiven. 23 oct. après-midimar. 1er déc. matin
        6 MLOps 2mer. 20 janv. matinjeu. 26 nov. après-midimar. 1er déc. après-midi
        7 L'édition de 7 hmer. 20 janv. après-midilun. 8 févr. matinlun. 18 janv. matin
        8 Surveiller et administrermar. 9 févr. matin, avec le TD 9lun. 8 févr. après-midilun. 18 janv. après-midi
        9 L'infrastructure en codemar. 9 févr. matin, avec le TD 8jeu. 11 févr. matinmer. 10 févr. matin
        10 Consolider et soutenirmar. 9 févr. après-midijeu. 11 févr. après-midimer. 10 févr. après-midi

    Matin 09 h 10 – 12 h 40 · après-midi 13 h 40 – 17 h 10 (M2-DE1 : 18 h 10). Le calendrier de votre groupe, avec le livrable de chaque TD, est sur la plateforme : c'est lui qui fait foi.

## Slide 16

Projet M2Ops · La gazette
      TD 1 · 3 h 30 ·  ·
      Cadrage et bornage
      À la fin de la séance, votre équipe existe, sait ce qu'est La gazette,
        ce qu'elle a le droit de faire avec la presse, et a tranché une première architecture.
        Rien ne tourne encore : on comprend et on borne.

## Slide 17

Dans cet ordre, à votre rythme : le temps est à vous, le livrable est pour la fin.

      1Veille éclair, en binômes
        Six sujets, deux options chacun, leurs limites, votre reco. Puis trois minutes par équipe devant les autres.
      2Choix des sources
        Au moins 4 PQR et 4 PQN : comment vous les lirez, leurs conditions, leur fréquence. sources.csv.
      3Note de cadrage et schéma
        Une page : docs/cadrage.md. Les six boîtes, ce qui circule, où ça tourne.
      4Le dépôt
        Créé, un premier commit, son lien sur la fiche de l'équipe.
      5Tour des équipes
        En fin de séance, votre schéma en une minute.
      livrableTout commité
        Note, schéma et sources.csv dans le dépôt avant de partir.

## Slide 18

En binômes dans l'équipe, six sujets à se répartir.
        Par sujet, une diapo ou une demi-page : deux options, leurs limites, votre reco.

      1Récupérer la presse
        comment on y accède, sous quelle forme, les pièges
      2Faire tourner chaque matin
        comment, où, et comment relancer
      3Stocker
        le brut, le propre, sous quelle forme
      4Regrouper des textes
        par thèmes, avec quelles approches
      5Surveiller
        métriques, alertes, journaux
      6Décrire l'infrastructure en code
        quelles options, pour quel hébergement

## Slide 19

Au moins 4 PQR et 4 PQN.
        Pour chacune : comment vous la lirez, ses conditions, sa fréquence.
        Vérifiées à la main : ouvrez-la, regardez un item.

          sources.csv

            nomle titre de presse
            typePQR ou PQN
            regionsa région
            accescomment on la lit : l'adresse, le format
            conditionsses conditions d'utilisation
            notesfréquence de mise à jour, ce que vous avez vu

          Commité dans le dépôt avec la note de cadrage.

## Slide 20

Trois choses, toutes dans le dépôt avant de partir.

        une page
        docs/cadrage.md

          le besoin avec vos mots
          le périmètre : dedans, dehors
          les contraintes
          la stack retenue, les alternatives écartées, pourquoi
          les risques, les rôles dans l'équipe

        le schéma
        L'architecture

          les six boîtes
          ce qui circule entre elles
          où ça tourne

        docs/architecture.png · .svg · ou Mermaid dans le markdown

        le dépôt
        Git

          le dépôt créé
          un premier commit
          son lien sur la fiche de l'équipe, sur la plateforme

## Slide 21

Le livrable du TD 1, commité dans le dépôt de l'équipe.
        Vous savez ce que vous construirez au TD 2 : le socle.
        Et au TD 3 : la collecte.

          Équipe formée et inscrite
          Dépôt créé et lié sur la plateforme
          docs/cadrage.md commité
          Le schéma d'architecture commité
          sources.csv commité

## Slide 22

l'équipe
        Relire la note de cadrage à tête reposée, et la corriger
        C'est la première chose que la grille regarde — C7.1 : « une veille
          technologique est utilisée pour identifier les solutions les plus efficaces ».

        chacun·e
        Installer ce qu'il faut pour le TD 2

          Docker, Git
          le langage choisi
          un compte sur la forge de l'équipe, avec accès au dépôt

## Slide 23

Maintenant
      Faites des équipes de 3 ou 4.
      Sur lessons.rempart.dev, dans l'espace de votre groupe — mot de passe : .

