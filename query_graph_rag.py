"""
Module d'interrogation et de génération pour le Graph RAG avec Neo4j, Cypher et API Live.
1. Reçoit une question en langage naturel (français).
2. Le LLM route la question vers la source appropriée :
   a) Neo4j (données historiques 2019-2024) via Text-to-Cypher
   b) API Football-Data.org (données temps réel : classements, buteurs, résultats)
3. Synthétise la réponse finale certifiée par les données.
"""

import os
import sys
import re
import json
from dotenv import load_dotenv
from neo4j import GraphDatabase
from groq import Groq
from livefootballapi import get_top_scorers, get_standings, get_recent_matches, LEAGUE_CODES

# Sécuriser l'encodage du terminal Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

load_dotenv()

# Configuration Neo4j
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "football2024")

# Configuration LLM Groq
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "qwen/qwen3.8-27b"

# Schéma officiel du Graphe injecté dans le prompt pour le LLM
NEO4J_SCHEMA_PROMPT = """
Le schéma Neo4j est le suivant :

NŒUDS ET PROPRIÉTÉS :
- (:Player {id: int, name: str, code: str, name_normalized: str, position: str, sub_position: str, nationality: str, date_of_birth: str, foot: str, market_value: int, highest_market_value: int})
  * p.name : nom officiel (ex: 'Kylian Mbappé')
  * p.name_normalized : nom en minuscules SANS accents (ex: 'kylian mbappe') -> TRÈS UTILE pour la recherche !
  * p.code : code slug (ex: 'kylian-mbappe')
- (:Club {id: int, name: str, code: str, name_normalized: str, coach: str, squad_size: int})
  * c.name_normalized : nom du club en minuscules sans accents (ex: 'real madrid', 'fc barcelone')
- (:Stadium {name: str, seats: int})
- (:Competition {id: str, name: str, code: str, country: str, type: str})  // id ex: 'CL' (Champions League), 'GB1' (Premier League), 'ES1' (LaLiga), 'IT1' (Serie A), 'L1' (Bundesliga), 'FR1' (Ligue 1)
- (:Award {name: str})  // ex: "Ballon d'Or", "UEFA Men's Player of the Year", "European Golden Shoe"

RELATIONS ET ATTRIBUTS :
- (:Club)-[:PLAYS_AT]->(:Stadium)
- (:Club)-[:COMPETES_IN]->(:Competition)
- (:Player)-[:CURRENT_CLUB]->(:Club)
- (:Player)-[:TRANSFERRED_TO {season: str, date: str, fee: int, from_club_id: int, from_club_name: str, to_club_name: str}]->(:Club)
- (:Player)-[:PLAYED_FOR {matches: int, goals: int, assists: int, minutes: int, yellow_cards: int, red_cards: int}]->(:Club)
- (:Club)-[:WON_TROPHY {season: str}]->(:Competition)
- (:Club)-[:RUNNER_UP {season: str}]->(:Competition)
- (:Player)-[:WON_AWARD {season: str, details: str}]->(:Award)

RÈGLES IMPORTANTES DE CYPHER :
1. Pour rechercher un joueur par nom, utilise TOUJOURS p.name_normalized CONTAINS '<nom_sans_accent>' (ex: p.name_normalized CONTAINS 'mbappe') ou toLower(p.name) CONTAINS '<nom>'.
2. Quand tu cherches le club ou des infos sur un joueur, renvoie TOUJOURS p.name ET c.name (ex: RETURN p.name AS joueur, c.name AS club) pour distinguer clairement d'éventuels homonymes.
3. Ne génère QUE la requête Cypher, entourée d'un bloc ```cypher ... ```, sans explications préalables.
4. Limite les résultats avec LIMIT 10 sauf si un décompte ou une agrégation est demandée.
5. Renvoie des alias clairs dans le RETURN (ex: RETURN p.name AS joueur, c.name AS club, s.name AS stadium).
"""

