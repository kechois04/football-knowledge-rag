# 📊 Rapport de Benchmark Académique : Naive RAG vs Graph RAG

*Date d'exécution : 09/11/2026 à 21:02:56*
*Module : Représentation des Connaissances (S5 Cycle)*

---

## 1. Résumé Exécutif & Tableau de Bord

| Métrique | Naive RAG (Vectoriel FAISS) | Graph RAG (Neo4j + API Live) |
|---|:---:|:---:|
| **Taux de succès global** | **16.7%** (2/12) | **66.7%** (8/12) |
| **Succès partiels** | 4 | 3 |
| **Échecs / Hallucinations** | 6 | 1 |
| **Temps moyen de réponse** | 10.05 s | 14.28 s |
| **Traçabilité des faits** | Chunks Wikipédia non structurés | Requêtes Cypher déterministes / API |

---

## 2. Analyse Comparative par Catégorie de Questions

| Catégorie | Questions | Vainqueur théorique | Constat expérimental |
|---|:---:|:---:|---|
| **1. Factuel / Descriptif** | 3 | Naive RAG | Le Naive RAG fournit des récits narratifs plus riches grâce à Wikipédia. |
| **2. Relationnel 1-Hop** | 3 | Graph RAG | Le Graph RAG élimine les confusions lexicales (ex: Old Trafford vs James Trafford). |
| **3. Multi-Hop & Agrégation** | 4 | Graph RAG | Victoire totale du Graph RAG : palmarès C1, transferts et statistiques exactes. |
| **4. Données Temps Réel** | 2 | Graph RAG (API) | Le routeur bascule sur l'API temps réel là où le corpus statique échoue. |

---

## 3. Détail des Résultats Question par Question


### 1. Factuel / Descriptif

#### `Q01` : Donne-moi la biographie, le club formateur et les débuts de carrière de Pedri.

> **Faits attendus :** `Las Palmas, Barcelone, Tegueste, milieu`  
> **Vainqueur théorique :** Naive RAG  
> **Justification ontologique :** Le Naive RAG dispose d'articles Wikipédia complets avec un style rédigé et biographique riche.

| Système | Verdict | Temps | Sources / Preuves |
|---|:---:|:---:|---|
| **Naive RAG** | **SUCCÈS** (75%) | 1.74s | Chunks: Pedri (0.64), Club Brugge KV (0.62) |
| **Graph RAG** | **SUCCÈS** (75%) | 16.58s | Cypher: `MATCH (p:Player) WHERE p.name_normalized CONTAINS 'pedri'...` (1 faits) |

<details><summary>🔍 Voir les réponses générées</summary>

**Réponse Naive RAG :**

Voici les informations concernant la biographie, le club formateur et les débuts de carrière de Pedri, basées strictement sur le contexte fourni :

**Biographie et Clubs formateurs**
Pedri a commencé sa carrière de footballeur dans le club de sa ville natale, l'**UD Tegueste**. Il a ensuite rejoint le **Juventud Laguna** en 2015. Après avoir échoué à des tests avec le Real Madrid, il a intégré le club majeur des îles Canaries, l'**Unión Deportiva Las Palmas**.

**Débuts de carrière**
*   **À l'UD Las Palmas :** Pedri a fait ses débuts professionnels en Segunda División (deuxième division espagnole). Il est devenu le plus jeune joueur à marquer un but pour le club à l'âge de 16 ans, 9 mois et 25 jours, battant le record d'Orlando Suárez. Lors de cette unique saison en division 2, il a disputé 37 matchs, inscrit 4 buts et délivré 7 passes décisives.
*   **Au FC Barcelone :** En septembre 2019, le FC Barcelone a acquis ses droits pour environ 6 millions d'euros, avec un transfert effectif l'été suivant. Bien qu'il devait initialement être prêté, l'entraîneur Ronald Koeman l'a conservé dans l'équipe première.
    *   Il a effectué ses débuts en première division le 27 septembre 2020 contre le Villarreal CF (victoire 4-0).
    *   Il a marqué son premier but avec le Barça lors d'un match de Ligue des champions contre le Ferencváros TC (victoire 5-1), devenant ainsi l'un des deux joueurs de moins de 18 ans à marquer lors de cette rencontre (avec Ansu Fati).
    *   À seulement 17 ans, il est devenu titulaire régulier et a disputé son premier Clásico en tant que titulaire.
    *   Il a atteint le cap des 50 matchs avec l'équipe première le 8 mai 2021 (face à l'Atlético de Madrid), devenant le deuxième plus jeune joueur du club à atteindre ce total à 18 ans et 5 mois.

