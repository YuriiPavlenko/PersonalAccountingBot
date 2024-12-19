from google.oauth2 import service_account
from googleapiclient.discovery import build

class SheetsClient:
    def __init__(self, spreadsheet_id):
        self.spreadsheet_id = spreadsheet_id
        credentials = service_account.Credentials.from_service_account_file(
            'credentials.json',
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        self.service = build('sheets', 'v4', credentials=credentials)
    
    def append_expense(self, date, category, amount, description):
        values = [[date, category, amount, description]]
        body = {'values': values}
        self.service.spreadsheets().values().append(
            spreadsheetId=self.spreadsheet_id,
            range='Expenses!A:D',
            valueInputOption='USER_ENTERED',
            body=body
        ).execute()
