"""
Script de téléchargement des articles complets Wikipédia pour le Naive RAG.
Télécharge le texte intégral (Histoire, Carrière, Palmarès, Statistiques)
des clubs et des joueurs majeurs depuis l'API Wikipédia MediaWiki (explaintext=1).
"""

import os
import time
import requests
import pandas as pd

# ================= Configuration =================
CLUBS_CSV = "sources_filtered/clubs.csv"
PLAYERS_CSV = "sources_filtered/players.csv"
OUTPUT_DIR = "corpus_wikipedia"

# Langue principale ('fr' ou 'en')
LANG = "fr"

# Nombre de joueurs majeurs à télécharger
TOP_N_PLAYERS = 1000

# Limite maximale de caractères par article pour éviter les textes démesurés (None = tout garder)
# 25 000 caractères correspond à environ 4 000 mots (~10-15 pages de texte riche)
MAX_CHARS_PER_ARTICLE = 25000

# User-Agent obligatoire selon la politique de l'API Wikimedia
HEADERS = {
    "User-Agent": "ProjetRAGMaster/2.0 (etudiant@universite.fr) PythonRequests/2.31"
}
# =================================================


def search_wikipedia_title(query: str, lang: str = "fr", session: requests.Session = None) -> str | None:
    """Recherche le titre exact d'une page Wikipédia correspondant à une requête."""
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
        print(f"Erreur recherche pour '{query}': {e}")
    return None


def fetch_full_article(title: str, lang: str = "fr", session: requests.Session = None) -> dict | None:
    """
    Récupère le texte INTÉGRAL de l'article Wikipédia (avec toutes les sections :
    Carrière, Palmarès, Historique, etc.) en texte brut propre (sans balises HTML).
    """
    s = session or requests
    url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "prop": "extracts|info",
        "inprop": "url",
        "explaintext": 1,   # Extrait le texte brut sans HTML
        "titles": title,
        "redirects": 1,     # Suit automatiquement les redirections
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
                        # Tronquage propre si l'article dépasse la limite
                        if MAX_CHARS_PER_ARTICLE and len(text) > MAX_CHARS_PER_ARTICLE:
                            text = text[:MAX_CHARS_PER_ARTICLE] + "\n\n[... Suite de l'article tronquée pour le RAG ...]"
                        return {
                            "title": pdata.get("title", title),
                            "extract": text,
                            "url": pdata.get("fullurl", f"https://{lang}.wikipedia.org/wiki/{title}"),
                        }
    except Exception as e:
        print(f"Erreur récupération article complet pour '{title}': {e}")
    return None


def get_wiki_content(query: str, lang: str = "fr", session: requests.Session = None) -> dict | None:
    """Cherche la page et extrait le contenu complet (avec repli en anglais si non trouvé)."""
    # 1. Essai en français
    title = search_wikipedia_title(query, lang=lang, session=session)
    if title:
        data = fetch_full_article(title, lang=lang, session=session)
        if data:
            return data

    # 2. Repli en anglais si la langue initiale était le français
    if lang != "en":
        title_en = search_wikipedia_title(query, lang="en", session=session)
        if title_en:
            data_en = fetch_full_article(title_en, lang="en", session=session)
            if data_en:
                return data_en

    return None


def main():
    os.makedirs(f"{OUTPUT_DIR}/clubs", exist_ok=True)
    os.makedirs(f"{OUTPUT_DIR}/players", exist_ok=True)
    
    session = requests.Session()
    stats = {"clubs_saved": 0, "players_saved": 0}

    # ---------------- 1. Téléchargement des CLUBS ----------------
    print(f"\n--- 1. Téléchargement des articles Wikipédia complets pour les CLUBS ---")
    clubs_df = pd.read_csv(CLUBS_CSV, encoding="latin-1")
    for idx, row in clubs_df.iterrows():
        club_id = row["club_id"]
        club_name = row["name"]
        file_path = f"{OUTPUT_DIR}/clubs/club_{club_id}.txt"

        # On recherche avec "football" pour lever les ambiguïtés
        search_query = f"{club_name} football"
        content = get_wiki_content(search_query, lang=LANG, session=session)

        if content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"ID: {club_id}\n")
                f.write(f"Type: Club\n")
                f.write(f"Nom: {club_name}\n")
                f.write(f"Titre Wikipedia: {content['title']}\n")
                f.write(f"URL: {content['url']}\n")
                f.write(f"Longueur texte: {len(content['extract'])} caractères\n")
                f.write("\n=== CONTENU INTÉGRAL ===\n")
                f.write(content["extract"])
            stats["clubs_saved"] += 1
            print(f"[{idx+1}/{len(clubs_df)}] Club OK: {club_name} ({len(content['extract'])} car.)")
        else:
            print(f"[{idx+1}/{len(clubs_df)}] Non trouvé : {club_name}")

        time.sleep(0.12)  # Respect de l'API Wikimedia

    # ---------------- 2. Téléchargement des JOUEURS ----------------
    print(f"\n--- 2. Téléchargement des articles Wikipédia complets pour les JOUEURS (Top {TOP_N_PLAYERS}) ---")
    players_df = pd.read_csv(PLAYERS_CSV, encoding="latin-1")
    
    top_players = players_df.dropna(subset=["name"]).sort_values(
        by="market_value_in_eur", ascending=False
    ).head(TOP_N_PLAYERS)

    for idx, row in top_players.reset_index().iterrows():
        player_id = row["player_id"]
        player_name = row["name"]
        file_path = f"{OUTPUT_DIR}/players/player_{player_id}.txt"

        search_query = f"{player_name} football"
        content = get_wiki_content(search_query, lang=LANG, session=session)

        if content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"ID: {player_id}\n")
                f.write(f"Type: Joueur\n")
                f.write(f"Nom: {player_name}\n")
                f.write(f"Titre Wikipedia: {content['title']}\n")
                f.write(f"URL: {content['url']}\n")
                f.write(f"Longueur texte: {len(content['extract'])} caractères\n")
                f.write("\n=== CONTENU INTÉGRAL ===\n")
                f.write(content["extract"])
            stats["players_saved"] += 1
            print(f"[{idx+1}/{len(top_players)}] Joueur OK: {player_name} ({len(content['extract'])} car.)")
        else:
            print(f"[{idx+1}/{len(top_players)}] Non trouvé : {player_name}")

        time.sleep(0.12)

    print("\n" + "="*50)
    print(f"Téléchargement terminé avec succès !")
    print(f"Clubs enregistrés : {stats['clubs_saved']}")
    print(f"Joueurs enregistrés : {stats['players_saved']}")
    print("="*50)


if __name__ == "__main__":
    main()
