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
import logging
import sys


LOG_FILE = "daily_scrape.log"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

log_file = os.path.join(SCRIPT_DIR, LOG_FILE)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(stream=sys.stdout),  # Console output
        logging.FileHandler(log_file, mode='a', encoding='utf-8')  # Daily log file
    ],
    force=True
)

CSV_FILENAME = "basil_ladder_games.csv"
REPLAY_FOLDER = "replays"
BASIL_MAIN_URL = "https://basil.bytekeeper.org/"
LAST_24H_TEXT = "Last 24h"

RANKING_JSON_URL = "https://data.basil-ladder.net/stats/ranking.json"

TEST_MODE = False
MAX_GAMES_TO_SCRAPE = 10


# Create empty DataFrame with required columns
def create_empty_dataframe():
    columns = [
        "game_id", "bot1_name", "bot1_rank", "bot1_rating", "bot1_race", "bot1_result",
        "bot2_name", "bot2_rank", "bot2_rating", "bot2_race", "bot2_result",
        "map_name", "game_length", "timestamp", "date_scraped",
        "replay_link", "downloaded"
    ]
    return pd.DataFrame(columns=columns)


def load_existing_games():
    logging.info(f"Loading existing games data from {CSV_FILENAME}")

    if os.path.exists(CSV_FILENAME):
        df = pd.read_csv(CSV_FILENAME)
        logging.info(f"Loaded {len(df)} games from existing database.")
    else:
        logging.info(f"No existing data found at {CSV_FILENAME}")
        df = create_empty_dataframe()
        df.to_csv(CSV_FILENAME, index=False)
        logging.info(f"Created new CSV file: {CSV_FILENAME}")

    return df


def get_all_bot_ratings():
    logging.info(f"Fetching master rating list from {RANKING_JSON_URL}...")
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
                logging.warning(f"JSON entry missing 'botName' or 'rating': {bot_data}")

        logging.info(f"Successfully loaded ratings for {len(ratings_lookup)} bots from JSON.")
        return ratings_lookup

    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch ranking JSON: {e}")
        return {}
    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse ranking JSON: {e}")
        return {}
    except Exception as e:
        logging.error(f"Unexpected error processing ranking JSON: {e}")
        return {}


def extract_basil_ladder_games(bot_ratings_dict):
    logging.info("Fetching latest games from BASIL Ladder (Last 24h)...")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=chrome_options)
    games_data = []

    try:
        logging.info(f"Navigating to {BASIL_MAIN_URL}...")
        driver.get(BASIL_MAIN_URL)

        # Wait for page to load
        logging.info("Waiting for page to load...")
        wait = WebDriverWait(driver, 10)
        last_24h_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, f"//a[contains(text(), '{LAST_24H_TEXT}')]"))
        )
        logging.info("Clicking 'Last 24h' button...")
        last_24h_button.click()

        # Wait for the table to appear
        games_table = wait.until(EC.presence_of_element_located((By.ID, "gamesTable")))
        time.sleep(3)

        # Get rows
        game_rows = games_table.find_elements(By.TAG_NAME, "tr")
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Skip first row
        start_idx = 2
        total_games_in_table = max(0, len(game_rows) - start_idx)

        if total_games_in_table == 0:
             logging.warning("No game data rows found after skipping headers.")
        else:
            logging.info(f"Found {total_games_in_table} games in the table")

        processed_count = 0
        for row_idx, row in enumerate(game_rows[start_idx:], start=1):
            cells = row.find_elements(By.TAG_NAME, "td")
            # print(cells)

            if TEST_MODE and processed_count >= MAX_GAMES_TO_SCRAPE:
                logging.info(f"Test mode: Stopping after processing {processed_count} games.")
                break

            if len(cells) < 5:
                logging.warning(f"Skipping row {row_idx + start_idx - 1}: Expected >= 5 cells, found {len(cells)}")
                continue

            processed_count += 1

            # Log progress more meaningfully
            if processed_count % 20 == 0 or processed_count == total_games_in_table:
                percent = (processed_count / total_games_in_table) * 100
                print(f"Processing game {processed_count}/{total_games_in_table} ({percent:.1f}%)")

            try:
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
                    logging.error(f"Failed to retrieve bot races: {e}")
                    bot1_race = ""
                    bot2_race = ""

                bot1_rating = bot_ratings_dict.get(bot1_name, -1)
                bot2_rating = bot_ratings_dict.get(bot2_name, -1)

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
                logging.error(f"Error processing row {row_idx + start_idx - 1}: {e}", exc_info=True)

    except Exception as e:
        logging.exception(f"An error occurred during Selenium extraction: {e}")
    finally:
        driver.quit()
        logging.info("Browser closed.")

    logging.info(f"Extracted data for {len(games_data)} games from the page.")
    return games_data


