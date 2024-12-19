import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.bot.main import ExpenseBot

@pytest.fixture
@patch('src.bot.main.SheetsClient')
@patch('src.bot.main.ExpenseTrackingAgent')
@patch('src.bot.main.Application')
def expense_bot(mock_application, mock_agent, mock_sheets_client):
    mock_app = MagicMock()
    mock_application.builder().token().build.return_value = mock_app
    return ExpenseBot()

def test_initialization(expense_bot):
    assert expense_bot.app is not None
    assert expense_bot.agent is not None

@pytest.mark.asyncio
async def test_start_command(expense_bot):
    update = AsyncMock()
    context = MagicMock()
    await expense_bot.start_command(update, context)
    update.message.reply_text.assert_called_once_with(
        "Hello! I will help you track your expenses. Just send me the expense information."
    )

@pytest.mark.asyncio
async def test_handle_message(expense_bot):
    update = AsyncMock()
    context = MagicMock()
    expense_bot.agent.process_message = AsyncMock(return_value="Processed message")
    await expense_bot.handle_message(update, context)
    update.message.reply_text.assert_called_once_with("Processed message")
