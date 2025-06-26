# sheets_updater.py
import os
import csv
import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Google Sheets settings
SPREADSHEET_ID = '1tJ04EY1AtyS-7iKlmgZhmom0f97xK3DsZ88wkqmRwNs'
RANGE_NAME = 'Sheet1!A2:F'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
CREDENTIALS_FILE = os.path.join('secrets', 'credentials.json')


def get_service():
    """
    Creates and returns a Google Sheets API service instance.
    """
    creds = service_account.Credentials.from_service_account_file(
        CREDENTIALS_FILE,
        scopes=SCOPES
    )
    service = build('sheets', 'v4', credentials=creds)
    return service


def fetch_course_list(csv_output='course-list.csv'):
    """
    Fetches course codes from Google Sheet and writes to a CSV file with
    'included' and 'excluded' columns based on Auto (B) and Manual (D) flags.
    """
    service = get_service()
    sheet = service.spreadsheets()
    result = sheet.values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=RANGE_NAME
    ).execute()
    values = result.get('values', [])

    included = []
    excluded = []

    for row in values:
        course_code = row[0].strip() if len(row) > 0 else ''
        auto_flag = row[1].strip().lower() if len(row) > 1 else ''
        manual_flag = row[3].strip().lower() if len(row) > 3 else ''

        if auto_flag == 'true':
            included.append(course_code)
        elif manual_flag == 'true':
            excluded.append(course_code)

    # Write to CSV
    with open(csv_output, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['included', 'excluded'])
        for i in range(max(len(included), len(excluded))):
            writer.writerow([
                included[i] if i < len(included) else '',
                excluded[i] if i < len(excluded) else ''
            ])

    logging.info(f"Fetched {len(included)} included and {len(excluded)} excluded courses from Sheets.")


def update_status_sheet(scrape_results):
    """
    Updates the Google Sheet Columns C (Status) and D (Notes) based on scrape results.
    scrape_results is a dict: {course_code: {'success': bool, 'note': str}}
    """
    service = get_service()
    sheet = service.spreadsheets()
    result = sheet.values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=RANGE_NAME
    ).execute()
    values = result.get('values', [])

    updates = []
    for row in values:
        course_code = row[0].strip() if len(row) > 0 else ''
        if course_code in scrape_results:
            status = 'Complete' if scrape_results[course_code]['success'] else 'Error'
            notes = scrape_results[course_code].get('note', '')
            updates.append([status, notes])
        else:
            updates.append(['', ''])

    update_range = f'Sheet1!C2:D{len(updates)+1}'
    body = {'values': updates}
    sheet.values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=update_range,
        valueInputOption='RAW',
        body=body
    ).execute()

    logging.info("Updated status and notes in Google Sheets.")
