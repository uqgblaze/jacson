import csv
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Spreadsheet configuration
SPREADSHEET_ID = "1tJ04EY1AtyS-7iKlmgZhmom0f97xK3DsZ88wkqmRwNs"
RANGE_NAME = "Sheet1!A4:F"  # Starts from row 4
CSV_FILE = "course-list.csv"
STATUS_SCHEDULED = "Scheduled"

def get_sheet_service():
    credentials_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    creds = service_account.Credentials.from_service_account_info(
        eval(credentials_json),
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    return build("sheets", "v4", credentials=creds).spreadsheets()

def process_sheet_and_generate_csv(sheet_service):
    sheet = sheet_service.values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
    rows = sheet.get("values", [])

    included = []
    excluded = []
    updates = []

    for idx, row in enumerate(rows, start=4):  # Adjusted for actual row index in Google Sheets
        course_code = row[0].strip() if len(row) > 0 else ""
        jacson_request = row[1].strip().lower() == "true" if len(row) > 1 else False
        status = row[2].strip() if len(row) > 2 else ""
        manual = row[3].strip().lower() == "true" if len(row) > 3 else False

        if not course_code:
            continue

        if jacson_request and not manual:
            included.append(course_code)
            updates.append((idx, STATUS_SCHEDULED, ""))  # Set status to Scheduled, clear notes
        elif manual:
            excluded.append(course_code)

    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["included", "excluded"])
        for i in range(max(len(included), len(excluded))):
            writer.writerow([
                included[i] if i < len(included) else "",
                excluded[i] if i < len(excluded) else ""
            ])

    return updates

def update_statuses(sheet_service, updates):
    data = []
    for row_idx, status, note in updates:
        data.append({"range": f"Sheet1!C{row_idx}", "values": [[status]]})  # Status column
        data.append({"range": f"Sheet1!F{row_idx}", "values": [[note]]})    # Notes column
    body = {"valueInputOption": "RAW", "data": data}
    sheet_service.values().batchUpdate(spreadsheetId=SPREADSHEET_ID, body=body).execute()

if __name__ == "__main__":
    service = get_sheet_service()
    updates = process_sheet_and_generate_csv(service)
    update_statuses(service, updates)
