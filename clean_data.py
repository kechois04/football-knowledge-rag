import os
import pandas as pd

# 1. Définition des paramètres
TARGET_LEAGUES = ['CL', 'GB1', 'ES1', 'IT1', 'L1', 'FR1']
TARGET_SEASONS = [2019, 2020, 2021, 2022, 2023]  # 5 saisons (ex: 2019/20 à 2023/24)

INPUT_DIR = "./sources"
OUTPUT_DIR = "./sources_filtered"
os.makedirs(OUTPUT_DIR, exist_ok=True)

print("--- 1. Filtrage de competitions.csv & games.csv ---")
# Compétitions
competitions = pd.read_csv(f"{INPUT_DIR}/competitions.csv")
competitions_filtered = competitions[competitions['competition_id'].isin(TARGET_LEAGUES)]
competitions_filtered.to_csv(f"{OUTPUT_DIR}/competitions.csv", index=False)

# Matchs (pivot central)
games = pd.read_csv(f"{INPUT_DIR}/games.csv")
games_filtered = games[
    (games['competition_id'].isin(TARGET_LEAGUES)) & 
    (games['season'].isin(TARGET_SEASONS))
]
games_filtered.to_csv(f"{OUTPUT_DIR}/games.csv", index=False)

valid_game_ids = set(games_filtered['game_id'].unique())
print(f"Matchs conservés : {len(valid_game_ids)}")

print("--- 2. Filtrage des appearances et club_games ---")
# Appearances (volumineux, filtré par game_id)
appearances = pd.read_csv(f"{INPUT_DIR}/appearances.csv")
appearances_filtered = appearances[appearances['game_id'].isin(valid_game_ids)]
appearances_filtered.to_csv(f"{OUTPUT_DIR}/appearances.csv", index=False)

valid_player_ids = set(appearances_filtered['player_id'].unique())
valid_club_ids = set(games_filtered['home_club_id']).union(set(games_filtered['away_club_id']))

# Club games
club_games = pd.read_csv(f"{INPUT_DIR}/club_games.csv")
club_games_filtered = club_games[club_games['game_id'].isin(valid_game_ids)]
club_games_filtered.to_csv(f"{OUTPUT_DIR}/club_games.csv", index=False)

print("--- 3. Filtrage des clubs et des joueurs ---")
# Clubs
clubs = pd.read_csv(f"{INPUT_DIR}/clubs.csv")
clubs_filtered = clubs[
    (clubs['domestic_competition_id'].isin(TARGET_LEAGUES)) | 
    (clubs['club_id'].isin(valid_club_ids))
]
clubs_filtered.to_csv(f"{OUTPUT_DIR}/clubs.csv", index=False)

# Joueurs
players = pd.read_csv(f"{INPUT_DIR}/players.csv")
players_filtered = players[players['player_id'].isin(valid_player_ids)]
players_filtered.to_csv(f"{OUTPUT_DIR}/players.csv", index=False)

print("--- 4. Filtrage des transferts et valorisations ---")
# Transferts
transfers = pd.read_csv(f"{INPUT_DIR}/transfers.csv")
transfers_filtered = transfers[transfers['player_id'].isin(valid_player_ids)]
transfers_filtered.to_csv(f"{OUTPUT_DIR}/transfers.csv", index=False)

# Valorisations
player_valuations = pd.read_csv(f"{INPUT_DIR}/player_valuations.csv")
player_valuations_filtered = player_valuations[player_valuations['player_id'].isin(valid_player_ids)]
player_valuations_filtered.to_csv(f"{OUTPUT_DIR}/player_valuations.csv", index=False)

print("Terminé ! Les fichiers filtrés sont dans le dossier ./sources_filtered/")