CYPHER_FEW_SHOTS = """
Exemples :
Q: Dans quel club joue Mbappé ?
```cypher
MATCH (p:Player)-[:CURRENT_CLUB]->(c:Club)
WHERE p.name_normalized CONTAINS 'mbappe' OR p.code CONTAINS 'mbappe'
RETURN p.name AS joueur, c.name AS club
```

Q: Qui joue à Old Trafford ?
```cypher
MATCH (c:Club)-[:PLAYS_AT]->(s:Stadium)
WHERE toLower(s.name) CONTAINS 'trafford'
RETURN c.name AS club, s.name AS stadium, s.seats AS capacite
```

Q: Quels clubs ont remporté la Ligue des Champions entre 2020 et 2024 ?
```cypher
MATCH (c:Club)-[w:WON_TROPHY]->(comp:Competition)
WHERE comp.id = 'CL' AND w.season >= '2020' AND w.season <= '2024'
RETURN w.season AS saison, c.name AS vainqueur
ORDER BY saison DESC
```

Q: Quel est l'historique des transferts de Erling Haaland ?
```cypher
MATCH (p:Player)-[t:TRANSFERRED_TO]->(c:Club)
WHERE p.name_normalized CONTAINS 'haaland'
RETURN p.name AS joueur, t.season AS saison, t.from_club_name AS club_depart, c.name AS club_arrivee, t.fee AS montant
ORDER BY t.date ASC
```

Q: Combien de buts Lionel Messi a-t-il marqués avec le FC Barcelone ?
```cypher
MATCH (p:Player)-[r:PLAYED_FOR]->(c:Club)
WHERE p.name_normalized CONTAINS 'messi' AND c.name_normalized CONTAINS 'barcelona'
RETURN p.name AS joueur, c.name AS club, r.matches AS matches, r.goals AS buts, r.assists AS passes
```

Q: Qui a gagné le Ballon d'Or en 2023 ?
```cypher
MATCH (p:Player)-[w:WON_AWARD]->(a:Award)
WHERE w.season = '2023' AND a.name CONTAINS 'Ballon'
RETURN p.name AS joueur, a.name AS distinction, w.season AS saison
```
"""

# Prompt de routage : le LLM décide si la question nécessite Neo4j ou l'API Live
ROUTING_PROMPT = """Tu es un routeur intelligent pour un système RAG sur le football.
Tu dois déterminer quelle source de données utiliser pour répondre à la question de l'utilisateur.

SOURCES DISPONIBLES :
1. "neo4j" : Base de données historique couvrant la période 2019-2024. Contient : joueurs, clubs, stades, transferts, statistiques de match, trophées, distinctions individuelles (Ballon d'Or, etc.) des 5 grands championnats européens + Champions League.
2. "live_scorers" : API temps réel pour les meilleurs buteurs ACTUELS de la saison en cours.
3. "live_standings" : API temps réel pour le classement ACTUEL d'un championnat en cours.
4. "live_matches" : API temps réel pour les derniers résultats de matchs récents.

RÈGLES DE ROUTAGE :
- Si la question porte sur le classement ACTUEL, la saison EN COURS, les résultats RÉCENTS → utilise une source "live_*".
- Si la question porte sur des données historiques (transferts, palmarès, statistiques passées, stade d'un club) → utilise "neo4j".
- Si la question mentionne "actuellement", "en ce moment", "cette saison", "cette année" → "live_*".

Réponds UNIQUEMENT avec un JSON valide au format :
{"source": "<neo4j|live_scorers|live_standings|live_matches>", "league": "<nom_du_championnat_si_pertinent>"}

QUESTION DE L'UTILISATEUR :
"""


