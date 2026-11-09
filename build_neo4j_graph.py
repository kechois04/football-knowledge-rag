"""
Script d'ingestion et de construction du Graphe de Connaissances dans Neo4j.
Lit les fichiers CSV dans sources_filtered/ et injecte les nœuds et relations :
- Competition, Club, Stadium, Player, Award
- Relations : PLAYS_AT, COMPETES_IN, CURRENT_CLUB, TRANSFERRED_TO, PLAYED_FOR (stats), WON_TROPHY, WON_AWARD
"""

import os
import sys
import time
import unicodedata
import pandas as pd
from dotenv import load_dotenv
from neo4j import GraphDatabase

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

load_dotenv()


def normalize_str(s: str) -> str:
    if not s:
        return ""
    return unicodedata.normalize("NFKD", str(s)).encode("ASCII", "ignore").decode("utf-8").lower().strip()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "football2024")

BATCH_SIZE = 1000


def run_batch(session, query: str, batch: list[dict]):
    """Exécute une requête Cypher avec un lot de paramètres UNWIND."""
    if batch:
        session.run(query, {"batch": batch})


def build_knowledge_graph():
    print("=" * 65)
    print("      CONSTRUCTION DU GRAPHE DE CONNAISSANCES NEO4J")
    print("=" * 65)

    start_time = time.time()
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    driver.verify_connectivity()

    with driver.session() as session:
        # 1. Nettoyage et initialisation des contraintes et index
        print("\n[1/8] Création des contraintes d'unicité et index...")
        constraints = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Club) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Player) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (comp:Competition) REQUIRE comp.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Stadium) REQUIRE s.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (a:Award) REQUIRE a.name IS UNIQUE",
            "CREATE INDEX IF NOT EXISTS FOR (p:Player) ON (p.name)",
            "CREATE INDEX IF NOT EXISTS FOR (p:Player) ON (p.name_normalized)",
            "CREATE INDEX IF NOT EXISTS FOR (p:Player) ON (p.code)",
            "CREATE INDEX IF NOT EXISTS FOR (c:Club) ON (c.name)",
            "CREATE INDEX IF NOT EXISTS FOR (c:Club) ON (c.name_normalized)",
        ]
        for c in constraints:
            session.run(c)
        print("  ✓ Contraintes et index créés.")

        # 2. Ingestion des Compétitions
        print("\n[2/8] Ingestion des compétitions (competitions.csv)...")
        df_comp = pd.read_csv("sources_filtered/competitions.csv").fillna("")
        comp_records = []
        for _, row in df_comp.iterrows():
            comp_records.append({
                "id": str(row["competition_id"]),
                "name": str(row["name"]),
                "code": str(row["competition_code"]),
                "country": str(row.get("country_name", "")),
                "type": str(row.get("type", ""))
            })
        session.run("""
            UNWIND $batch AS row
            MERGE (c:Competition {id: row.id})
            SET c.name = row.name,
                c.code = row.code,
                c.country = row.country,
                c.type = row.type
        """, {"batch": comp_records})
        print(f"  ✓ {len(comp_records)} compétitions insérées.")

        # 3. Ingestion des Clubs et Stades
        print("\n[3/8] Ingestion des clubs et stades (clubs.csv)...")
        df_clubs = pd.read_csv("sources_filtered/clubs.csv").fillna("")
        club_records = []
        for _, row in df_clubs.iterrows():
            club_records.append({
                "id": int(row["club_id"]),
                "code": str(row["club_code"]),
                "name": str(row["name"]),
                "name_normalized": normalize_str(row["name"]),
                "coach": str(row.get("coach_name", "")),
                "stadium_name": str(row.get("stadium_name", "")).strip(),
                "stadium_seats": int(row["stadium_seats"]) if str(row.get("stadium_seats", "")).replace(".0","").isdigit() else 0,
                "squad_size": int(row["squad_size"]) if str(row.get("squad_size", "")).isdigit() else 0,
                "domestic_comp_id": str(row.get("domestic_competition_id", ""))
            })
        
        # Clubs et Stades
        session.run("""
            UNWIND $batch AS row
            MERGE (c:Club {id: row.id})
            SET c.name = row.name,
                c.code = row.code,
                c.name_normalized = row.name_normalized,
                c.coach = row.coach,
                c.squad_size = row.squad_size
            
            WITH c, row
            WHERE row.stadium_name <> ''
            MERGE (s:Stadium {name: row.stadium_name})
            SET s.seats = row.stadium_seats
            MERGE (c)-[:PLAYS_AT]->(s)
            
            WITH c, row
            WHERE row.domestic_comp_id <> ''
            MERGE (comp:Competition {id: row.domestic_comp_id})
            MERGE (c)-[:COMPETES_IN]->(comp)
        """, {"batch": club_records})
        print(f"  ✓ {len(club_records)} clubs et leurs stades reliés.")

        # 4. Ingestion des Joueurs
        print("\n[4/8] Ingestion des joueurs (players.csv)...")
        df_players = pd.read_csv("sources_filtered/players.csv").fillna("")
        player_batches = []
        current_batch = []
        for _, row in df_players.iterrows():
            mv = int(float(row["market_value_in_eur"])) if str(row.get("market_value_in_eur", "")).replace(".0","").isdigit() else 0
            hmv = int(float(row["highest_market_value_in_eur"])) if str(row.get("highest_market_value_in_eur", "")).replace(".0","").isdigit() else 0
            current_club_id = int(float(row["current_club_id"])) if str(row.get("current_club_id", "")).replace(".0","").isdigit() else 0
            
            current_batch.append({
                "id": int(row["player_id"]),
                "name": str(row["name"]),
                "code": str(row.get("player_code", "")).lower().strip(),
                "name_normalized": normalize_str(row["name"]),
                "position": str(row.get("position", "")),
                "sub_position": str(row.get("sub_position", "")),
                "nationality": str(row.get("country_of_citizenship", "")),
                "date_of_birth": str(row.get("date_of_birth", "")),
                "foot": str(row.get("foot", "")),
                "market_value": mv,
                "highest_market_value": hmv,
                "current_club_id": current_club_id
            })
            if len(current_batch) >= BATCH_SIZE:
                player_batches.append(current_batch)
                current_batch = []
        if current_batch:
            player_batches.append(current_batch)

        for b in player_batches:
            session.run("""
                UNWIND $batch AS row
                MERGE (p:Player {id: row.id})
                SET p.name = row.name,
                    p.code = row.code,
                    p.name_normalized = row.name_normalized,
                    p.position = row.position,
                    p.sub_position = row.sub_position,
                    p.nationality = row.nationality,
                    p.date_of_birth = row.date_of_birth,
                    p.foot = row.foot,
                    p.market_value = row.market_value,
                    p.highest_market_value = row.highest_market_value
                
                WITH p, row
                WHERE row.current_club_id > 0
                MATCH (c:Club {id: row.current_club_id})
                MERGE (p)-[:CURRENT_CLUB]->(c)
            """, {"batch": b})
        print(f"  ✓ {len(df_players)} joueurs créés et reliés à leur club actuel.")

        # 5. Ingestion des Transferts
        print("\n[5/8] Ingestion de l'historique des transferts (transfers.csv)...")
        df_transfers = pd.read_csv("sources_filtered/transfers.csv").fillna("")
        transfer_batches = []
        current_batch = []
        for _, row in df_transfers.iterrows():
            pid = int(float(row["player_id"])) if str(row.get("player_id", "")).replace(".0","").isdigit() else 0
            to_cid = int(float(row["to_club_id"])) if str(row.get("to_club_id", "")).replace(".0","").isdigit() else 0
            from_cid = int(float(row["from_club_id"])) if str(row.get("from_club_id", "")).replace(".0","").isdigit() else 0
            fee = int(float(row["transfer_fee"])) if str(row.get("transfer_fee", "")).replace(".0","").isdigit() else 0

            if pid > 0 and to_cid > 0:
                current_batch.append({
                    "player_id": pid,
                    "to_club_id": to_cid,
                    "from_club_id": from_cid,
                    "from_club_name": str(row.get("from_club_name", "")),
                    "to_club_name": str(row.get("to_club_name", "")),
                    "season": str(row.get("transfer_season", "")),
                    "date": str(row.get("transfer_date", "")),
                    "fee": fee
                })
                if len(current_batch) >= BATCH_SIZE:
                    transfer_batches.append(current_batch)
                    current_batch = []
        if current_batch:
            transfer_batches.append(current_batch)

        for b in transfer_batches:
            session.run("""
                UNWIND $batch AS row
                MATCH (p:Player {id: row.player_id})
                MATCH (to_c:Club {id: row.to_club_id})
                CREATE (p)-[t:TRANSFERRED_TO {
                    season: row.season,
                    date: row.date,
                    fee: row.fee,
                    from_club_id: row.from_club_id,
                    from_club_name: row.from_club_name,
                    to_club_name: row.to_club_name
                }]->(to_c)
            """, {"batch": b})
        print(f"  ✓ {len(df_transfers)} transferts historiques enregistrés.")

        # 6. Statistiques de carrière agrégées (appearances.csv)
        print("\n[6/8] Agrégation des statistiques de carrière (appearances.csv)...")
        df_app = pd.read_csv("sources_filtered/appearances.csv", usecols=[
            "player_id", "player_club_id", "goals", "assists", "minutes_played", "yellow_cards", "red_cards"
        ]).fillna(0)
        
        agg = df_app.groupby(["player_id", "player_club_id"]).agg({
            "goals": "sum",
            "assists": "sum",
            "minutes_played": "sum",
            "yellow_cards": "sum",
            "red_cards": "sum",
            "player_id": "count"
        }).rename(columns={"player_id": "matches"}).reset_index()

        stat_batches = []
        current_batch = []
        for _, row in agg.iterrows():
            current_batch.append({
                "player_id": int(row["player_id"]),
                "club_id": int(row["player_club_id"]),
                "matches": int(row["matches"]),
                "goals": int(row["goals"]),
                "assists": int(row["assists"]),
                "minutes": int(row["minutes_played"]),
                "yellow_cards": int(row["yellow_cards"]),
                "red_cards": int(row["red_cards"])
            })
            if len(current_batch) >= BATCH_SIZE:
                stat_batches.append(current_batch)
                current_batch = []
        if current_batch:
            stat_batches.append(current_batch)

        for b in stat_batches:
            session.run("""
                UNWIND $batch AS row
                MATCH (p:Player {id: row.player_id})
                MATCH (c:Club {id: row.club_id})
                MERGE (p)-[r:PLAYED_FOR]->(c)
                SET r.matches = row.matches,
                    r.goals = row.goals,
                    r.assists = row.assists,
                    r.minutes = row.minutes,
                    r.yellow_cards = row.yellow_cards,
                    r.red_cards = row.red_cards
            """, {"batch": b})
        print(f"  ✓ {len(agg)} relations PLAYED_FOR avec statistiques globales enregistrées.")

        # 7. Palmarès des clubs (trophies.csv)
        print("\n[7/8] Ingestion des trophées par club (trophies.csv)...")
        df_trophies = pd.read_csv("sources_filtered/trophies.csv").fillna("")
        trophy_records = []
        for _, row in df_trophies.iterrows():
            trophy_records.append({
                "season": str(row["season"]),
                "competition_id": str(row["competition"]),
                "winner_code": str(row["winner_club_code"]),
                "runner_up_code": str(row["runner_up_club_code"])
            })
        session.run("""
            UNWIND $batch AS row
            MATCH (comp:Competition {id: row.competition_id})
            MATCH (winner:Club {code: row.winner_code})
            MERGE (winner)-[:WON_TROPHY {season: row.season}]->(comp)
            
            WITH row, comp
            MATCH (runner:Club {code: row.runner_up_code})
            MERGE (runner)-[:RUNNER_UP {season: row.season}]->(comp)
        """, {"batch": trophy_records})
        print(f"  ✓ {len(trophy_records)} trophées et finales enregistrés.")

        # 8. Distinctions individuelles (individual_awards.csv)
        print("\n[8/8] Ingestion des récompenses individuelles (individual_awards.csv)...")
        df_awards = pd.read_csv("sources_filtered/individual_awards.csv").fillna("")
        award_records = []
        for _, row in df_awards.iterrows():
            award_records.append({
                "season": str(row["season"]),
                "award_name": str(row["award_name"]),
                "player_id": int(row["player_id"]),
                "player_name": str(row["player_name"]),
                "details": str(row.get("details", ""))
            })
        session.run("""
            UNWIND $batch AS row
            MERGE (a:Award {name: row.award_name})
            WITH a, row
            MATCH (p:Player {id: row.player_id})
            MERGE (p)-[:WON_AWARD {season: row.season, details: row.details}]->(a)
        """, {"batch": award_records})
        print(f"  ✓ {len(award_records)} distinctions individuelles reliées aux joueurs.")

        # Résumé final
        print("\n" + "=" * 65)
        res_nodes = session.run("MATCH (n) RETURN count(n) AS total_nodes").single()["total_nodes"]
        res_rels = session.run("MATCH ()-[r]->() RETURN count(r) AS total_rels").single()["total_rels"]
        print(f"✅ Graphe construit avec succès en {time.time() - start_time:.1f}s !")
        print(f"📊 Total Nœuds dans Neo4j     : {res_nodes:,}")
        print(f"🔗 Total Relations dans Neo4j : {res_rels:,}")
        print("=" * 65)

    driver.close()


if __name__ == "__main__":
    build_knowledge_graph()