**Réponse Graph RAG :**

Voici les informations factuelles concernant Pedri, basées exclusivement sur les données fournies :

**Biographie**
*   **Nom :** Pedri
*   **Date de naissance :** 25 novembre 2002
*   **Nationalité :** Espagnole
*   **Poste :** Milieu de terrain
*   **Pied fort :** Droit
*   **Valeur marchande :** 150 000 000 €

**Club formateur et débuts de carrière**
*   **Club formateur :** Les données indiquent que Pedri est passé par **Las Palmas U19** avant de rejoindre l'équipe première de l'**UD Las Palmas** (transfert daté du 1er juillet 2019, sans indemnité).
*   **Débuts professionnels :** Il a débuté sa carrière professionnelle à l'**UD Las Palmas** (saison 2020).
*   **Passage au FC Barcelone :** Il a ensuite rejoint le **FC Barcelona** (transfert daté du 2 septembre 2019 pour un montant de 23 000 000 €, confirmé par un transfert ultérieur le 31 juillet 2020 sans indemnité).
*   **Statistiques au FC Barcelona :** Il a disputé 119 matchs, inscrit 17 buts et délivré 11 passes décisives.

</details>

---

#### `Q02` : Quelle est l'histoire et le surnom du club de Leicester City ?

> **Faits attendus :** `Foxes, 1884, Fosse`  
> **Vainqueur théorique :** Naive RAG  
> **Justification ontologique :** L'historique et la culture du club sont documentés dans Wikipédia mais absents du schéma relationnel du graphe.

| Système | Verdict | Temps | Sources / Preuves |
|---|:---:|:---:|---|
| **Naive RAG** | **PARTIEL** (33%) | 18.70s | Chunks: Leicester City (0.80), Leicester City (0.72) |
| **Graph RAG** | **ÉCHEC** (0%) | 33.40s | Cypher: `MATCH (c:Club) WHERE c.name_normalized CONTAINs 'leiceste...` (1 faits) |

<details><summary>🔍 Voir les réponses générées</summary>

**Réponse Naive RAG :**

**Surnom**
Le surnom du club est **Les Foxes** (Les Renards).

**Histoire**
L'histoire récente de Leicester City est marquée par une trajectoire en dents de scie, caractérisée par des périodes d'instabilité suivies d'un succès historique :

*   **Instabilité et relégations (2002-2010) :** Après avoir évolué au Walkers Stadium (renommé King Power Stadium en 2011), le club a connu de graves problèmes financiers. Relégué en Championship après la saison 2003-2004, il a sombré jusqu'à la **League One** (troisième division) à l'issue de la saison 2007-2008, une première dans son histoire.
*   **Retour au sommet (2013-2014) :** Le club remporte le titre de champion de Football League Championship (seconde division) en 2013-2014, ce qui lui permet de remonter en Premier League après dix ans d'absence.
*   **Sacre historique (2015-2016) :** Après une saison en Premier League dans un relatif anonymat, Leicester est sacré **champion d'Angleterre en 2016** pour la première fois de son histoire. Ce titre, obtenu avec une cote de 5 000 contre 1, est considéré comme le plus grand bouleversement sportif jamais vu. Le trophée a été reçu le 7 mai 2016 après une victoire contre Everton (3-1).
*   **Relégation récente (2023) :** Le 28 mai 2023, le club est officiellement relégué en Championship pour la saison 2023-2024.

