# basil-replay-scraper

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
Repository: [https://github.com/Sprowk/basil-replay-scraper](https://github.com/Sprowk/basil-replay-scraper)

A Python tool for scraping the latest StarCraft bot games from the BASIL Ladder, collecting game data, and optionally downloading .rep replay files. Uses Selenium to navigate the site, stores results in a CSV database, and includes features for managing replays and ensuring data integrity. **Automation is primarily handled via GitHub Actions.**

## Features

*   **Web Scraping:** Uses Selenium (headless Chrome) to fetch game data from the BASIL Ladder "Last 24h" view.
*   **Data Extraction:** Collects details like participating bots, ranks, results, map, game length, timestamp, bot races, and replay download links.
*   **Persistent Storage:** Saves scraped game data incrementally into a CSV file (`basil_ladder_games.csv`).
*   **Unique Game IDs:** Assigns a unique, sequential `game_id` to each newly recorded game.
*   **Duplicate Prevention:** Checks for existing games based on key fields (bots, results, map, timestamp, etc.) before adding new ones. Skips games with missing `game_length`.
*   **Replay Management (Optional):**
    *   Can download available `.rep` replay files into a designated folder (`replays/`).
    *   Names replays using their unique `game_id` (e.g., `123.rep`).
    *   Tracks download status (`downloaded` flag) in the CSV.
    *   Can synchronize the `downloaded` status based on files present in the `replays/` folder.
*   **Logging:** Records actions, warnings, and errors to both the console and a log file (`daily_scrape.log`).
*   **Automated Execution:** Designed to run automatically via GitHub Actions, committing updated data back to the repository.
*   **Interactive Mode:** `main()` function provides an optional command-line interface for viewing stats, triggering updates, and downloading replays manually.

## Requirements

*   Python (3.9 or higher recommended)
*   pip (Python package installer)
*   Git (for cloning and version control)
*   Required Python packages (see `requirements.txt`)
*   **(For Local Interactive Use Only):** Google Chrome browser and compatible ChromeDriver.

## Setup & Installation (for Local Use/Development)

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/Sprowk/basil-replay-scraper
    cd basil-replay-scraper # Make sure you navigate into the correct directory
    ```

2.  **Create a Virtual Environment:** (Highly Recommended)
    ```bash
    python3 -m venv venv # Or python -m venv venv
    ```

3.  **Activate the Virtual Environment:**
    *   **macOS/Linux:** `source venv/bin/activate`
    *   **Windows:** `venv\Scripts\activate`

4.  **Install Dependencies:** Ensure you have a `requirements.txt` file in the project root:
    ```txt
    # requirements.txt
    selenium>=4.0
    pandas>=1.3
    requests>=2.25
    # Add any other direct dependencies your script uses
    ```
    Then install the packages:
    ```bash
    pip install -r requirements.txt
    ```

5.  **(Local Use Only) Install/Verify ChromeDriver:** If running interactively, ensure you have a compatible ChromeDriver. For GitHub Actions automation, this is handled by the workflow.

## Interactive Mode (Local Only)
While the primary automation runs via GitHub Actions (without downloading replays), you can run the scraper locally for testing, manual updates, or specifically **to download the replay files**.

1.  Follow the Setup & Installation steps above.
2.  Activate your virtual environment (`source venv/bin/activate`).
3.  Make sure you are in the `basil-replay-scraper` directory.
4.  Run: `python main.py`
5.  Follow the on-screen menu prompts (e.g., show stats, run full update, download pending).

## Automation via GitHub Actions (Recommended)

This project is configured to run automatically using GitHub Actions. The workflow performs the scraping and commits the updated `basil_ladder_games.csv` and `daily_scrape.log` files back to the repository.

**How it Works:**

1.  **Workflow File:** The automation logic is defined in `.github/workflows/scrape_basil.yml`.
2.  **Triggers:** The workflow is triggered:
    *   **On a Schedule:** Uses `cron` syntax (e.g., twice daily). See the `schedule` section in the workflow file.
    *   **Manually:** Can be triggered from the "Actions" tab in your GitHub repository (`workflow_dispatch`).
3.  **Execution:** The workflow runs on a GitHub-hosted runner (Ubuntu):
    *   Checks out the repository code.
    *   Sets up the specified Python version.
    *   Installs dependencies from `requirements.txt`.
    *   Sets up Chrome and ChromeDriver (required by Selenium).
    *   Executes the scraper's automated task function (`main.run_automated_task(download=False)`).
    *   If changes are detected in the specified data/log files, it automatically commits and pushes them back to the repository using a bot identity.

**Setup:**

1.  **Ensure the Workflow File Exists:** Make sure the `.github/workflows/scrape_basil.yml` file is present in your repository with the correct configuration (see example below).
2.  **Commit and Push:** Commit the `.github/workflows/scrape_basil.yml` file to your repository's main branch.
3.  **Enable Actions (if needed):** Ensure GitHub Actions are enabled for your repository (usually they are by default).

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