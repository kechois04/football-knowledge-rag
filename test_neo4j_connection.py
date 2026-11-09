"""Test la connexion à l'instance Neo4j Docker."""
import os
import sys
from dotenv import load_dotenv
from neo4j import GraphDatabase

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

load_dotenv()

uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
user = os.getenv("NEO4J_USER", "neo4j")
password = os.getenv("NEO4J_PASSWORD", "football2024")

print(f"Tentative de connexion à Neo4j ({uri}) en tant que '{user}'...")

try:
    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        driver.verify_connectivity()
        with driver.session() as session:
            result = session.run("RETURN 'Connexion Neo4j réussie ! Version : ' + apoc.version() AS msg")
            record = result.single()
            if record:
                print("✅", record["msg"])
            else:
                result2 = session.run("RETURN 'Connexion Neo4j réussie !' AS msg")
                print("✅", result2.single()["msg"])
except Exception as e:
    # Si APOC n'est pas encore initialisé, tester un simple RETURN 1
    try:
        with GraphDatabase.driver(uri, auth=(user, password)) as driver:
            with driver.session() as session:
                res = session.run("RETURN 'Connexion Neo4j réussie sans APOC' AS msg")
                print("✅", res.single()["msg"])
    except Exception as e2:
        print("❌ Échec de la connexion :", e2)