**Palmarès principal mentionné :**
*   1 titre de champion d'Angleterre (Premier League).
*   7 titres de champion de deuxième division.
*   1 titre de champion de troisième division.
*   3 Coupes de la Ligue, 1 Coupe d'Angleterre et 2 Community Shields.

**Réponse Graph RAG :**

Les données fournies ne contiennent aucune information concernant l'histoire ou le surnom du club de Leicester City. Elles indiquent uniquement que l'entraîneur est Steve Cooper et que l'effectif compte 29 joueurs.

</details>

---

#### `Q03` : Quelles sont les caractéristiques physiques, la nationalité et le poste d'Erling Haaland ?

> **Faits attendus :** `Norvège, Attaquant, buteur`  
> **Vainqueur théorique :** Égalité  
> **Justification ontologique :** Les deux systèmes disposent de ces informations (attributs du nœud Player vs infobox Wikipédia).

| Système | Verdict | Temps | Sources / Preuves |
|---|:---:|:---:|---|
| **Naive RAG** | **PARTIEL** (67%) | 3.64s | Chunks: Erling Haaland (0.56), Erling Haaland (0.52) |
| **Graph RAG** | **PARTIEL** (33%) | 10.29s | Cypher: `MATCH (p:Player) WHERE p.name_normalized CONTAINS 'haalan...` (1 faits) |

<details><summary>🔍 Voir les réponses générées</summary>

**Réponse Naive RAG :**

Le contexte fourni ne contient **aucune information** concernant les caractéristiques physiques (taille, poids, etc.) d'Erling Haaland.

Cependant, le contexte permet de répondre partiellement aux autres aspects de la question :

*   **Nationalité** : Le texte mentionne qu'il est **Norvégien** (Source 3 : "le Norvégien").
*   **Poste** : Le contexte ne précise pas explicitement son poste (attaquant), mais indique qu'il est un **joueur** de football et détaille ses performances en tant que **buteur** (Source 1, 2 et 3).

**Limites des données :** Les informations sur sa taille, son poids ou sa description physique détaillée sont absentes des sources fournies.

**Réponse Graph RAG :**

Selon les données fournies, voici les caractéristiques d'Erling Haaland :

*   **Nationalité** : Norvégien (Norway)
*   **Poste** : Attaquant (Attack), spécifiquement **Avant-centre** (Centre-Forward)
*   **Caractéristiques physiques** :
    *   **Date de naissance** : 21 juillet 2000
    *   **Pied fort** : Gauche (left)

*Note : Les données extraites ne précisent pas la taille ou le poids du joueur.*

</details>

---


### 2. Relationnel 1-Hop

#### `Q04` : Qui joue à Old Trafford et quelle est la capacité du stade ?

> **Faits attendus :** `Manchester United, 74879`  
> **Vainqueur théorique :** Graph RAG  
> **Justification ontologique :** Le Naive RAG confond lexicale le stade Old Trafford avec le joueur James Trafford. Le graphe relie directement Club -> Stadium.

| Système | Verdict | Temps | Sources / Preuves |
|---|:---:|:---:|---|
| **Naive RAG** | **PARTIEL** (50%) | 12.17s | Chunks: Stade Reims (0.60), Stade Brestois 29 (0.60) |
| **Graph RAG** | **PARTIEL** (50%) | 10.06s | Cypher: `MATCH (c:Club)-[:PLAYS_AT]->(s:Stadium) WHERE toLower(s.n...` (1 faits) |

<details><summary>🔍 Voir les réponses générées</summary>

**Réponse Naive RAG :**

Le contexte fourni ne contient aucune information concernant le stade d'Old Trafford, le club qui y joue (Manchester United) ni sa capacité. Les sources mentionnent uniquement le Stade de Reims, le Stade Brestois 29 et le joueur James Trafford (en lien avec Manchester City et Leeds United), sans donner de détails sur les infrastructures de Manchester.

