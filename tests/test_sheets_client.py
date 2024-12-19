import pytest
from unittest.mock import patch, MagicMock
from src.sheets.client import SheetsClient

@pytest.fixture
@patch('src.sheets.client.build')
@patch('src.sheets.client.service_account.Credentials.from_service_account_info')
@patch('src.sheets.client.GOOGLE_CREDENTIALS', '{"type": "service_account"}')
def sheets_client(mock_creds, mock_build):
    mock_service = MagicMock()
    mock_build.return_value = mock_service
    return SheetsClient('test_spreadsheet_id')

def test_initialization(sheets_client):
    assert sheets_client.service is not None
    assert sheets_client.spreadsheet_id == 'test_spreadsheet_id'

def test_append_expense(sheets_client):
    sheets_client.append_expense('2024-01-01', 'Food', 100, 'Groceries')
    sheets_client.service.spreadsheets().values().append.assert_called_once()
