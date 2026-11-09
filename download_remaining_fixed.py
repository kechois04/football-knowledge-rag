"""
Script de téléchargement définitif pour les clubs et joueurs manquants.
Résout spécifiquement le problème de typographie / accents :
1. Configure l'encodage de la console en UTF-8 pour éviter les erreurs d'affichage.
2. Utilise le 'player_code' et 'club_code' (noms normalisés sans accents) comme repli infaillible.
3. Recherche d'abord sur Wikipédia FR, puis sur Wikipédia EN si nécessaire.
4. Ne télécharge QUE les éléments manquants (11 clubs et ~85 joueurs restants).
"""

import os
import sys
import glob
import time
import requests
import pandas as pd

# Sécuriser l'encodage du terminal Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ================= Configuration =================
CLUBS_CSV = "sources_filtered/clubs.csv"
PLAYERS_CSV = "sources_filtered/players.csv"
AWARDS_CSV = "sources_filtered/individual_awards.csv"
APPS_CSV = "sources_filtered/appearances.csv"
OUTPUT_DIR = "corpus_wikipedia"

MAX_CHARS_PER_ARTICLE = 25000

HEADERS = {
    "User-Agent": "ProjetRAGMasterFinal/3.0 (etudiant@universite.fr) PythonRequests/2.31"
}
# =================================================


def get_existing_ids(subfolder: str) -> set[int]:
    """Récupère l'ensemble des IDs déjà enregistrés avec un fichier non vide (> 300 octets)."""
    existing = set()
    pattern = os.path.join(OUTPUT_DIR, subfolder, "*_*.txt")
    for f in glob.glob(pattern):
        try:
            if os.path.getsize(f) > 300:
                basename = os.path.basename(f)
                entity_id = int(basename.split("_")[1].split(".")[0])
                existing.add(entity_id)
        except Exception:
            continue
    return existing


def search_wikipedia_title(query: str, lang: str = "fr", session: requests.Session = None) -> str | None:
    """Recherche le titre exact d'une page Wikipédia."""
    s = session or requests
    url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "format": "json",
        "srlimit": 1,
        "utf8": 1,
    }
    try:
        r = s.get(url, params=params, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            results = r.json().get("query", {}).get("search", [])
            if results:
                return results[0]["title"]
    except Exception:
        pass
    return None


def fetch_full_article(title: str, lang: str = "fr", session: requests.Session = None) -> dict | None:
    """Récupère le texte complet structuré de l'article via l'Action API."""
    s = session or requests
    url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "prop": "extracts|info",
        "inprop": "url",
        "explaintext": 1,
        "titles": title,
        "redirects": 1,
        "format": "json",
    }
    try:
        r = s.get(url, params=params, headers=HEADERS, timeout=12)
        if r.status_code == 200:
            pages = r.json().get("query", {}).get("pages", {})
            for pid, pdata in pages.items():
                if pid != "-1":
                    text = pdata.get("extract", "").strip()
                    if text:
                        if MAX_CHARS_PER_ARTICLE and len(text) > MAX_CHARS_PER_ARTICLE:
                            text = text[:MAX_CHARS_PER_ARTICLE] + "\n\n[... Suite de l'article tronquée pour le RAG ...]"
                        return {
                            "title": pdata.get("title", title),
                            "extract": text,
                            "url": pdata.get("fullurl", f"https://{lang}.wikipedia.org/wiki/{title}"),
                        }
    except Exception:
        pass
    return None


def robust_wiki_fetch(name: str, code: str, session: requests.Session) -> dict | None:
    """
    Stratégie multi-niveaux :
    1. Nom original sur WP FR
    2. Code normalisé sans tirets sur WP FR
    3. Nom / Code sur WP EN (repli)
    """
    clean_code = str(code).replace("-", " ")
    queries = [
        f"{name} football",
        f"{clean_code} football",
        name,
        clean_code,
    ]

    # Essai sur Wikipédia FR
    for q in queries:
        title = search_wikipedia_title(q, lang="fr", session=session)
        if title:
            data = fetch_full_article(title, lang="fr", session=session)
            if data:
                return data

    # Repli sur Wikipédia EN
    for q in queries:
        title = search_wikipedia_title(q, lang="en", session=session)
        if title:
            data = fetch_full_article(title, lang="en", session=session)
            if data:
                return data

    return None