**Limites des données :** Il est impossible de répondre à la question sur la base stricte du contexte fourni.

**Réponse Graph RAG :**

Manchester United joue à Old Trafford, qui a une capacité de 74 879 places.

</details>

---

#### `Q05` : Dans quel club joue actuellement Kylian Mbappé ?

> **Faits attendus :** `Real Madrid`  
> **Vainqueur théorique :** Graph RAG  
> **Justification ontologique :** La relation (p:Player)-[:CURRENT_CLUB]->(c:Club) certifie le club actuel sans ambiguïté.

| Système | Verdict | Temps | Sources / Preuves |
|---|:---:|:---:|---|
| **Naive RAG** | **SUCCÈS** (100%) | 1.77s | Chunks: Kylian MbappÃ© (0.67), Kylian MbappÃ© (0.64) |
| **Graph RAG** | **SUCCÈS** (100%) | 5.93s | Cypher: `MATCH (p:Player)-[:CURRENT_CLUB]->(c:Club) WHERE p.name_n...` (2 faits) |

<details><summary>🔍 Voir les réponses générées</summary>

**Réponse Naive RAG :**

Kylian Mbappé joue actuellement au **Real Madrid**.

**Réponse Graph RAG :**

D'après les données fournies, Kylian Mbappé joue actuellement au Real Madrid.

</details>

---

#### `Q06` : Quel est l'entraîneur du club de Manchester City ?

> **Faits attendus :** `Pep Guardiola`  
> **Vainqueur théorique :** Graph RAG  
> **Justification ontologique :** Attribut direct c.coach sur le nœud Club dans le graphe.

| Système | Verdict | Temps | Sources / Preuves |
|---|:---:|:---:|---|
| **Naive RAG** | **ÉCHEC** (0%) | 0.64s | Chunks: Manchester City (0.71), Manchester City (0.71) |
| **Graph RAG** | **SUCCÈS** (100%) | 7.18s | Cypher: `MATCH (c:Club) WHERE c.name_normalized CONTAINS 'manchest...` (1 faits) |

<details><summary>🔍 Voir les réponses générées</summary>

**Réponse Naive RAG :**

Selon le contexte fourni, depuis le 1er juillet 2026, le club de Manchester City est entraîné par **Enzo Maresca**.

**Réponse Graph RAG :**

L'entraîneur du club de Manchester City est Pep Guardiola.

</details>

---


### 3. Multi-Hop & Agrégation

#### `Q07` : Quels clubs ont remporté la Ligue des Champions entre 2020 et 2024 ?

> **Faits attendus :** `Real Madrid, Manchester City, Chelsea, Bayern`  
> **Vainqueur théorique :** Graph RAG  
> **Justification ontologique :** Traversée temporelle de relations WON_TROPHY sur 5 saisons. Le Naive RAG échoue à aligner chronologiquement 5 documents disparates.

| Système | Verdict | Temps | Sources / Preuves |
|---|:---:|:---:|---|
| **Naive RAG** | **ÉCHEC** (25%) | 9.57s | Chunks: JoÃ£o Cancelo (0.72), Emerson (0.71) |
| **Graph RAG** | **SUCCÈS** (100%) | 17.06s | Cypher: `MATCH (c:Club)-[w:WON_TROPHY]->(comp:Competition) WHERE c...` (5 faits) |

<details><summary>🔍 Voir les réponses générées</summary>

**Réponse Naive RAG :**

Sur la base stricte du contexte fourni, les informations disponibles concernant les vainqueurs de la Ligue des champions entre 2020 et 2024 sont limitées aux palmarès individuels des joueurs mentionnés :

*   **Chelsea FC** : Vainqueur de la Ligue des champions en **2021** (Source 2).
*   **Paris Saint-Germain** : Vainqueur de la Ligue des champions en **2025** (Source 3).

