from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import pandas as pd
import os
import requests
from datetime import datetime
import json


CSV_FILENAME = "basil_ladder_games.csv"
REPLAY_FOLDER = "replays"
BASIL_MAIN_URL = "https://basil.bytekeeper.org/"
LAST_24H_TEXT = "Last 24h"

RANKING_JSON_URL = "https://data.basil-ladder.net/stats/ranking.json"

TEST_MODE = False
MAX_GAMES_TO_SCRAPE = 10


def load_existing_games():
    print(f"Loading existing games data from {CSV_FILENAME}")
    if os.path.exists(CSV_FILENAME):
        df = pd.read_csv(CSV_FILENAME)
        print(f"Loaded {len(df)} games from existing database.")
        print("Database columns:", ", ".join(df.columns))
    else:
        print(f"No existing data found at {CSV_FILENAME}")

        # Create empty DataFrame with required columns
        columns = [
            "game_id", "bot1_name", "bot1_rank", "bot1_rating", "bot1_race", "bot1_result",
            "bot2_name", "bot2_rank", "bot2_rating", "bot2_race", "bot2_result",
            "map_name", "game_length", "timestamp", "date_scraped",
            "replay_link", "downloaded"
        ]
        df = pd.DataFrame(columns=columns)

        df.to_csv(CSV_FILENAME, index=False)
        print(f"Created new CSV file: {CSV_FILENAME}")
    return df


def get_all_bot_ratings():
    print(f"Fetching master rating list from {RANKING_JSON_URL}...")
    ratings_lookup = {}
    try:
        response = requests.get(RANKING_JSON_URL, timeout=15)
        response.raise_for_status()

        all_bots_data = response.json()

        # Create the lookup dictionary
        for bot_data in all_bots_data:
            name = bot_data.get("botName")
            rating = bot_data.get("rating")
            if name is not None and rating is not None:
                ratings_lookup[name] = rating
            else:
                print(f"WARN: JSON entry missing 'botName' or 'rating': {bot_data}")

        print(f"Successfully loaded ratings for {len(ratings_lookup)} bots from JSON.")
        return ratings_lookup

    except requests.exceptions.RequestException as e:
        print(f"ERROR: Failed to fetch ranking JSON: {e}")
        return {}
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse ranking JSON: {e}")
        return {}
    except Exception as e:
        print(f"ERROR: Unexpected error processing ranking JSON: {e}")
        return {}


