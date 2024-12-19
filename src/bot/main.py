from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from src.agent.main import ExpenseTrackingAgent
from src.sheets.client import SheetsClient
from src.config import TELEGRAM_TOKEN, GOOGLE_SHEETS_ID
from langchain_community.chat_models import ChatOpenAI

class ExpenseBot:
    def __init__(self):
        sheets_client = SheetsClient(GOOGLE_SHEETS_ID)
        self.agent = ExpenseTrackingAgent(sheets_client)
        self.app = Application.builder().token(TELEGRAM_TOKEN).build()
        
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(MessageHandler(filters.TEXT, self.handle_message))

    async def start_command(self, update: Update, context):
        await update.message.reply_text(
            "Привет! Я помогу вам отслеживать расходы. Просто отправьте мне информацию о расходе."
        )

    async def handle_message(self, update: Update, context):
        response = await self.agent.process_message(update.message.text)
        await update.message.reply_text(response)

    def run(self):
        self.app.run_polling()

