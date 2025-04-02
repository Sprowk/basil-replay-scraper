#!/bin/bash

# --- Configuration ---
SCRAPER_DIR="/Users/alexander/PycharmProjects/BasicScraper"
PYTHON_SCRIPT_NAME="main.py"
PYTHON_CMD="python3"

# --- Path to your virtual environment's activate script ---
VENV_ACTIVATE_SCRIPT="$SCRAPER_DIR/.venv/bin/activate"

# --- Script Body ---
echo "------------------------------------"
echo "Starting BASIL Scraper Task via run.sh at $(date)"
echo "Script directory: $SCRAPER_DIR"
echo "Python script: $PYTHON_SCRIPT_NAME"
echo "Activating venv: $VENV_ACTIVATE_SCRIPT"
echo "------------------------------------"

# 1. Validate paths
if [ ! -d "$SCRAPER_DIR" ]; then
  echo "ERROR: Scraper directory not found: $SCRAPER_DIR" >&2; exit 1; fi
if [ ! -f "$SCRAPER_DIR/$PYTHON_SCRIPT_NAME" ]; then
  echo "ERROR: Python script not found: $SCRAPER_DIR/$PYTHON_SCRIPT_NAME" >&2; exit 1; fi
if [ ! -f "$VENV_ACTIVATE_SCRIPT" ]; then
  echo "ERROR: Virtual environment activate script not found: $VENV_ACTIVATE_SCRIPT" >&2

# 2. Activate the virtual environment
echo "Activating virtual environment..."
source "$VENV_ACTIVATE_SCRIPT" || { echo "ERROR: Failed to activate virtual environment" >&2; exit 1; }

# 3. Change directory to the script's location
echo "Changing directory to $SCRAPER_DIR..."
cd "$SCRAPER_DIR" || { echo "ERROR: Failed to change directory" >&2; exit 1; }

# 4. Execute the specific Python function using python -c
echo "Executing Python command (within venv)..."
PYTHON_MODULE_NAME="${PYTHON_SCRIPT_NAME%.py}"
PYTHON_CODE="import $PYTHON_MODULE_NAME; $PYTHON_MODULE_NAME.run_automated_task(download=True)"

$PYTHON_CMD -c "$PYTHON_CODE"
EXIT_CODE=$? # Capture exit code immediately

# 5. Deactivate the virtual environment
echo "Deactivating virtual environment..."
deactivate

# 6. Report status
echo "------------------------------------"
if [ $EXIT_CODE -ne 0 ]; then
  echo "ERROR: Python script execution failed with exit code $EXIT_CODE at $(date)" >&2
else
  echo "Python script execution completed successfully at $(date)"
fi
echo "run.sh finished."
echo "------------------------------------"

exit $EXIT_CODE