def extract_basil_ladder_games(bot_ratings_dict):
    print("\nFetching latest games from BASIL Ladder (Last 24h)...")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=chrome_options)
    games_data = []

    # Initialize the rating cache for this run
    rating_cache = {}

    try:
        print(f"Navigating to {BASIL_MAIN_URL}...")
        driver.get(BASIL_MAIN_URL)

        # Wait for page to load
        print("Waiting for page to load...")
        wait = WebDriverWait(driver, 10)
        last_24h_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, f"//a[contains(text(), '{LAST_24H_TEXT}')]"))
        )
        print("Clicking 'Last 24h' button...")
        last_24h_button.click()

        # Wait for the table to appear
        games_table = wait.until(EC.presence_of_element_located((By.ID, "gamesTable")))
        time.sleep(3)

        # Get rows
        game_rows = games_table.find_elements(By.TAG_NAME, "tr")
        print(f"Found {len(game_rows)} game rows in the table")

        current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Skip first row
        start_idx = 2

        for row_idx, row in enumerate(game_rows[start_idx:], start=1):
            cells = row.find_elements(By.TAG_NAME, "td")
            # print(cells)

            if TEST_MODE and row_idx > MAX_GAMES_TO_SCRAPE:
                break

            if len(cells) < 3:
                continue

            #if row_idx % 10 == 0:
            #    print(f"Processed {row_idx}/{len(game_rows)} games")

            if row_idx % 10 == 0 or row_idx == len(game_rows):
                percent = (row_idx / len(game_rows)) * 100
                print(f"Processed {row_idx}/{len(game_rows)} games ({percent:.1f}%)")

            bot1 = cells[0].text.split(maxsplit=1)
            bot1_rank = bot1[0].strip()
            bot1_name = bot1[1].strip()

            bot2 = cells[1].text.split(maxsplit=1)
            bot2_rank = bot2[0].strip()
            bot2_name = bot2[1].strip()

            bot1_result = "Win"
            bot2_result = "Loss"

            map_name = cells[2].text.strip()
            timestamp = cells[3].text.strip()
            game_length = cells[4].text.strip()

            # Grab the replay link from any <a> with .rep in the href
            replay_link = None
            all_links = row.find_elements(By.TAG_NAME, "a")
            for link in all_links:
                href = link.get_attribute("href")
                if href and ".rep" in href:
                    replay_link = href
                    break

            try:
                bot1_race = cells[0].get_attribute('class').split()[1][5:] or ""
                bot2_race = cells[1].get_attribute('class').split()[1][5:] or ""
            except Exception as e:
                bot1_race = ""
                bot2_race = ""

            bot1_rating = bot_ratings_dict.get(bot1_name, -1)
            bot2_rating = bot_ratings_dict.get(bot2_name, -1)

            #bot1_rating = 0 #fetch_bot_rating(bot1_name, rating_cache)
            #bot2_rating = 0 #fetch_bot_rating(bot2_name, rating_cache)

            # Store it all in a dictionary
            games_data.append({
                # game_id is assigned later in update_games_database
                "bot1_name": bot1_name, "bot1_rank": bot1_rank,
                "bot1_rating": bot1_rating, "bot1_race": bot1_race,
                "bot1_result": bot1_result,

                "bot2_name": bot2_name, "bot2_rank": bot2_rank,
                "bot2_rating": bot2_rating, "bot2_race": bot2_race,
                "bot2_result": bot2_result,

                "map_name": map_name, "game_length": game_length,
                "timestamp": timestamp, "date_scraped": current_date,
                "replay_link": replay_link, "downloaded": False
            })

    except Exception as e:
        print(f"An error occurred during extraction: {e}")
    finally:
        driver.quit()

    print(f"Extracted {len(games_data)} total games.")

    return games_data


def update_games_database(new_games, existing_df):
    if not new_games:
        print("No new games scraped.")
        return existing_df

    new_df = pd.DataFrame(new_games)

    # Make sure existing DataFrame has the columns we expect
    if existing_df.empty:
        columns = [
            "game_id", "bot1_name", "bot1_rank", "bot1_rating", "bot1_race", "bot1_result",
            "bot2_name", "bot2_rank", "bot2_rating", "bot2_race", "bot2_result",
            "map_name", "game_length", "timestamp", "date_scraped",
            "replay_link", "downloaded"
        ]
        existing_df = pd.DataFrame(columns=columns)
    else:
        # Convert game_id to int in case it's stored as string
        existing_df['game_id'] = pd.to_numeric(existing_df['game_id'], errors='coerce').fillna(0).astype(int)

    before_count = len(existing_df)
    unique_rows = []

    print("\n=== Checking for new unique games ===")
    print(f"Existing games in database: {before_count}")
    print(f"New games scraped: {len(new_df)}")

    # Current max ID
    current_max_id = 0 if existing_df.empty else existing_df['game_id'].max()

    # Check uniqueness by (timestamp, bot1_name, bot2_name, bot1_result, bot2_result, map_name)
    for _, row in new_df.iterrows():
        # see if any row in existing matches these 6 fields exactly
        duplicate = existing_df[
            (existing_df['timestamp'] == row['timestamp']) &
            (existing_df['bot1_name'] == row['bot1_name']) &
            (existing_df['bot2_name'] == row['bot2_name']) &
            (existing_df['bot1_result'] == row['bot1_result']) &
            (existing_df['bot2_result'] == row['bot2_result']) &
            (existing_df['map_name'] == row['map_name'])
        ]
        if duplicate.empty:
            current_max_id += 1
            row['game_id'] = current_max_id
            unique_rows.append(row)

    if unique_rows:
        print(f"Found {len(unique_rows)} new unique games.")
        new_unique_df = pd.DataFrame(unique_rows, columns=existing_df.columns)
        existing_df = pd.concat([existing_df, new_unique_df], ignore_index=True)
    else:
        print("No new unique games found.")

    after_count = len(existing_df)
    print(f"Database size: {before_count} → {after_count} (+{after_count - before_count})")

    # Sort by game_id ascending
    existing_df = existing_df.sort_values(by='game_id', ascending=True)
    existing_df.reset_index(drop=True, inplace=True)

    # Re-save in a known column order
    final_cols = [
        "game_id", "bot1_name", "bot1_rank", "bot1_rating", "bot1_race", "bot1_result",
        "bot2_name", "bot2_rank", "bot2_rating", "bot2_race", "bot2_result",
        "map_name", "game_length", "timestamp", "date_scraped",
        "replay_link", "downloaded"
    ]

    existing_df = existing_df[final_cols]
    existing_df.to_csv(CSV_FILENAME, index=False)

    return existing_df