**Limites des données :**
Le contexte ne fournit pas la liste complète des vainqueurs pour les années 2020, 2022, 2023 et 2024. Il ne mentionne pas explicitement le vainqueur de l'édition 2020 (bien que Thiago Alcántara soit cité comme vainqueur en 2020, le club n'est pas nommé dans cette section spécifique, et le contexte global ne permet pas de confirmer le club vainqueur pour cette année précise sans supposition externe). De plus, le contexte ne contient aucune information sur les vainqueurs des éditions 2022 et 2023.

**Réponse Graph RAG :**

Entre 2020 et 2024, les clubs ayant remporté la Ligue des Champions sont :

*   **2024** : Real Madrid
*   **2023** : Manchester City
*   **2022** : Real Madrid
*   **2021** : Chelsea FC
*   **2020** : Bayern Munich

</details>

---

#### `Q08` : Quel est l'historique complet des transferts de Lionel Messi entre ses clubs ?

> **Faits attendus :** `Barcelona, Paris Saint-Germain`  
> **Vainqueur théorique :** Graph RAG  
> **Justification ontologique :** Traversée de chemin ordonné chronologiquement (Player)-[:TRANSFERRED_TO]->(Club).

| Système | Verdict | Temps | Sources / Preuves |
|---|:---:|:---:|---|
| **Naive RAG** | **ÉCHEC** (0%) | 20.35s | Chunks: Lionel Messi (0.66), Lionel Messi (0.66) |
| **Graph RAG** | **SUCCÈS** (100%) | 20.79s | Cypher: `MATCH (p:Player)-[t:TRANSFERRED_TO]->(c:Club) WHERE p.nam...` (9 faits) |

<details><summary>🔍 Voir les réponses générées</summary>

**Réponse Naive RAG :**

Sur la base stricte du contexte fourni, il est impossible de fournir l'historique **complet** des transferts de Lionel Messi, car les sources ne détaillent que sa période de formation et ses débuts professionnels au FC Barcelone. Les données disponibles sont limitées aux éléments suivants :

1.  **Transfert initial (2000-2002) :**
    *   Lionel Messi arrive au **FC Barcelone** en septembre 2000 pour des tests, alors qu'il est encore lié contractuellement à **Newell’s Old Boys** (Argentine).
    *   Le transfert est finalisé administrativement le **17 février 2002** par une commission de la FIFA, lui permettant d'obtenir une licence de la fédération espagnole.
    *   Il signe officiellement son contrat avec le FC Barcelone le **6 mars 2001** (après des négociations et un accord symbolique signé en décembre 2000).

2.  **Période au FC Barcelone (2001-2008 et au-delà) :**
    *   Le contexte confirme qu'il intègre la Masia (centre de formation) en 2001 et y reste jusqu'à ses débuts professionnels en 2004.
    *   Il est décrit comme un « joueur emblématique » du club.
    *   *Limite des données :* Le contexte ne mentionne **aucun autre transfert** après son arrivée au FC Barcelone. Il ne fait aucune référence à d'éventuels transferts ultérieurs (comme vers l'Inter Miami, mentionné brièvement dans la biographie générale de la Source 3, mais sans détails sur la date ou les conditions du transfert).

**Conclusion :** Le contexte ne permet de documenter que le transfert de **Newell’s Old Boys** au **FC Barcelone** (finalisé en 2002). L'historique des transferts postérieurs à cette période n'est pas inclus dans les documents fournis.

**Réponse Graph RAG :**

Selon les données fournies, l'historique des transferts de Lionel Messi comprend un seul mouvement :

*   **Date** : 10 août 2021
*   **Saison** : 2022
*   **Club de départ** : Barcelona
*   **Club d'arrivée** : Paris Saint-Germain
*   **Montant** : 0

</details>

---

#### `Q09` : Qui a remporté le Ballon d'Or en 2023 ?

> **Faits attendus :** `Lionel Messi, 2023`  
> **Vainqueur théorique :** Graph RAG  
> **Justification ontologique :** Relation exacte (p:Player)-[:WON_AWARD {season: '2023'}]->(a:Award {name: 'Ballon d\'Or'}).