def update_games_database(new_games, existing_df):
    if new_games:
         logging.info("Attempting to update game database with newly scraped games...")
    else:
        logging.info("No new games scraped to update database.")
        return existing_df

    new_df = pd.DataFrame(new_games)

    # Make sure existing DataFrame has the columns we expect
    if existing_df.empty:
        logging.info("Existing database is empty. Creating structure from scratch.")
        existing_df = create_empty_dataframe()
    else:
        # Convert game_id to int in case it's stored as string
        existing_df['game_id'] = pd.to_numeric(existing_df['game_id'], errors='coerce').fillna(0).astype(int)

    before_count = len(existing_df)
    unique_rows = []

    logging.info(f"Existing games in database: {before_count}")
    logging.info(f"New games scraped: {len(new_df)}")

    # Current max ID
    current_max_id = 0 if existing_df.empty else existing_df['game_id'].max()
    duplicate_count = 0

    # Check uniqueness by (timestamp, bot1_name, bot2_name, bot1_result, bot2_result, map_name)
    for _, row in new_df.iterrows():
        # see if any row in existing matches these 6 fields exactly
        duplicate = existing_df[
            (existing_df['game_length'].fillna('') == str(row['game_length'])) &
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
        else:
            duplicate_count += 1

    if duplicate_count == 0:
        logging.info("No duplicate games were found.")
    else:
        logging.info(f"Found and skipped {duplicate_count} duplicate game(s) already present in the database.")

    if unique_rows:
        logging.info(f"Found {len(unique_rows)} new unique games.")
        new_unique_df = pd.DataFrame(unique_rows, columns=existing_df.columns)
        existing_df = pd.concat([existing_df, new_unique_df], ignore_index=True)
    else:
        logging.info("No new unique games found.")

    after_count = len(existing_df)
    logging.info(f"Database size: {before_count} -> {after_count} (+{after_count - before_count})")

    # Sort by game_id ascending
    existing_df = existing_df.sort_values(by='game_id', ascending=True)
    existing_df.reset_index(drop=True, inplace=True)

    # Re-save in a known column order
    final_cols = create_empty_dataframe().columns.tolist()

    try:
        existing_df[final_cols].to_csv(CSV_FILENAME, index=False)
        logging.info(f"Database saved successfully to {CSV_FILENAME}")
    except Exception as e:
        logging.error(f"Failed to save updated database to {CSV_FILENAME}: {e}")

    return existing_df


def download_replays(games_df):
    if not os.path.exists(REPLAY_FOLDER):
        try:
            os.makedirs(REPLAY_FOLDER)
            logging.info(f"Created replay folder: {REPLAY_FOLDER}/")
        except OSError as e:
            logging.error(f"Could not create replay folder {REPLAY_FOLDER}: {e}")
            return games_df # Cannot proceed without folder

    to_download = games_df[(games_df['replay_link'].notna()) & (games_df['downloaded'] == False)]
    total_pending = len(to_download)
    if total_pending == 0:
        logging.info("No new replays to download.")
        return games_df

    logging.info(f"Found {total_pending} replay(s) pending download...")

    downloaded_count = 0
    failed_count = 0

    # Download each replay with progress
    for i, (idx, game) in enumerate(to_download.iterrows(), start=1):
        try:
            replay_url = game["replay_link"]
            game_id = game["game_id"]
            filename = f"{game_id}.rep"  # just <id>.rep
            filepath = os.path.join(REPLAY_FOLDER, filename)

            response = requests.get(replay_url, stream=True, timeout=30)
            if response.status_code == 200:
                bytes_downloaded = 0
                chunk_size = 8192

                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        f.write(chunk)
                        bytes_downloaded += len(chunk)

                games_df.at[idx, 'downloaded'] = True
                downloaded_count += 1
            else:
                logging.error(f"HTTP {response.status_code} for game ID {game_id}")
                failed_count += 1

        except Exception as e:
            logging.error(f"✗ Failed to download from {game['replay_link']}: {e}")
            failed_count += 1

        if i % 10 == 0 or i == total_pending:
            overall_percent = (i / total_pending) * 100
            print(f"Downloaded {i}/{total_pending} replays ({overall_percent:.1f}% complete)")

    logging.info(f"Replay Download Summary:")
    logging.info(f"  Successfully Downloaded: {downloaded_count}")
    logging.info(f"  Failed/Skipped:          {failed_count}")
    logging.info(f"  Total Processed:         {total_pending}")

    # Save updated CSV with download statuses
    try:
        required_cols = create_empty_dataframe().columns.tolist()
        games_df[required_cols].to_csv(CSV_FILENAME, index=False)
        logging.info(f"Updated download statuses saved to {CSV_FILENAME}")
    except Exception as e:
         logging.error(f"Failed to save updated CSV after downloads: {e}")

    return games_df


def show_statistics(games_df):
    print("\n=== Database Statistics ===")

    if games_df is None or games_df.empty:
        logging.info("No game data loaded to analyze.")
        return

    expected_cols = create_empty_dataframe().columns.tolist()

    for col in expected_cols:
        if col not in games_df.columns:
            logging.warning(f"Column '{col}' missing in DataFrame. Statistics will be skipped.")
            return

    total_games = len(games_df)
    print(f"Total Games Recorded: {total_games}")
    if total_games == 0:
        return

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
    else:
        logging.info("No map data available.")

    print("\n--- Most Frequent Bots (Top 5) ---")
    all_bots = pd.concat([games_df['bot1_name'], games_df['bot2_name']], ignore_index=True).dropna()
    bot_counts = all_bots.value_counts()
    if not bot_counts.empty:
        for i, (bot_name, count) in enumerate(bot_counts.head(5).items()):
            print(f"  {i+1}. {bot_name}: {count} games")
    else:
        logging.info("No bot data available.")

    print("\n--- Race Distribution ---")
    all_races = pd.concat([games_df['bot1_race'], games_df['bot2_race']], ignore_index=True)
    all_races = all_races.dropna().astype(str).str.lower()
    valid_races = all_races[~all_races.isin([''])]
    race_counts = valid_races.value_counts()
    if not race_counts.empty:
        for race_name, count in race_counts.items():
            print(f"  {race_name.capitalize()}: {count} games")
    else:
        logging.info("No valid race data available.")

    print("\n--- Race Matchup Counts ---")
    if 'bot1_race' in games_df.columns and 'bot2_race' in games_df.columns:
        matchup_counts = {}
        invalid_matchup_count = 0
        valid_races_set = {'terran', 'protoss', 'zerg'} #, 'terran_random','protoss_random','zerg_random'}

        for _, row in games_df.iterrows():
            r1 = str(row.get('bot1_race', '')).lower()
            r2 = str(row.get('bot2_race', '')).lower()

            if r1 in valid_races_set and r2 in valid_races_set:
                matchup_key = tuple(sorted((r1, r2)))
                matchup_counts[matchup_key] = matchup_counts.get(matchup_key, 0) + 1
            else:
                invalid_matchup_count += 1

        if matchup_counts:
            sorted_matchups = sorted(matchup_counts.items(), key=lambda item: (-item[1], item[0]))
            for (race1, race2), count in sorted_matchups:
                print(f"  {race1.capitalize()} vs {race2.capitalize()}: {count} games")
        else:
            logging.info("No valid race matchup data available.")

        if invalid_matchup_count > 0:
            print(f"  Games with Invalid/Unknown Race(s): {invalid_matchup_count}")

    else:
        logging.info("Skipping Race Matchup Counts (missing 'bot1_race' or 'bot2_race' column).")

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
            logging.info("No valid numeric rating data found for statistics.")

        # Display count of '-1' (not found) entries
        print(f"  (Entries without rating: {minus_one_count})")

    except Exception as e:
        logging.error(f"Failed processing ratings: {e}")

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
            logging.info("Could not determine timeframe (no valid timestamps found).")
    except Exception as e:
        logging.error(f"Failed processing timestamps: {e}")

    print("=" * 27)


def sync_replay_status(games_df, replay_folder_path=REPLAY_FOLDER):
    logging.info(f"Synchronizing 'downloaded' status with folder: {replay_folder_path}")

    # Column 'game_id' is required
    if 'game_id' not in games_df.columns:
        logging.error("Cannot sync replay status: 'game_id' column missing.")
        return games_df # Cannot proceed

    # Ensure 'downloaded' column exists
    if 'downloaded' not in games_df.columns:
        logging.warning("Initializing 'downloaded' column type to False.")
        games_df['downloaded'] = False

    # Scan the replay folder for .rep files
    found_replay_filenames = set()
    if os.path.exists(replay_folder_path):
        try:
            found_replay_filenames = {f for f in os.listdir(replay_folder_path) if f.lower().endswith(".rep")}
            logging.info(f"Found {len(found_replay_filenames)} potential .rep files in {replay_folder_path}.")
        except OSError as e:
            logging.error(f"Error scanning replay directory {replay_folder_path}: {e}")
    else:
        logging.warning(f"Replay directory not found: {replay_folder_path}")

    # Check if the replay file for a given game ID exists
    def check_exists(game_id):
        try:
            if pd.isna(game_id):
                return False
            return f"{int(game_id)}.rep" in found_replay_filenames
        except (ValueError, TypeError):
             return False # Treat invalid IDs as False

    # Calculate the new statuses based on folder scan
    logging.info("Calculating new 'downloaded' statuses based on folder scan...")
    new_downloaded_status = games_df['game_id'].apply(check_exists)

    # Store the state before modification for comparison later
    old_downloaded_status = games_df['downloaded'].copy()

    # Calculate the changes by comparing old and new
    statuses_changed_to_true = ((new_downloaded_status == True) & (old_downloaded_status == False)).sum()
    statuses_changed_to_false = ((new_downloaded_status == False) & (old_downloaded_status == True)).sum()

    #  Apply the new changes to the DataFrame
    games_df['downloaded'] = new_downloaded_status

    logging.info(f"Synchronization complete. 'downloaded' status updated.")
    logging.info(f"  Status changed to True: {statuses_changed_to_true}")
    logging.info(f"  Status changed to False: {statuses_changed_to_false}")
    logging.info(f"  Total marked as downloaded: {old_downloaded_status.sum()} -> {games_df['downloaded'].sum()}")

    # Save updated CSV with download statuses
    try:
        required_cols = create_empty_dataframe().columns.tolist()
        games_df[required_cols].to_csv(CSV_FILENAME, index=False)
        logging.info(f"Updated download statuses saved to {CSV_FILENAME}")
    except Exception as e:
         logging.error(f"Failed to save updated CSV after downloads: {e}")

    return games_df


def run_automated_task(download=False):
    start_time = time.time()
    logging.info("=" * 30)
    logging.info("Starting Automated Scrape Task")
    logging.info(f"Download replays: {'Enabled' if download else 'Disabled'}")
    logging.info("=" * 30)
    success = False  # Flag to track outcome

    try:
        logging.info("Step 1: Loading existing game data...")
        games_df = load_existing_games()

        if download:
            logging.info("Step 2: Syncing replay status with folder...")
            games_df = sync_replay_status(games_df, REPLAY_FOLDER)
        else:
            logging.info("Step 2: Skipping syncing replay status.")

        logging.info("Step 3: Fetching bot ratings...")
        bot_ratings = get_all_bot_ratings()

        logging.info("Step 4: Extracting new games from BASIL ladder...")
        new_games = extract_basil_ladder_games(bot_ratings)

        logging.info("Step 5: Updating games database with new games...")
        games_df = update_games_database(new_games, games_df)

        if download:
            logging.info("Step 6: Downloading new replays...")
            games_df = download_replays(games_df)
        else:
            logging.info("Step 6: Skipping replay download.")

        success = True

    except Exception as e:
        logging.exception("!!! An critical error occurred during the daily scrape job, halting execution !!!")

    finally:
        end_time = time.time()
        duration = end_time - start_time
        logging.info("="*30)
        logging.info(f"Automated Scrape Task Finished")
        logging.info(f"Outcome: {'SUCCESS' if success else 'FAILURE'}")
        logging.info(f"Total Duration: {duration:.2f} seconds")
        logging.info("="*30)


def main():
    print("=== BASIL Ladder Games Scraper and Replay Downloader ===")
    logging.info("Starting scraper.\n")

    games_df = load_existing_games()
    games_df = sync_replay_status(games_df, REPLAY_FOLDER)

    sys.stdout.flush()

    while True:
        print("\nWhat would you like to do?")
        print("1. Show current database statistics")
        print("2. Fetch NEW games from BASIL Ladder (and download new replays)")
        print("3. Download pending replays")
        print("4. Exit")

        choice = input("\nEnter your choice (1-4): ")

        if choice == '1':
            show_statistics(games_df)

        elif choice == '2':
            print("--- Starting Full Update Process ---")
            bot_ratings = get_all_bot_ratings()
            if not bot_ratings:
                 logging.warning("Could not fetch ratings JSON. Ratings in CSV will be '-1'.")
            new_games = extract_basil_ladder_games(bot_ratings)

            games_df = update_games_database(new_games, games_df)
            games_df = download_replays(games_df)
            print("--- Full Update Process Finished ---")

        elif choice == '3':
            print("--- Starting Replay Download ---")
            games_df = download_replays(games_df)
            print("--- Replay Download Finished ---")

        elif choice == '4':
            print("\nExiting program. Goodbye!")
            break

        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    main()
