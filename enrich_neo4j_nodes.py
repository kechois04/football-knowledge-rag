"""
Enrichit les nœuds Player et Club dans Neo4j avec name_normalized et code
pour permettre des recherches insensibles aux accents (ex: mbappe -> Kylian Mbappé).
"""
import os
import sys
import unicodedata
import pandas as pd
from dotenv import load_dotenv
from neo4j import GraphDatabase

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "football2024")


def normalize_str(s: str) -> str:
    if not s:
        return ""
    return unicodedata.normalize("NFKD", str(s)).encode("ASCII", "ignore").decode("utf-8").lower().strip()


def enrich():
    print("Connexion à Neo4j pour l'enrichissement...")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    with driver.session() as session:
        # 1. Enrichir les Joueurs
        df_players = pd.read_csv("sources_filtered/players.csv").fillna("")
        batch = []
        for _, row in df_players.iterrows():
            batch.append({
                "id": int(row["player_id"]),
                "code": str(row.get("player_code", "")).lower().strip(),
                "name_normalized": normalize_str(row["name"])
            })
        
        session.run("""
            UNWIND $batch AS row
            MATCH (p:Player {id: row.id})
            SET p.code = row.code,
                p.name_normalized = row.name_normalized
        """, {"batch": batch})
        print(f"✓ {len(batch)} Joueurs enrichis avec 'code' et 'name_normalized'.")

        # Index sur name_normalized pour des perfs instantanées
        session.run("CREATE INDEX IF NOT EXISTS FOR (p:Player) ON (p.name_normalized)")
        session.run("CREATE INDEX IF NOT EXISTS FOR (p:Player) ON (p.code)")

        # 2. Enrichir les Clubs
        df_clubs = pd.read_csv("sources_filtered/clubs.csv").fillna("")
        club_batch = []
        for _, row in df_clubs.iterrows():
            club_batch.append({
                "id": int(row["club_id"]),
                "code": str(row.get("club_code", "")).lower().strip(),
                "name_normalized": normalize_str(row["name"])
            })
        
        session.run("""
            UNWIND $batch AS row
            MATCH (c:Club {id: row.id})
            SET c.code = row.code,
                c.name_normalized = row.name_normalized
        """, {"batch": club_batch})
        print(f"✓ {len(club_batch)} Clubs enrichis avec 'name_normalized'.")

        session.run("CREATE INDEX IF NOT EXISTS FOR (c:Club) ON (c.name_normalized)")

    driver.close()
    print("Enrichissement terminé avec succès !")


if __name__ == "__main__":
    enrich()