class GraphRAG:
    def __init__(self):
        print("Connexion au graphe Neo4j Docker...")
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        self.driver.verify_connectivity()
        self.client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
        print("Graph RAG prêt avec Neo4j, Groq et API Live Football.\n")

    def close(self):
        self.driver.close()

    def route_question(self, question: str) -> dict:
        """Le LLM détermine si la question nécessite Neo4j ou l'API Live."""
        if not self.client:
            return {"source": "neo4j", "league": ""}

        prompt = ROUTING_PROMPT + question + "\n\nJSON :"

        completion = self.client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=60,
        )
        content = completion.choices[0].message.content.strip()

        # Extraire le JSON
        try:
            # Chercher un JSON dans la réponse
            json_match = re.search(r'\{[^}]+\}', content)
            if json_match:
                return json.loads(json_match.group())
        except (json.JSONDecodeError, AttributeError):
            pass
        return {"source": "neo4j", "league": ""}

    def generate_cypher(self, question: str) -> str:
        """Utilise le LLM pour traduire une question en langage naturel en requête Cypher."""
        if not self.client:
            raise ValueError("Clé GROQ_API_KEY manquante.")

        prompt = f"""Tu es un expert mondial en bases de données orientées graphe Neo4j et Cypher.
Traduis la question utilisateur en une requête Cypher valide et optimale en suivant strictement le schéma ci-dessous.

{NEO4J_SCHEMA_PROMPT}

{CYPHER_FEW_SHOTS}

QUESTION UTILISATEUR :
{question}

Génère UNIQUEMENT le bloc Cypher :"""

        completion = self.client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=300,
        )
        content = completion.choices[0].message.content.strip()

        # Extraire la requête du bloc ```cypher
        match = re.search(r"```(?:cypher)?\s*(.*?)\s*```", content, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return content

    def execute_cypher(self, cypher: str) -> list[dict]:
        """Exécute la requête Cypher dans Neo4j et retourne la liste des enregistrements."""
        with self.driver.session() as session:
            result = session.run(cypher)
            return [record.data() for record in result]

    def call_live_api(self, source: str, league: str) -> str:
        """Appelle la fonction de l'API Live correspondante."""
        league = league.strip() if league else "premier league"
        if source == "live_scorers":
            return get_top_scorers(league)
        elif source == "live_standings":
            return get_standings(league)
        elif source == "live_matches":
            return get_recent_matches(league)
        return "Source inconnue."

    def synthesize_answer(self, question: str, source_label: str, data_text: str) -> str:
        """Formule une réponse en français à partir des données extraites."""
        if not self.client:
            return f"Résultats bruts : {data_text}"

        prompt = f"""Tu es un assistant universitaire expert en football.
Réponds à la question de manière claire, concise et précise en t'appuyant EXCLUSIVEMENT sur les données fournies ci-dessous.
Ne spécule pas et n'invente rien.

QUESTION :
{question}

SOURCE DES DONNÉES : {source_label}

DONNÉES EXTRAITES :
{data_text}

RÉPONSE FACTUELLE EN FRANÇAIS :"""

        completion = self.client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=500,
        )
        return completion.choices[0].message.content.strip()

    def ask(self, question: str) -> dict:
        """Pipeline complet Graph RAG : Routage -> Exécution (Neo4j ou API Live) -> Synthèse."""
        # Étape 1 : Routage intelligent
        route = self.route_question(question)
        source = route.get("source", "neo4j")
        league = route.get("league", "")

        cypher = None
        records = []
        live_data = None
        error = None

        if source == "neo4j":
            # Étape 2a : Text-to-Cypher + Exécution Neo4j
            cypher = self.generate_cypher(question)
            try:
                records = self.execute_cypher(cypher)
            except Exception as e:
                error = str(e)

            if error:
                answer = f"Erreur lors de l'exécution Cypher : {error}"
            elif not records:
                answer = "Aucune information correspondante n'a été trouvée dans le Graphe de Connaissances."
            else:
                data_text = f"Requête Cypher : {cypher}\nRésultats : {records}"
                answer = self.synthesize_answer(question, "Graphe de Connaissances Neo4j (2019-2024)", data_text)
        else:
            # Étape 2b : Appel API temps réel
            try:
                live_data = self.call_live_api(source, league)
            except Exception as e:
                error = str(e)
                live_data = f"Erreur API : {error}"

            answer = self.synthesize_answer(
                question,
                f"API Football-Data.org en temps réel ({source})",
                live_data
            )

        return {
            "question": question,
            "source": source,
            "league": league,
            "cypher": cypher,
            "records": records,
            "live_data": live_data,
            "error": error,
            "answer": answer
        }


def main():
    rag = GraphRAG()

    print("=" * 65)
    print("  ASSISTANT GRAPH RAG FOOTBALL (Neo4j + API Live + Groq)")
    print("  Sources : Graphe de connaissances (2019-2024)")
    print("            + API Football-Data.org (temps réel)")
    print("  Posez directement vos questions (ou 'exit' pour quitter)")
    print("=" * 65)

    while True:
        try:
            user_q = input("\n⚽ Votre question : ").strip()
            if not user_q or user_q.lower() in ["exit", "quit", "q"]:
                print("\nFin de la session Graph RAG. À bientôt !")
                break

            print("\n⚙️  Routage, interrogation et génération en cours...")
            res = rag.ask(user_q)

            # Affichage selon la source utilisée
            source_label = "Neo4j (Graphe historique)" if res["source"] == "neo4j" else f"API Live ({res['source']})"
            print(f"\n📡 Source utilisée : {source_label}")

            if res["cypher"]:
                print(f"\n🔮 Requête Cypher générée :\n{res['cypher']}")
                print(f"\n📊 Faits certifiés extraits ({len(res['records'])} enregistrements) :")
                for i, rec in enumerate(res["records"][:5], 1):
                    print(f"   [{i}] {rec}")
                if len(res["records"]) > 5:
                    print(f"   ... et {len(res['records']) - 5} autres enregistrements.")

            if res["live_data"]:
                print(f"\n📊 Données temps réel :\n{res['live_data']}")

            print(f"\n🤖 Réponse synthétisée :\n{res['answer']}")
            print("-" * 65)

        except (KeyboardInterrupt, EOFError):
            print("\nInterruption.")
            break

    rag.close()


if __name__ == "__main__":
    main()
