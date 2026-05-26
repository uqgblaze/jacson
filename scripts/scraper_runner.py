#### USE THIS CODE TO EXECUTE AND RUN JACSON:
# 1. CREATES LOG, THEN LOADS COURSES TO SCRAPE FROM LOCAL course-list.csv
# 2. SCRAPES PUBLIC DATA FROM COURSE-PROFILES.UQ.EDU.AU, SAVES LOCALLY UNDER ./PROFILES
# 3. BUILDS INDEX.JSON FROM SCRAPED PROFILES VIA INDEXSON
# 4. UPLOADS ALL COURSE PROFILES FROM THE LOCAL FILE TO THIS REPOSITORY
####
# scripts/scraper_runner.py
import os
import sys
import time
import logging
import argparse
import subprocess
from datetime import datetime

# All scripts now live in the same directory (./scripts)
import jacson

# Optional: Only import sheets_updater if Google Sheets integration is needed
try:
    import sheets_updater
    SHEETS_AVAILABLE = True
except ImportError:
    SHEETS_AVAILABLE = False

# Project root is one level up from ./scripts/
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")
COURSE_CSV_PATH = os.path.join(PROJECT_ROOT, "course-list.csv")
UPLOAD_SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "upload_profiles.py")
INDEXSON_SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "indexson.py")


def setup_logging(job_id: str = None):
    """
    Configure logging to stdout and (if possible) a log file.

    When job_id is provided (e.g. launched by JacDash), the log file is named
    scrape_{job_id}.log so that JacDash can tail it by job ID.
    Otherwise falls back to a date-stamped filename for standalone runs.
    """
    log_format = "%(asctime)s [%(levelname)s]: %(message)s"
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    stream = logging.StreamHandler()
    stream.setFormatter(logging.Formatter(log_format))
    root.addHandler(stream)
    try:
        os.makedirs(LOGS_DIR, exist_ok=True)
        if job_id:
            log_filename = f"scrape_{job_id}.log"
        else:
            log_filename = f"scrape_{datetime.now().strftime('%Y-%m-%d')}.log"
        log_file = os.path.join(LOGS_DIR, log_filename)
        file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
        file_handler.setFormatter(logging.Formatter(log_format))
        root.addHandler(file_handler)
        logging.info("Logging setup complete. Log file: %s", log_file)
    except (PermissionError, OSError) as e:
        logging.warning("Could not write to logs folder (%s); logging to console only.", e)


def verify_course_list_exists():
    if not os.path.exists(COURSE_CSV_PATH):
        logging.warning(f"course-list.csv not found at {COURSE_CSV_PATH}")
        logging.warning("The scraper will attempt to create a sample file if needed.")
    else:
        logging.info(f"Using local course-list.csv from {COURSE_CSV_PATH}")


def run_scraper():
    logging.info("Starting JacSON scraper...")
    scrape_results = jacson.main(
        csv_path=COURSE_CSV_PATH,
        base_directory=PROJECT_ROOT,
    )
    logging.info("JacSON scraper completed.")
    return scrape_results


def build_index():
    logging.info("Building index via indexSON.py...")
    try:
        subprocess.run(
            [sys.executable, INDEXSON_SCRIPT_PATH],
            check=True,
            cwd=PROJECT_ROOT,
        )
        logging.info("index.json built successfully.")
    except subprocess.CalledProcessError as e:
        logging.error(f"indexSON.py failed: {e}")


def upload_profiles():
    logging.info("Uploading profiles via upload_profiles.py...")
    try:
        subprocess.run(
            [sys.executable, UPLOAD_SCRIPT_PATH],
            check=True,
            cwd=PROJECT_ROOT,
        )
        logging.info("Profiles uploaded successfully.")
    except subprocess.CalledProcessError as e:
        logging.error(f"upload_profiles.py failed: {e}")


def update_status_on_sheets(scrape_results):
    if not SHEETS_AVAILABLE:
        logging.info("Skipping Google Sheets status update (sheets_updater not available).")
        return
    logging.info("Updating status on Google Sheets...")
    try:
        sheets_updater.update_status_sheet(scrape_results)
        logging.info("Google Sheets status update complete.")
    except Exception as e:
        logging.warning(f"Failed to update Google Sheets: {e}")
        logging.info("Continuing without Google Sheets update.")


def main():
    parser = argparse.ArgumentParser(description="JacSON scraper runner")
    parser.add_argument(
        "--job-id",
        default=None,
        help="Job ID supplied by JacDash (used to name the log file). "
             "Omit for standalone runs.",
    )
    args = parser.parse_args()

    setup_logging(job_id=args.job_id)
    os.chdir(PROJECT_ROOT)
    verify_course_list_exists()
    scrape_results = run_scraper()
    build_index()
    upload_profiles()
    update_status_on_sheets(scrape_results)
    logging.info("All tasks completed. Script finished.")


if __name__ == "__main__":
    main()
