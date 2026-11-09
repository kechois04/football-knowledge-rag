"""
Module d'interrogation en direct de l'API Football-Data.org (v4).
Permet de récupérer les classements, meilleurs buteurs et résultats récents en direct.
Utilisé comme source de données temps réel dans le projet RAG.
"""

import os
import sys
import requests
from dotenv import load_dotenv

# Sécuriser l'encodage du terminal Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

load_dotenv()

# Clé API Football-Data.org (gratuite, plan Free tier)
FOOTBALL_DATA_API_KEY = os.getenv("FOOTBALL_DATA_API_KEY", "1aa839a77b7248eab1938752937f71ee")

BASE_URL = "https://api.football-data.org/v4"
HEADERS = {"X-Auth-Token": FOOTBALL_DATA_API_KEY}

# Correspondance des noms de ligue courants vers les codes API
LEAGUE_CODES = {
    "laliga": "PD",
    "la liga": "PD",
    "liga": "PD",
    "premier league": "PL",
    "pl": "PL",
    "bundesliga": "BL1",
    "serie a": "SA",
    "ligue 1": "FL1",
    "champions league": "CL",
    "ldc": "CL",
}


def get_top_scorers(league: str = "laliga", limit: int = 10) -> str:
    """Récupère le classement actuel des meilleurs buteurs d'un championnat."""
    code = LEAGUE_CODES.get(league.lower().strip(), league.upper())
    url = f"{BASE_URL}/competitions/{code}/scorers?limit={limit}"

    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            data = r.json()
            comp_name = data.get("competition", {}).get("name", league)
            season = data.get("season", {}).get("startDate", "")[:4]
            scorers = data.get("scorers", [])

            output = [f"Meilleurs buteurs actuels - {comp_name} ({season}) :"]
            for s in scorers:
                player = s["player"]["name"]
                team = s["team"]["name"]
                goals = s["goals"]
                assists = s.get("assists") or 0
                output.append(f"- {player} ({team}) : {goals} buts ({assists} passes)")
            return "\n".join(output)
        else:
            return f"Erreur API ({r.status_code}) : Impossible de récupérer les buteurs."
    except Exception as e:
        return f"Erreur de connexion : {e}"


def get_standings(league: str = "laliga", top_n: int = None) -> str:
    """Récupère le classement actuel d'un championnat complet (ou top_n équipes)."""
    code = LEAGUE_CODES.get(league.lower().strip(), league.upper())
    url = f"{BASE_URL}/competitions/{code}/standings"

    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            data = r.json()
            comp_name = data.get("competition", {}).get("name", league)
            standings_table = data["standings"][0]["table"]
            if top_n:
                standings_table = standings_table[:top_n]

            output = [f"Classement actuel complet - {comp_name} :"]
            for pos in standings_table:
                rank = pos["position"]
                team = pos["team"]["name"]
                points = pos["points"]
                played = pos["playedGames"]
                gd = pos.get("goalDifference", 0)
                output.append(f"{rank}. {team} - {points} pts ({played} matchs, diff: {gd:+d})")
            return "\n".join(output)
        else:
            return f"Erreur API ({r.status_code}) : Impossible de récupérer le classement."
    except Exception as e:
        return f"Erreur de connexion : {e}"


def get_recent_matches(league: str = "premier league", limit: int = 10) -> str:
    """Récupère les derniers résultats d'un championnat (une journée complète)."""
    code = LEAGUE_CODES.get(league.lower().strip(), league.upper())
    url = f"{BASE_URL}/competitions/{code}/matches?status=FINISHED&limit={limit}"

    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            data = r.json()
            comp_name = data.get("competition", {}).get("name", league)
            matches = data.get("matches", [])[-limit:]

            output = [f"Derniers résultats - {comp_name} :"]
            for m in matches:
                home = m["homeTeam"]["name"]
                away = m["awayTeam"]["name"]
                home_goals = m["score"]["fullTime"]["home"]
                away_goals = m["score"]["fullTime"]["away"]
                date = m.get("utcDate", "")[:10]
                matchday = m.get("matchday", "?")
                output.append(f"- J{matchday} ({date}) : {home} {home_goals}-{away_goals} {away}")
            return "\n".join(output)
        else:
            return f"Erreur API ({r.status_code}) : Impossible de récupérer les matchs."
    except Exception as e:
        return f"Erreur de connexion : {e}"


# Liste des fonctions disponibles et leur description (pour l'intégration LLM)
AVAILABLE_FUNCTIONS = {
    "get_top_scorers": {
        "fn": get_top_scorers,
        "description": "Récupère les meilleurs buteurs actuels d'un championnat donné.",
        "params": {"league": "Nom du championnat (ex: 'premier league', 'laliga', 'ligue 1')", "limit": "Nombre de résultats (défaut: 5)"}
    },
    "get_standings": {
        "fn": get_standings,
        "description": "Récupère le classement actuel d'un championnat donné.",
        "params": {"league": "Nom du championnat", "top_n": "Nombre d'équipes à afficher (défaut: 5)"}
    },
    "get_recent_matches": {
        "fn": get_recent_matches,
        "description": "Récupère les derniers résultats d'un championnat donné.",
        "params": {"league": "Nom du championnat", "limit": "Nombre de matchs (défaut: 5)"}
    },
}


if __name__ == "__main__":
    # Test local :
    print(get_top_scorers("laliga"))
    print()
    print(get_standings("premier league"))
    print()
    print(get_recent_matches("ligue 1"))
