# scrape_runner.py
# This version does not do git pull/push - just uploads the JSON files directly to the Github.
# Each run will override the JSON files that are in the folders!
import os
import time
import logging
import subprocess
from datetime import datetime

# Import your scraper module
import jacson
# Import Google Sheets utility
from scripts import sheets_updater


def setup_logging():
    logs_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(logs_dir, exist_ok=True)
    log_file = os.path.join(logs_dir, f"scrape_{datetime.now().strftime('%Y-%m-%d')}.log")
    logging.basicConfig(
        filename=log_file,
        filemode='a',
        format='%(asctime)s [%(levelname)s]: %(message)s',
        level=logging.INFO
    )
    logging.getLogger().addHandler(logging.StreamHandler())
    logging.info("Logging setup complete.")


def update_course_list_from_google_sheets():
    logging.info("Updating course-list.csv from Google Sheets...")
    sheets_updater.fetch_course_list("course-list.csv")
    logging.info("course-list.csv updated.")


def run_scraper():
    logging.info("Starting JacSON scraper...")
    scrape_results = jacson.main()
    logging.info("JacSON scraper completed.")
    return scrape_results


def upload_profiles():
    logging.info("Uploading profiles via upload_profiles.py...")
    script_path = os.path.join(os.getcwd(), "scripts", "upload_profiles.py")
    try:
        subprocess.run(["python", script_path], check=True)
        logging.info("Profiles uploaded successfully.")
    except subprocess.CalledProcessError as e:
        logging.error(f"upload_profiles.py failed: {e}")
        # If desired, you can adjust scrape_results here to reflect upload failures


def update_status_on_sheets(scrape_results):
    logging.info("Updating status on Google Sheets...")
    sheets_updater.update_status_sheet(scrape_results)
    logging.info("Google Sheets status update complete.")


def main():
    setup_logging()
    update_course_list_from_google_sheets()
    scrape_results = run_scraper()
    upload_profiles()
    update_status_on_sheets(scrape_results)
    logging.info("All tasks completed. Script finished.")


if __name__ == "__main__":
    main()