def download_replays(games_df):
    if not os.path.exists(REPLAY_FOLDER):
        os.makedirs(REPLAY_FOLDER)
        print(f"Created replay folder: {REPLAY_FOLDER}/")

    to_download = games_df[(games_df['replay_link'].notna()) & (games_df['downloaded'] == False)]
    total_pending = len(to_download)
    if total_pending == 0:
        print("\nNo new replays to download.")
        return games_df

    print(f"\n=== Replay Download ===")
    print(f"Found {total_pending} replay(s) pending download...")

    # Download each replay with progress
    for i, (idx, game) in enumerate(to_download.iterrows(), start=1):
        try:
            replay_url = game["replay_link"]
            game_id = game["game_id"]
            filename = f"{game_id}.rep"  # just <id>.rep
            filepath = os.path.join(REPLAY_FOLDER, filename)

            response = requests.get(replay_url, stream=True)
            if response.status_code == 200:
                file_size = int(response.headers.get('content-length', 0))
                bytes_downloaded = 0
                chunk_size = 8192

                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        f.write(chunk)
                        bytes_downloaded += len(chunk)
                        if file_size > 0:
                            file_percent = (bytes_downloaded / file_size) * 100
                            print(f"  - {file_percent:5.1f}% of current file", end='\r')

                games_df.at[idx, 'downloaded'] = True
            else:
                print(f"  ✗ Failed: HTTP {response.status_code}")

        except Exception as e:
            print(f"  ✗ Error downloading {game['replay_link']}: {e}")

        if i % 10 == 0 or i == total_pending:
            overall_percent = (i / total_pending) * 100
            print(f"Downloaded {i}/{total_pending} replays ({overall_percent:.1f}% complete)")

    # Save updated CSV
    games_df.to_csv(CSV_FILENAME, index=False)
    print("\nAll pending replays processed (downloaded or failed).")
    return games_df


