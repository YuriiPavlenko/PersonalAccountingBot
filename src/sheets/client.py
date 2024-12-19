import json
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from src.config import GOOGLE_CREDENTIALS

class SheetsClient:
    def __init__(self, spreadsheet_id):
        self.spreadsheet_id = spreadsheet_id
        self.service = self.get_sheets_service()
    
    def get_sheets_service(self):
        try:
            # Очищаем строку от лишних символов
            credentials_string = GOOGLE_CREDENTIALS.strip()
            # Удаляем лишние кавычки, если они есть
            if credentials_string.startswith('"') and credentials_string.endswith('"'):
                credentials_string = credentials_string[1:-1]
            if credentials_string.startswith("'") and credentials_string.endswith("'"):
                credentials_string = credentials_string[1:-1]
                
            credentials_info = json.loads(credentials_string)
            
        except json.JSONDecodeError as e:
            print(f"Ошибка парсинга JSON: {str(e)}")
            print(f"Полученное значение GOOGLE_CREDENTIALS: {GOOGLE_CREDENTIALS[:100]}...")
            raise
            
        creds = service_account.Credentials.from_service_account_info(
            credentials_info,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        return build('sheets', 'v4', credentials=creds, cache_discovery=False)
    
    def append_expense(self, date, category, amount, description):
        values = [[date, category, amount, description]]
        body = {'values': values}
        self.service.spreadsheets().values().append(
            spreadsheetId=self.spreadsheet_id,
            range='Expenses!A:D',
            valueInputOption='USER_ENTERED',
            body=body
        ).execute()
