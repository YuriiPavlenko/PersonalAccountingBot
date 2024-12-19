import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from telegram import InlineKeyboardMarkup
from src.agent.main import ExpenseTrackingAgent
from src.bot.main import ExpenseBot

@pytest.fixture
@patch('src.bot.main.SheetsClient', autospec=True)
@patch('src.bot.main.ExpenseTrackingAgent', autospec=True)
@patch('src.bot.main.Application', autospec=True)
def expense_bot(mock_application, mock_agent, mock_sheets_client):
    mock_app = MagicMock()
    mock_application.builder().token().build.return_value = mock_app
    mock_agent_instance = mock_agent.return_value
    return ExpenseBot()
    return ExpenseBot()

def test_initialization(expense_bot):
    assert expense_bot.app is not None
    assert expense_bot.agent is not None
    assert expense_bot.pending_expenses == {}

@pytest.mark.asyncio
async def test_start_command(expense_bot):
    update = AsyncMock()
    context = MagicMock()
    await expense_bot.start_command(update, context)
    update.message.reply_text.assert_called_once_with(
        "Hello! I will help you track your expenses. Just send me the expense information."
    )

@pytest.mark.asyncio
async def test_handle_message_new_expense(expense_bot):
    update = AsyncMock()
    update.message.chat_id = 123
    context = MagicMock()
    
    mock_expense_data = {
        "data": {
            "date": "2024-01-01",
            "amount": 100,
            "currency": "THB",
            "description": "Test expense",
            "cash": True,
            "user": "test_user"
        },
        "summary": "Test expense summary"
    }
    
    expense_bot.agent.process_message = AsyncMock(return_value=mock_expense_data)
    await expense_bot.handle_message(update, context)
    
    # Check if expense was stored in pending_expenses
    assert expense_bot.pending_expenses[123] == mock_expense_data
    
    # Verify that reply contains both summary and confirmation buttons
    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    assert mock_expense_data["summary"] in call_args[0][0]
    assert isinstance(call_args[1]["reply_markup"], InlineKeyboardMarkup)

@pytest.mark.asyncio
async def test_handle_message_correction(expense_bot):
    update = AsyncMock()
    update.message.chat_id = 123
    context = MagicMock()
    
    # Set up a pending expense
    mock_previous_expense = {
        "data": {"date": "2024-01-01"},
        "summary": "Previous expense"
    }
    expense_bot.pending_expenses[123] = mock_previous_expense
    
    mock_corrected_expense = {
        "data": {"date": "2024-01-02"},
        "summary": "Corrected expense"
    }
    expense_bot.agent.process_correction = AsyncMock(return_value=mock_corrected_expense)
    
    await expense_bot.handle_message(update, context)
    
    # Verify correction was processed
    expense_bot.agent.process_correction.assert_called_once_with(
        mock_previous_expense,
        update.message.text
    )
    
    # Check if corrected expense was stored
    assert expense_bot.pending_expenses[123] == mock_corrected_expense

@pytest.mark.asyncio
@patch.object(ExpenseTrackingAgent, 'write_expense', new_callable=AsyncMock)
async def test_handle_button_confirm(mock_write_expense, expense_bot):
    query = AsyncMock()
    query.message.chat_id = 123
    query.data = "confirm"
    context = MagicMock()
    
    mock_expense = {
        "data": {"date": "2024-01-01"},
        "summary": "Test expense"
    }
    expense_bot.pending_expenses[123] = mock_expense
    
    query.answer = AsyncMock(return_value=None)
    query.message.reply_text = AsyncMock()
    await expense_bot.handle_button(query, context)
    query.answer.assert_called_once()
    
    # Verify expense was written
    mock_write_expense.assert_called_once_with(mock_expense)
    
    # Verify success message
    query.message.reply_text.assert_called_once_with("✅ Expense successfully recorded!")
    
    # Verify pending expense was cleared
    assert 123 not in expense_bot.pending_expenses

@pytest.mark.asyncio
async def test_handle_button_reject(expense_bot):
    query = AsyncMock()
    query.message.chat_id = 123
    query.data = "reject"
    context = MagicMock()
    
    mock_expense = {
        "data": {"date": "2024-01-01"},
        "summary": "Test expense"
    }
    expense_bot.pending_expenses[123] = mock_expense
    
    await expense_bot.handle_button(query, context)
    
    # Verify correction message
    query.message.reply_text.assert_called_once_with(
        "Please tell me what needs to be corrected, and I'll adjust the entry."
    )
    
    # Verify pending expense remains
    assert expense_bot.pending_expenses[123] == mock_expense