def show_statistics(games_df):
    print("\n=== Database Statistics ===")

    if games_df is None or games_df.empty:
        print("No game data loaded to analyze.")
        return

    # Ensure expected columns exist... (same as before)
    expected_cols = [
        "game_id", "bot1_name", "bot1_rank", "bot1_rating", "bot1_race", "bot1_result",
        "bot2_name", "bot2_rank", "bot2_rating", "bot2_race", "bot2_result",
        "map_name", "game_length", "timestamp", "date_scraped",
        "replay_link", "downloaded"
    ]
    for col in expected_cols:
        if col not in games_df.columns:
            print(f"WARN: Column '{col}' missing in DataFrame. Statistics for it will be skipped.")
            games_df[col] = pd.NA

    total_games = len(games_df)
    print(f"Total Games Recorded: {total_games}")
    if total_games == 0: return

    print("\n--- Replay Status ---")
    downloaded_count = games_df['downloaded'].sum()
    pending_download = games_df[games_df['replay_link'].notna() & (games_df['downloaded'] == False)]
    pending_count = len(pending_download)
    missing_link_count = games_df['replay_link'].isna().sum()

    print(f"  Replays Downloaded: {downloaded_count}")
    print(f"  Replays Pending Download: {pending_count}")
    if missing_link_count > 0:
        print(f"  Games Missing Replay Link: {missing_link_count}")

    print("\n--- Map Popularity (Top 5) ---")
    map_counts = games_df['map_name'].dropna().value_counts()
    if not map_counts.empty:
        for i, (map_name, count) in enumerate(map_counts.head(5).items()):
             print(f"  {i+1}. {map_name}: {count} games")
    else: print("  No map data available.")

    print("\n--- Most Frequent Bots (Top 5) ---")
    all_bots = pd.concat([games_df['bot1_name'], games_df['bot2_name']], ignore_index=True).dropna()
    bot_counts = all_bots.value_counts()
    if not bot_counts.empty:
        for i, (bot_name, count) in enumerate(bot_counts.head(5).items()):
            print(f"  {i+1}. {bot_name}: {count} games")
    else: print("  No bot data available.")

    print("\n--- Race Distribution ---")
    all_races = pd.concat([games_df['bot1_race'], games_df['bot2_race']], ignore_index=True)
    all_races = all_races.dropna().astype(str).str.lower()
    valid_races = all_races[~all_races.isin(['unknown', 'n/a', ''])]
    race_counts = valid_races.value_counts()
    if not race_counts.empty:
        for race_name, count in race_counts.items():
            print(f"  {race_name.capitalize()}: {count} games")
    else:
        print("  No valid race data available.")

    print("\n--- Bot Ratings  ---")
    try:
        bot1_ratings_num = pd.to_numeric(games_df['bot1_rating'], errors='coerce')
        bot2_ratings_num = pd.to_numeric(games_df['bot2_rating'], errors='coerce')
        all_numeric_ratings = pd.concat([bot1_ratings_num, bot2_ratings_num], ignore_index=True)

        # Count '-1' entries (before dropping NaNs)
        minus_one_count = (all_numeric_ratings == -1).sum()

        # Isolate valid ratings for stats (drop NaN and -1)
        valid_ratings = all_numeric_ratings.dropna()
        valid_ratings = valid_ratings[valid_ratings != -1]
        valid_ratings_count = len(valid_ratings)

        if valid_ratings_count > 0:
            print(f"  Average Rating: {valid_ratings.mean():.0f}")
            print(f"  Min Rating:     {valid_ratings.min():.0f}")
            print(f"  Max Rating:     {valid_ratings.max():.0f}")
        else:
            print("  No valid numeric rating data found for statistics.")

        # Display count of '-1' (not found) entries
        print(f"  (Entries without rating: {minus_one_count})")

    except Exception as e:
        print(f"  Error processing ratings: {e}")


    print("\n--- Game Timeframe ---")
    try:
        timestamps = pd.to_datetime(games_df['timestamp'], format='%Y.%m.%d %I:%M %p', errors='coerce')
        valid_timestamps = timestamps.dropna()
        if not valid_timestamps.empty:
            first_game_time = valid_timestamps.min()
            last_game_time = valid_timestamps.max()
            print(f"  Earliest Game Timestamp: {first_game_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  Latest Game Timestamp:   {last_game_time.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print("  Could not determine timeframe (no valid timestamps found).")
    except Exception as e:
        print(f"  Error processing timestamps: {e}")

    print("=" * 27)


def main():
    print("=== BASIL Ladder Games Scraper and Replay Downloader ===")

    while True:
        print("\nWhat would you like to do?")
        print("1. Load database and show statistics")
        print("2. Fetch NEW games from BASIL Ladder (and download new replays)")
        print("3. Download pending replays")
        print("4. Exit")

        choice = input("\nEnter your choice (1-4): ")

        if choice == '1':
            games_df = load_existing_games()
            show_statistics(games_df)

        elif choice == '2':
            bot_ratings = get_all_bot_ratings()
            if not bot_ratings:
                 print("WARN: Could not fetch ratings JSON. Ratings in CSV will be 'N/A'.")
            new_games = extract_basil_ladder_games(bot_ratings)

            games_df = load_existing_games()
            games_df = update_games_database(new_games, games_df)
            games_df = download_replays(games_df)

        elif choice == '3':
            games_df = load_existing_games()
            games_df = download_replays(games_df)

        elif choice == '4':
            print("\nExiting program. Goodbye!")
            break

        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    main()