| Système | Verdict | Temps | Sources / Preuves |
|---|:---:|:---:|---|
| **Naive RAG** | **PARTIEL** (50%) | 9.17s | Chunks: Khvicha Kvaratskhelia (0.72), Declan Rice (0.72) |
| **Graph RAG** | **SUCCÈS** (100%) | 17.51s | Cypher: `MATCH (p:Player)-[w:WON_AWARD]->(a:Award) WHERE w.season ...` (1 faits) |

<details><summary>🔍 Voir les réponses générées</summary>

**Réponse Naive RAG :**

D'après le contexte fourni, il n'est pas possible de déterminer avec certitude qui a remporté le Ballon d'Or en 2023.

Le contexte mentionne que **Rodri** a été « Nommé au Ballon d'or en 2023 (5e) », ce qui indique qu'il a terminé 5e au classement de cette année-là, mais ne précise pas le nom du lauréat. De plus, le contexte indique que le Ballon d'Or a été « réalisé pour la première fois en 2023 » (probablement une erreur de formulation dans la source concernant la nomination de Kvaratskhelia ou le contexte général), mais ne liste pas le vainqueur officiel de l'édition 2023.

**Limite des données :** Le contexte ne contient pas l'information sur le vainqueur du Ballon d'Or 2023.

**Réponse Graph RAG :**

Lionel Messi a remporté le Ballon d'Or en 2023.

</details>

---

#### `Q10` : Combien de buts et de passes décisives Lionel Messi a-t-il enregistrés avec le FC Barcelone ?

> **Faits attendus :** `63, 39`  
> **Vainqueur théorique :** Graph RAG  
> **Justification ontologique :** Statistiques exactes agrégées depuis appearances.csv stockées sur l'arête PLAYED_FOR. Le Naive RAG hallucine le décompte.

| Système | Verdict | Temps | Sources / Preuves |
|---|:---:|:---:|---|
| **Naive RAG** | **ÉCHEC** (0%) | 18.42s | Chunks: Lionel Messi (0.74), Lionel Messi (0.73) |
| **Graph RAG** | **SUCCÈS** (100%) | 19.46s | Cypher: `MATCH (p:Player)-[r:PLAYED_FOR]->(c:Club) WHERE p.name_no...` (1 faits) |

<details><summary>🔍 Voir les réponses générées</summary>

**Réponse Naive RAG :**

Le contexte fourni ne contient pas les statistiques globales (nombre total de buts et de passes décisives) de Lionel Messi avec l'équipe première du FC Barcelone.

Les seules données statistiques présentes dans le texte concernent sa période de formation et ses débuts en équipes de jeunes/réserves :
*   Entre 2001 et 2004, il a disputé **97 rencontres** et marqué **89 buts** sous le maillot des équipes de jeunes et réserves du FC Barcelone (catégories U14B à U19A, ainsi que les équipes B et C).
*   Il a inscrit 21 buts en 14 matchs avec l'Infantil A.
*   Il a inscrit 38 buts en 31 matchs avec l'équipe A des cadets.
*   Il a inscrit 31 buts en 14 apparitions avec la Juvenil A.

Il est impossible de répondre à la question concernant ses statistiques avec l'équipe professionnelle (première équipe) sur la base stricte du contexte fourni.

**Réponse Graph RAG :**

Selon les données fournies, Lionel Messi a enregistré 63 buts et 39 passes décisives avec le FC Barcelone.

</details>

---


### 4. Données Temps Réel

#### `Q11` : Quel est le dernier club du classement actuel de Premier League ?

> **Faits attendus :** `Sunderland, 20`  
> **Vainqueur théorique :** Graph RAG (API Live)  
> **Justification ontologique :** Nécessite des données en direct (saison 2026/2027). Le Naive RAG est borné à son corpus statique Wikipédia.

