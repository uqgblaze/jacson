import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Spreadsheet configuration
SPREADSHEET_ID = "1tJ04EY1AtyS-7iKlmgZhmom0f97xK3DsZ88wkqmRwNs"
RANGE_NAME = "Sheet1!A4:F"
STATUS_SUCCESS = "Success!"
STATUS_FAILURE = "Failure"

def get_sheet_service():
    credentials_json = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
    creds = service_account.Credentials.from_service_account_info(
        eval(credentials_json),
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    return build("sheets", "v4", credentials=creds).spreadsheets()

def update_results(sheet_service):
    sheet = sheet_service.values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
    rows = sheet.get("values", [])
    updates = []

    for idx, row in enumerate(rows, start=4):  # Start from row 4 in Google Sheets
        course_code = row[0].strip() if len(row) > 0 else ""
        status = row[2].strip() if len(row) > 2 else ""

        # Only process rows marked as "Scheduled"
        if not course_code or status != "Scheduled":
            continue

        try:
            # Check if the output JSON file exists anywhere in the project
            found = False
            for root, dirs, files in os.walk("."):
                if f"{course_code}.json" in files:
                    found = True
                    break

            if found:
                updates.append({
                    "row": idx,
                    "status": STATUS_SUCCESS,
                    "jacson_request": "FALSE",
                    "notes": ""
                })
            else:
                updates.append({
                    "row": idx,
                    "status": STATUS_FAILURE,
                    "jacson_request": "FALSE",
                    "notes": f"Could not find {course_code}.json in output"
                })

        except Exception as e:
            updates.append({
                "row": idx,
                "status": STATUS_FAILURE,
                "jacson_request": "FALSE",
                "notes": str(e)
            })

    # Prepare and send batch update
    data = []
    for u in updates:
        row = u["row"]
        data.append({"range": f"Sheet1!B{row}", "values": [[u["jacson_request"]]]})  # Clear JacSON Request
        data.append({"range": f"Sheet1!C{row}", "values": [[u["status"]]]})          # Update Status
        data.append({"range": f"Sheet1!F{row}", "values": [[u["notes"]]]})           # Update Notes

    body = {"valueInputOption": "RAW", "data": data}
    sheet_service.values().batchUpdate(spreadsheetId=SPREADSHEET_ID, body=body).execute()

if __name__ == "__main__":
    service = get_sheet_service()
    update_results(service)
