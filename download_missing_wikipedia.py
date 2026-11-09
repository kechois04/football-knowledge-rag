"""
Script de téléchargement ciblé des fiches Wikipédia MANQUANTES.
- Détecte automatiquement les clubs et joueurs qui ne sont PAS encore dans corpus_wikipedia/
- Priorise spécifiquement :
    1. Tous les gagnants de récompenses individuelles (Messi, Benzema, Ronaldo, Jorginho...)
    2. Les légendes historiques (record de valeur marchande >= 40M€ : Ramos, Piqué, Ibrahimović...)
    3. Les meilleurs buteurs de 2019 à 2024 (>= 15 buts)
    4. Les 11 clubs restants
- Ignore systématiquement tous les fichiers déjà téléchargés avec succès.
"""

import os
import glob
import time
import requests
import pandas as pd

# ================= Configuration =================
CLUBS_CSV = "sources_filtered/clubs.csv"
PLAYERS_CSV = "sources_filtered/players.csv"
AWARDS_CSV = "sources_filtered/individual_awards.csv"
APPS_CSV = "sources_filtered/appearances.csv"
OUTPUT_DIR = "corpus_wikipedia"

LANG = "fr"
MAX_CHARS_PER_ARTICLE = 25000

HEADERS = {
    "User-Agent": "ProjetRAGMasterMissing/2.0 (etudiant@universite.fr) PythonRequests/2.31"
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
    except Exception as e:
        print(f"  [Recherche] Erreur pour '{query}': {e}")
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
    except Exception as e:
        print(f"  [Article] Erreur pour '{title}': {e}")
    return None


def get_wiki_content(query: str, lang: str = "fr", session: requests.Session = None) -> dict | None:
    """Cherche la page et extrait le contenu (français avec repli anglais)."""
    title = search_wikipedia_title(query, lang=lang, session=session)
    if title:
        data = fetch_full_article(title, lang=lang, session=session)
        if data:
            return data

    if lang != "en":
        title_en = search_wikipedia_title(query, lang="en", session=session)
        if title_en:
            data_en = fetch_full_article(title_en, lang="en", session=session)
            if data_en:
                return data_en

    return None


def identify_missing_players(existing_pids: set[int]) -> pd.DataFrame:
    """Identifie les joueurs clés non encore téléchargés."""
    players = pd.read_csv(PLAYERS_CSV, encoding="utf-8")
    awards = pd.read_csv(AWARDS_CSV, encoding="utf-8")
    apps = pd.read_csv(APPS_CSV, usecols=["player_id", "goals"])

    # 1. Tous les gagnants de trophées individuels
    award_pids = set(awards["player_id"])

    # 2. Joueurs à forte valeur historique (pic >= 40M€ : Messi, Ronaldo, Ramos, Benzema...)
    high_mv_pids = set(players[players["highest_market_value_in_eur"] >= 40_000_000]["player_id"])

    # 3. Meilleurs buteurs sur la période (>= 15 buts)
    player_goals = apps.groupby("player_id")["goals"].sum()
    top_scorers_pids = set(player_goals[player_goals >= 15].index)

    # Union de tous les joueurs prioritaires
    priority_pids = award_pids.union(high_mv_pids).union(top_scorers_pids)

    # Filtrer ceux qui manquent
    missing_pids = priority_pids - existing_pids
    missing_df = players[players["player_id"].isin(missing_pids)].copy()

    # Trier pour faire passer les trophées et les plus grands noms en premier
    missing_df["is_award"] = missing_df["player_id"].isin(award_pids)
    missing_df.sort_values(
        by=["is_award", "highest_market_value_in_eur"],
        ascending=[False, False],
        inplace=True
    )
    return missing_df


def identify_missing_clubs(existing_cids: set[int]) -> pd.DataFrame:
    """Identifie les clubs restants non encore téléchargés."""
    clubs = pd.read_csv(CLUBS_CSV, encoding="latin-1")
    missing_clubs = clubs[~clubs["club_id"].isin(existing_cids)].copy()
    return missing_clubs


def main():
    os.makedirs(f"{OUTPUT_DIR}/clubs", exist_ok=True)
    os.makedirs(f"{OUTPUT_DIR}/players", exist_ok=True)

    session = requests.Session()

    existing_clubs = get_existing_ids("clubs")
    existing_players = get_existing_ids("players")

    print("=" * 60)
    print(f"État actuel : {len(existing_clubs)} clubs et {len(existing_players)} joueurs déjà téléchargés.")
    print("=" * 60)

    # --- 1. CLUBS MANQUANTS ---
    missing_clubs = identify_missing_clubs(existing_clubs)
    print(f"\n[Clubs] {len(missing_clubs)} club(s) manquant(s) à traiter.")
    clubs_saved = 0
    for idx, row in missing_clubs.reset_index().iterrows():
        cid = row["club_id"]
        cname = row["name"]
        file_path = f"{OUTPUT_DIR}/clubs/club_{cid}.txt"

        query = f"{cname} football"
        content = get_wiki_content(query, lang=LANG, session=session)
        if content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"ID: {cid}\nType: Club\nNom: {cname}\nTitre: {content['title']}\nURL: {content['url']}\n")
                f.write(f"Longueur: {len(content['extract'])} car.\n\n=== CONTENU INTÉGRAL ===\n")
                f.write(content["extract"])
            clubs_saved += 1
            print(f"  + [{idx+1}/{len(missing_clubs)}] Club : {cname} ({len(content['extract'])} car.)")
        else:
            print(f"  - [{idx+1}/{len(missing_clubs)}] Non trouvé : {cname}")
        time.sleep(0.12)

    # --- 2. JOUEURS MANQUANTS (Stars, Lauréats & Buteurs) ---
    missing_players = identify_missing_players(existing_players)
    print(f"\n[Joueurs] {len(missing_players)} joueur(s) manquant(s) prioritaire(s) identifié(s).")
    print("Exemples prioritaires : Messi, Cristiano Ronaldo, Benzema, Ramos, Ibrahimović, etc.\n")

    players_saved = 0
    for idx, row in missing_players.reset_index().iterrows():
        pid = row["player_id"]
        pname = row["name"]
        file_path = f"{OUTPUT_DIR}/players/player_{pid}.txt"

        query = f"{pname} football"
        content = get_wiki_content(query, lang=LANG, session=session)
        if content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"ID: {pid}\nType: Joueur\nNom: {pname}\nTitre: {content['title']}\nURL: {content['url']}\n")
                f.write(f"Longueur: {len(content['extract'])} car.\n\n=== CONTENU INTÉGRAL ===\n")
                f.write(content["extract"])
            players_saved += 1
            print(f"  + [{idx+1}/{len(missing_players)}] Joueur : {pname} ({len(content['extract'])} car.)")
        else:
            print(f"  - [{idx+1}/{len(missing_players)}] Non trouvé : {pname}")
        time.sleep(0.12)

    print("\n" + "=" * 60)
    print("Mise à jour terminée avec succès !")
    print(f"Nouveaux clubs enregistrés : {clubs_saved}")
    print(f"Nouveaux joueurs enregistrés : {players_saved}")
    print(f"Total fiches clubs disponibles : {len(get_existing_ids('clubs'))}")
    print(f"Total fiches joueurs disponibles : {len(get_existing_ids('players'))}")
    print("=" * 60)


if __name__ == "__main__":
    main()