def main():
    os.makedirs(f"{OUTPUT_DIR}/clubs", exist_ok=True)
    os.makedirs(f"{OUTPUT_DIR}/players", exist_ok=True)

    session = requests.Session()

    existing_clubs = get_existing_ids("clubs")
    existing_players = get_existing_ids("players")

    print("=" * 60)
    print(f"État actuel : {len(existing_clubs)} clubs et {len(existing_players)} joueurs disponibles.")
    print("=" * 60)

    # ---------------- 1. TRAITEMENT DES CLUBS MANQUANTS ----------------
    clubs_df = pd.read_csv(CLUBS_CSV, encoding="utf-8")
    missing_clubs = clubs_df[~clubs_df["club_id"].isin(existing_clubs)].copy()
    print(f"\n[1/2] Traitement des {len(missing_clubs)} club(s) manquant(s)...")

    clubs_saved = 0
    for idx, row in missing_clubs.reset_index().iterrows():
        cid = row["club_id"]
        cname = row["name"]
        ccode = row["club_code"]
        file_path = f"{OUTPUT_DIR}/clubs/club_{cid}.txt"

        content = robust_wiki_fetch(cname, ccode, session)
        if content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"ID: {cid}\nType: Club\nNom: {cname}\nCode: {ccode}\nTitre: {content['title']}\nURL: {content['url']}\n")
                f.write(f"Longueur: {len(content['extract'])} car.\n\n=== CONTENU INTÉGRAL ===\n")
                f.write(content["extract"])
            clubs_saved += 1
            print(f"  + [{idx+1}/{len(missing_clubs)}] Club récupéré : {cname} -> {content['title']} ({len(content['extract'])} car.)")
        else:
            print(f"  - [{idx+1}/{len(missing_clubs)}] Échec pour : {cname} (code: {ccode})")
        time.sleep(0.12)

    # ---------------- 2. TRAITEMENT DES JOUEURS MANQUANTS ----------------
    players_df = pd.read_csv(PLAYERS_CSV, encoding="utf-8")
    awards_df = pd.read_csv(AWARDS_CSV, encoding="utf-8")
    apps_df = pd.read_csv(APPS_CSV, usecols=["player_id", "goals"])

    # Joueurs prioritaires
    award_pids = set(awards_df["player_id"])
    high_mv_pids = set(players_df[players_df["highest_market_value_in_eur"] >= 40_000_000]["player_id"])
    player_goals = apps_df.groupby("player_id")["goals"].sum()
    top_scorers_pids = set(player_goals[player_goals >= 15].index)

    priority_pids = award_pids.union(high_mv_pids).union(top_scorers_pids)
    missing_pids = priority_pids - existing_players

    missing_players = players_df[players_df["player_id"].isin(missing_pids)].copy()
    print(f"\n[2/2] Traitement des {len(missing_players)} joueur(s) manquant(s) (stars & accents)...")

    players_saved = 0
    for idx, row in missing_players.reset_index().iterrows():
        pid = row["player_id"]
        pname = row["name"]
        pcode = row["player_code"]
        file_path = f"{OUTPUT_DIR}/players/player_{pid}.txt"

        content = robust_wiki_fetch(pname, pcode, session)
        if content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"ID: {pid}\nType: Joueur\nNom: {pname}\nCode: {pcode}\nTitre: {content['title']}\nURL: {content['url']}\n")
                f.write(f"Longueur: {len(content['extract'])} car.\n\n=== CONTENU INTÉGRAL ===\n")
                f.write(content["extract"])
            players_saved += 1
            print(f"  + [{idx+1}/{len(missing_players)}] Joueur récupéré : {pname} -> {content['title']} ({len(content['extract'])} car.)")
        else:
            print(f"  - [{idx+1}/{len(missing_players)}] Échec pour : {pname} (code: {pcode})")
        time.sleep(0.12)

    total_clubs = len(get_existing_ids("clubs"))
    total_players = len(get_existing_ids("players"))

    print("\n" + "=" * 60)
    print("Mise à jour terminée avec succès !")
    print(f"Nouveaux clubs ajoutés : {clubs_saved}")
    print(f"Nouveaux joueurs ajoutés : {players_saved}")
    print(f"TOTAL CLUBS DANS LE CORPUS : {total_clubs} / {len(clubs_df)}")
    print(f"TOTAL JOUEURS DANS LE CORPUS : {total_players}")
    print("=" * 60)


if __name__ == "__main__":
    main()
