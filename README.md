# basil-replay-scraper

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
Repository: [https://github.com/Sprowk/basil-replay-scraper](https://github.com/Sprowk/basil-replay-scraper)

A Python tool for scraping the latest StarCraft bot games from the BASIL Ladder, collecting game data, and downloading .rep replay files. Uses Selenium to navigate the site, stores results in a CSV database, and includes features for managing replays and ensuring data integrity.

## Features

*   **Web Scraping:** Uses Selenium (headless Chrome) to fetch game data from the BASIL Ladder "Last 24h" view.
*   **Data Extraction:** Collects details like participating bots, ranks, results, map, game length, timestamp, and replay download links.
*   **Persistent Storage:** Saves scraped game data incrementally into a CSV file (`basil_ladder_games.csv`).
*   **Unique Game IDs:** Assigns a unique, sequential `game_id` to each newly recorded game.
*   **Duplicate Prevention:** Checks for existing games based on key fields (`timestamp`, bots, results, map) before adding new ones.
*   **Replay Management:**
    *   Downloads available `.rep` replay files into a designated folder (`replays/`).
    *   Names replays using their unique `game_id` (e.g., `123.rep`).
    *   Tracks download status (`downloaded` flag) in the CSV.
    *   Can synchronize the `downloaded` status based on files present in the `replays/` folder.
*   **Logging:** Records actions, warnings, and errors to both the console and a log file (`daily_scrape.log`).
*   **Modes of Operation:**
    *   **Automated Task:** `run_automated_task()` function designed for scheduled execution (e.g., via cron).
    *   **Interactive Menu:** `main()` function provides a command-line interface for viewing stats, triggering updates, and downloading replays manually.

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

4.  **Install Dependencies:** Ensure you have a `requirements.txt` file in the project root with the following content:
    ```txt
    # requirements.txt
    selenium>=4.0
    pandas>=1.3
    requests>=2.25
    ```
    Then install the packages:
    ```bash
    pip install -r requirements.txt
    ```

5.  **Install/Verify ChromeDriver:** Ensure you have a compatible ChromeDriver version installed and accessible in your system's PATH. Check compatibility with your Chrome version (`chrome://version`). You might need to update it:
    *   **Homebrew (macOS):** `brew update && brew upgrade chromedriver`
    *   **Manual:** Download the correct version and place the executable in a directory listed in your PATH (like `/usr/local/bin` or similar).

## Interactive Mode

1.  Activate your virtual environment (`source venv/bin/activate`).
2.  Make sure you are in the `BasicScraper` directory.
3.  Run: `python main.py`
4.  Follow the on-screen menu prompts (e.g., show stats, run full update, download pending).

## Automation Setup

To run the scraper automatically (e.g., once a day), use a scheduler like `cron` (macOS/Linux) or Task Scheduler (Windows). The recommended way is to use the `run.sh` script.

**Using `run.sh` (Recommended for macOS/Linux):**

1.  **Configure `run.sh`:** Open the `run.sh` file provided in the project. Ensure the following variables are set correctly:
    *   `SCRAPER_DIR`: Set this to the **absolute path** of your project directory (e.g., `/home/user/projects/basil-replay-scraper`).
    *   `PYTHON_SCRIPT_NAME`: The name of your main Python script (default: `main.py`). Change only if you renamed it.
    *   `PYTHON_CMD`: The command used to invoke Python when your virtual environment is active (e.g., `python3`, `python`).
    *   `VENV_ACTIVATE_SCRIPT`: The **absolute path** to the `activate` script within your virtual environment. Double-check if your virtual environment folder is named `.venv` (default in the script) or `venv`.
*   Save the changes made to `run.sh`.

2.  **Make `run.sh` Executable:**
    ```bash
    chmod +x /path/to/your/project/run.sh
    ```
    *(Replace `/path/to/your/project/run.sh` with the actual absolute path to the script).*

3.  **Schedule with `cron`:**
    *   Open your crontab for editing: `crontab -e`
    *   Add a line to schedule the script. To run daily at 3:30 AM:
        ```cron
        # Example: Run daily at 3:30 AM
        # m h  dom mon dow   command
        30 3 * * * /path/to/your/project/run.sh >> /path/to/your/project/cron_job.log 2>&1
        ```
    *   **Explanation:**
        *   `30 3 * * *`: Specifies the schedule (minute 30, hour 3, every day, month, day of week).
        *   `/path/to/your/project/run.sh`: The **absolute path** to the script to execute.
        *   `>> .../cron_run.log`: Appends standard output from `run.sh` to a log file.
        *   `2>&1`: Redirects standard error to the same place as standard output. This helps capture errors from the shell script itself.

## Configuration

Some behaviour can be tweaked by constants at the top of `main.py`:

*   `LOG_FILE`: Name of the log file (default: `daily_scrape.log`).
*   `CSV_FILENAME`: Name of the CSV database file (default: `basil_ladder_games.csv`).
*   `REPLAY_FOLDER`: Name of the directory to store downloaded replays (default: `replays`).
*   `BASIL_MAIN_URL`: Base URL for the BASIL Ladder website.
*   `LAST_24H_TEXT`: Text identifier for the "Last 24h" link on the BASIL site.
*   `RANKING_JSON_URL`: URL for the bot ranking JSON data.
*   `TEST_MODE`: Set to `True` to limit the number of games scraped (useful for debugging).
*   `MAX_GAMES_TO_SCRAPE`: Maximum number of games processed if `TEST_MODE` is `True`.

## File Structure
```
basil-replay-scraper/
├── venv/                   # Python virtual environment (created by setup)
├── replays/                # Holds downloaded .rep files (named <game_id>.rep)
│   └── ...                   # (Contains .rep files like 1.rep, 2.rep etc.)
├── main.py                 # Core scraping logic & optional interactive menu
├── run.sh                  # Shell script for automated runs (macOS/Linux)
├── basil_ladder_games.csv  # CSV database (created automatically if missing)
├── daily_scrape.log        # Log file (created automatically on first run)
├── requirements.txt        # Python dependencies
└── README.md               # Documentation (this file)
```

## License & Academic Use

This project is licensed under the [MIT License](https://opensource.org/licenses/MIT).