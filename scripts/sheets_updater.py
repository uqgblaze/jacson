import os
import sys
import time
import logging
import subprocess
from datetime import datetime

# Import your scraper
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
    logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))
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


def get_github_token():
    token_path = os.path.join("secrets", "github_token.txt")
    try:
        with open(token_path, 'r') as f:
            return f.read().strip()
    except Exception as e:
        logging.error(f"Failed to read GitHub token from {token_path}: {e}")
        return None


def push_to_github():
    logging.info("Pushing JSON files to GitHub...")
    token = get_github_token()
    if not token:
        logging.error("GitHub token missing. Skipping push.")
        return

    github_user = "uqgblaze"
    repo = "jacson"
    remote_url = f"https://{github_user}:{token}@github.com/{github_user}/{repo}.git"

    try:
        subprocess.run(["git", "remote", "set-url", "origin", remote_url], check=True)
        subprocess.run(["git", "add", "*"], check=True)
        subprocess.run(["git", "commit", "-m", f"Auto scrape update {datetime.now().isoformat()}"], check=True)
        subprocess.run(["git", "push", "origin", "main"], check=True)
        logging.info("Push to GitHub successful.")
    except subprocess.CalledProcessError as e:
        logging.error(f"Git push failed: {e}")


def update_status_on_sheets(scrape_results):
    logging.info("Updating status on Google Sheets...")
    sheets_updater.update_status_sheet(scrape_results)
    logging.info("Google Sheets status update complete.")


def main():
    setup_logging()
    update_course_list_from_google_sheets()
    scrape_results = run_scraper()
    push_to_github()
    update_status_on_sheets(scrape_results)
    logging.info("All tasks completed. Script finished.")


if __name__ == "__main__":
    main()
