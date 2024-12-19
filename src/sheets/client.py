import json
import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build
from src.config import GOOGLE_CREDENTIALS

class SheetsClient:
    def __init__(self, spreadsheet_id):
        self.logger = logging.getLogger(__name__)
        self.spreadsheet_id = spreadsheet_id
        self.logger.info("Initializing SheetsClient...")
        self.service = self.get_sheets_service()
    
    def get_sheets_service(self):
        try:
            self.logger.info("Loading Google credentials...")
            credentials_string = GOOGLE_CREDENTIALS.strip()
            if credentials_string.startswith('"') and credentials_string.endswith('"'):
                credentials_string = credentials_string[1:-1]
            if credentials_string.startswith("'") and credentials_string.endswith("'"):
                credentials_string = credentials_string[1:-1]
                
            credentials_info = json.loads(credentials_string)
            
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON parsing error: {str(e)}")
            self.logger.error(f"Received GOOGLE_CREDENTIALS: {GOOGLE_CREDENTIALS[:100]}...")
            raise
            
        creds = service_account.Credentials.from_service_account_info(
            credentials_info,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        self.logger.info("Google Sheets service initialized.")
        return build('sheets', 'v4', credentials=creds, cache_discovery=False)
    
    def append_expense(self, date, description, amount, currency, cash=False, user='default_user'):
        self.logger.info(f"Appending expense: {date}, {description}, {amount}, {currency}, {cash}, {user}")
        values = [[date, description, amount, currency, cash, user]]
        body = {'values': values}
        self.service.spreadsheets().values().append(
            spreadsheetId=self.spreadsheet_id,
            range='Expenses!A:F',
            valueInputOption='USER_ENTERED',
            body=body
        ).execute()
        self.logger.info("Expense appended successfully.")
