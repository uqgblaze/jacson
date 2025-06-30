# scraper_runner-GithubAuto.py
import os
import time
import logging
import subprocess
import base64
import json
import csv
import requests
from datetime import datetime

import jacson

from google.oauth2 import service_account
from googleapiclient.discovery import build


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


def get_google_service():
    creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    creds = service_account.Credentials.from_service_account_info(
        json.loads(creds_json),
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    return build("sheets", "v4", credentials=creds)


def fetch_course_list(service):
    sheet = service.spreadsheets()
    result = sheet.values().get(
        spreadsheetId='1tJ04EY1AtyS-7iKlmgZhmom0f97xK3DsZ88wkqmRwNs',
        range='Sheet1!A4:F'
    ).execute()

    values = result.get("values", [])
    included, excluded = [], []

    for row in values:
        code = row[0].strip() if len(row) > 0 else ''
        auto_flag = row[1].strip().lower() if len(row) > 1 else ''
        manual_flag = row[3].strip().lower() if len(row) > 3 else ''
        if auto_flag == 'true':
            included.append(code)
        elif manual_flag == 'true':
            excluded.append(code)

    with open("course-list.csv", "w", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["included", "excluded"])
        for i in range(max(len(included), len(excluded))):
            writer.writerow([
                included[i] if i < len(included) else '',
                excluded[i] if i < len(excluded) else ''
            ])

    logging.info(f"Fetched {len(included)} included and {len(excluded)} excluded courses.")


def upload_profiles():
    from pathlib import Path
    token = os.environ.get("MY_GITHUB_TOKEN")
    if not token:
        logging.warning("No GitHub token provided!")
        return

    base_path = Path("profiles")
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    for local_file in base_path.rglob("*.json"):
        rel_path = local_file.relative_to(base_path).as_posix()
        repo_path = f"profiles/{rel_path}"

        with open(local_file, "rb") as f:
            content = base64.b64encode(f.read()).decode()

        get_url = f"https://api.github.com/repos/uqgblaze/jacson/contents/{repo_path}"
        r = requests.get(get_url, headers=headers)

        if r.status_code == 200:
            sha = r.json()["sha"]
            action = "Updating"
        else:
            sha = None
            action = "Creating"

        payload = {
            "message": f"{action} {repo_path}",
            "content": content
        }
        if sha:
            payload["sha"] = sha

        put_url = get_url
        response = requests.put(put_url, headers=headers, data=json.dumps(payload))
        if response.status_code in (200, 201):
            logging.info(f"✅ {action} succeeded: {repo_path}")
        else:
            logging.error(f"❌ {action} failed: {repo_path} — {response.text}")


def update_status(service, scrape_results):
    sheet = service.spreadsheets()
    result = sheet.values().get(
        spreadsheetId='1tJ04EY1AtyS-7iKlmgZhmom0f97xK3DsZ88wkqmRwNs',
        range='Sheet1!A4:F'
    ).execute()

    values = result.get("values", [])
    tz = datetime.now().astimezone().tzinfo
    now = datetime.now(tz)
    stamp = now.strftime('%d %B, %Y at %H:%M') + ' AEST'

    updates = []
    for idx, row in enumerate(values, start=4):
        code = row[0].strip() if row else ''
        if code in scrape_results:
            ok = scrape_results[code]['success']
            updates.extend([
                {"range": f"Sheet1!B{idx}", "values": [[False]]},
                {"range": f"Sheet1!C{idx}", "values": [["Success!" if ok else "Error"]]},
                {"range": f"Sheet1!F{idx}", "values": [[f"Successfully ran on {stamp}" if ok else scrape_results[code].get("note", "")]]}
            ])

    body = {"valueInputOption": "RAW", "data": updates}
    sheet.values().batchUpdate(spreadsheetId='1tJ04EY1AtyS-7iKlmgZhmom0f97xK3DsZ88wkqmRwNs', body=body).execute()
    logging.info("Google Sheet updated with scrape results.")


def main():
    setup_logging()
    service = get_google_service()

    fetch_course_list(service)
    scrape_results = jacson.main()
    upload_profiles()
    update_status(service, scrape_results)


if __name__ == "__main__":
    main()