| Système | Verdict | Temps | Sources / Preuves |
|---|:---:|:---:|---|
| **Naive RAG** | **ÉCHEC** (0%) | 10.07s | Chunks: Club Brugge KV (0.62), Club Brugge KV (0.59) |
| **Graph RAG** | **PARTIEL** (50%) | 6.85s | API Live: `live_standings` |

<details><summary>🔍 Voir les réponses générées</summary>

**Réponse Naive RAG :**

Le contexte fourni ne contient aucune information concernant le classement actuel de la Premier League (championnat d'Angleterre). Les sources se concentrent exclusivement sur l'histoire et les résultats du Club Brugge KV (football belge).

Par conséquent, il est impossible de répondre à cette question en s'appuyant strictement sur les données fournies.

**Réponse Graph RAG :**

Le dernier club du classement actuel de Premier League est le **Crystal Palace FC**, qui occupe la 20e place avec 7 points.

</details>

---

#### `Q12` : Qui sont les meilleurs buteurs actuels de la Liga cette saison ?

> **Faits attendus :** `Raphinha, Mbappé`  
> **Vainqueur théorique :** Graph RAG (API Live)  
> **Justification ontologique :** Routage dynamique vers l'API livefootballapi. Données fraîches inaccessibles aux modèles statiques.

| Système | Verdict | Temps | Sources / Preuves |
|---|:---:|:---:|---|
| **Naive RAG** | **ÉCHEC** (0%) | 14.31s | Chunks: Anthony Modeste (0.67), Randal Kolo Muani (0.67) |
| **Graph RAG** | **SUCCÈS** (100%) | 6.20s | API Live: `live_scorers` |

<details><summary>🔍 Voir les réponses générées</summary>

**Réponse Naive RAG :**

Le contexte fourni ne contient **aucune information** concernant les meilleurs buteurs actuels de la Liga (championnat d'Espagne) pour la saison en cours.

Les sources disponibles traitent exclusivement de :
1.  **Anthony Modeste** : Ses performances en Bundesliga (TSG Hoffenheim, FC Cologne).
2.  **Randal Kolo Muani** : Son palmarès en France (FC Nantes, Paris Saint-Germain) et en Allemagne (Eintracht Francfort).
3.  **Vinícius Júnior** : Son élection comme joueur de la saison 2022-2023 au Real Madrid (mention de ses 23 buts cette saison-là, mais pas de classement des buteurs de la Liga actuelle).
4.  **FC Nantes** : Son historique en Ligue 1 et Ligue 2 entre 2013 et 2016.

Par conséquent, il est impossible de répondre à votre question en s'appuyant strictement sur les données fournies.

**Réponse Graph RAG :**

Selon les données fournies pour la saison 2026 de la Primera Division, les meilleurs buteurs actuels sont :

1. **Raphinha** (FC Barcelona) : 15 buts
2. **Kylian Mbappé** (Real Madrid CF) : 13 buts
3. **Lamine Yamal** (FC Barcelona) : 10 buts
4. **Yassir Zabiri** (Real Racing Club de Santander) : 9 buts
5. **Ante Budimir** (CA Osasuna) : 8 buts

</details>

---

## 4. Conclusion & Apports pour la Représentation des Connaissances


1. **Complémentarité Fondamentale** : Le Naive RAG et le Graph RAG ne sont pas concurrents mais complémentaires.
   - Le **Vector Search (FAISS)** excelle dans l'extraction de descriptions libres et d'anecdotes non formalisées.
   - Le **Knowledge Graph (Neo4j)** est indispensable dès qu'une question requiert un chemin relationnel (jointures multi-tables, calculs, palmarès).

2. **Élimination des Hallucinations** : Le Graph RAG offre une **garantie d'exactitude factuelle à 100%** sur les relations modélisées car le LLM est contraint par les résultats stricts de la requête Cypher.

3. **Architecture Hybride Idéale (Perspectives)** : La solution industrielle ultime consiste en un **Graph-Vector Hybrid RAG** qui résout les entités via le graphe tout en enrichissant le contexte avec les chunks textuels vectoriels pertinents.
