# basil-replay-scraper

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
Repository: [https://github.com/Sprowk/basil-replay-scraper](https://github.com/Sprowk/basil-replay-scraper)

A Python tool for scraping the latest StarCraft bot games from the BASIL Ladder, collecting game data, and downloading .rep replay files. Uses Selenium to navigate the site, stores results in a CSV database, and includes features for managing replays and ensuring data integrity.

## Features

*   Scrapes game data from the BASIL Ladder "Last 24h" view.
*   Uses Selenium with headless Chrome for web interaction.
*   Extracts game details: participating bots, ranks, races (if available), map, timestamp, game length.
*   Fetches bot ratings from the BASIL ranking JSON endpoint to enrich game data.
*   Stores game data persistently in a CSV file (`basil_ladder_games.csv`).
*   Assigns unique, sequential `game_id` to each new game.
*   Performs duplication checks to avoid adding the same game multiple times.
*   Downloads `.rep` replay files automatically into a `replays/` folder, named by `game_id`.
*   Tracks replay download status (`downloaded` column) in the CSV.
*   Synchronizes replay download status by checking files present in the `replays/` folder.
*   Logs activity to both the console and a file (`daily_scrape.log`).
*   Designed for easy automation via shell scripts or dedicated runner scripts.
*   Includes an optional interactive mode (via `main.py`) for stats and manual operations.

## Requirements

*   Python (3.9 or higher recommended)
*   pip (Python package installer)
*   Google Chrome browser installed
*   ChromeDriver executable:
    *   Must be compatible with your installed Google Chrome version. See [ChromeDriver Downloads](https://chromedriver.chromium.org/downloads) or use a webdriver manager library.
    *   Needs to be accessible via your system's PATH environment variable OR have its path specified within the script (currently assumes PATH).
*   Required Python packages (see `requirements.txt`)

## Setup & Installation

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/Sprowk/basil-replay-scraper
    cd BasicScraper
    ```

2.  **Create a Virtual Environment:** (Highly Recommended) This isolates project dependencies.
    ```bash
    python3 -m venv venv # Or python -m venv venv
    ```

3.  **Activate the Virtual Environment:**
    *   **macOS/Linux:** `source venv/bin/activate`
    *   **Windows:** `venv\Scripts\activate`

4.  **Install Dependencies:** Create a file named `requirements.txt` in the `BasicScraper` directory with the following content:

    ```txt
    # requirements.txt
    selenium>=4.0
    pandas>=1.3
    requests>=2.25
    ```
    Then run:
    ```bash
    pip install -r requirements.txt
    ```

5.  **Install/Verify ChromeDriver:** Ensure you have a compatible ChromeDriver version installed and accessible in your system's PATH. Check compatibility with your Chrome version (`chrome://version`). You might need to update it:
    *   **Homebrew (macOS):** `brew update && brew upgrade chromedriver`
    *   **Manual:** Download the correct version and place the executable in a directory listed in your PATH (like `/usr/local/bin` or similar).

## How It Works (Automated Task Flow)

When the `run_automated_task()` function (typically called via `run.sh` or `run_daily.py`) is executed:

1.  **Load Data:** Reads existing game data from `basil_ladder_games.csv` into a pandas DataFrame.
2.  **Sync Status:** Checks the `replays/` folder. Updates the `downloaded` status in the DataFrame to `True` for any `game_id` where `<game_id>.rep` exists, and `False` otherwise. Saves the potentially updated CSV.
3.  **Fetch Ratings:** Downloads the latest bot ratings from the `ranking.json` URL.
4.  **Launch Browser:** Starts a headless Chrome instance using Selenium.
5.  **Navigate & Scrape:**
    *   Opens the BASIL Ladder main page.
    *   Waits for and clicks the "Last 24h" button.
    *   Waits for the game table (`gamesTable`) to load.
    *   Extracts data (Timestamp, Bot1, Bot2, Map, Length, Replay Link, Races) from each row in the table.
    *   Looks up bot ratings using the fetched data.
6.  **Close Browser:** Quits the Selenium browser instance.
7.  **Update Database:**
    *   Compares each newly scraped game to the existing games in the DataFrame based on: `timestamp`, `bot1_name`, `bot2_name`, `bot1_result`, `bot2_result`, `map_name`.
    *   Handles potential missing values (`NaN`) during comparison to avoid errors.
    *   Identifies unique new games.
    *   Assigns the next available `game_id` to each unique game.
    *   Appends the unique new games to the DataFrame.
8.  **Save Database:** Sorts the updated DataFrame by `game_id` and saves it back to `basil_ladder_games.csv`.
9.  **Download Replays:** (If `download=True`)
    *   Identifies rows in the DataFrame that have a `replay_link` but where `downloaded` is `False`.
    *   Attempts to download the `.rep` file for each, saving it as `<game_id>.rep` in the `replays/` folder.
    *   Updates the `downloaded` status to `True` in the DataFrame for successful downloads.
10. **Save Database Again:** Saves the CSV file again to reflect the latest download statuses.
11. **Logging:** Throughout the process, logs information, warnings, and errors to both the console and the `daily_scrape.log` file.

## Usage (Manual / Interactive)

If your `main.py` file has the `if __name__ == "__main__":` block calling the interactive `main()` function, you can run it directly for manual operations:

1.  Activate your virtual environment (`source venv/bin/activate`).
2.  Make sure you are in the `BasicScraper` directory.
3.  Run: `python main.py`
4.  Follow the on-screen menu prompts (e.g., show stats, run full update, download pending).

## Automation Setup

To run the scraper automatically (e.g., once a day), use a scheduler like `cron` (macOS/Linux) or Task Scheduler (Windows). The recommended way is to use the `run.sh` script.

**Using `run.sh` (Recommended for macOS/Linux):**

1.  **Configure `run.sh`:** Open the `run.sh` file provided in the project. Ensure the following variables are set correctly:
    *   `SCRAPER_DIR`: Should be `/Users/alexander/PycharmProjects/BasicScraper`.
    *   `PYTHON_SCRIPT_NAME`: Should be `main.py` (based on your error log).
    *   `VENV_ACTIVATE_SCRIPT`: Should point to your virtual environment's activate script, likely `"$SCRAPER_DIR/venv/bin/activate"`. Verify this path exists.
    *   `PYTHON_CMD`: Should be `python3` or the command for your venv Python.

2.  **Make `run.sh` Executable:**
    ```bash
    chmod +x /Users/alexander/PycharmProjects/BasicScraper/run.sh
    ```

3.  **Schedule with `cron`:**
    *   Open your crontab for editing: `crontab -e`
    *   Add a line to schedule the script. To run daily at 3:30 AM:
        ```cron
        # Example: Run daily at 3:30 AM
        # m h  dom mon dow   command
        30 3 * * * /Users/alexander/PycharmProjects/BasicScraper/run.sh >> /Users/alexander/PycharmProjects/BasicScraper/cron_run.log 2>&1
        ```
    *   **Explanation:**
        *   `30 3 * * *`: Specifies the schedule (minute 30, hour 3, every day, month, day of week).
        *   `/Users/alexander/PycharmProjects/BasicScraper/run.sh`: The **absolute path** to the script to execute.
        *   `>> .../cron_run.log`: Appends standard output from `run.sh` to a log file.
        *   `2>&1`: Redirects standard error to the same place as standard output. This helps capture errors from the shell script itself.

## Configuration

Some behaviour can be tweaked by constants at the top of `main.py`:

*   `TEST_MODE`: Set to `True` to limit the number of games scraped (useful for testing).
*   `MAX_GAMES_TO_SCRAPE`: The maximum number of games processed if `TEST_MODE` is `True`.
*   `CSV_FILENAME`, `REPLAY_FOLDER`, `LOG_FILE`: Names for data/output files.
*   URL constants (`BASIL_MAIN_URL`, `RANKING_JSON_URL`).

## File Structure
```
BasicScraper/
├── venv/                     # Python virtual environment (created by setup)
├── replays/                  # Downloaded <game_id>.rep files
│   └── ...                   # (Contains .rep files like 1.rep, 2.rep etc.)
├── main.py                   # Main scraping logic, functions, and interactive mode
├── run.sh                    # Recommended automation script (Linux/macOS)
├── basil_ladder_games.csv    # Game database (created on first run if missing)
├── daily_scrape.log          # Log file for script activity (created on first run)
├── requirements.txt          # Python package dependencies
└── README.md                 # This file
```

## License & Academic Use

This project is licensed under the [MIT License](https://opensource.org/licenses/MIT).