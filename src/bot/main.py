import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from src.agent.main import ExpenseTrackingAgent
from src.sheets.client import SheetsClient
from src.config import TELEGRAM_TOKEN, GOOGLE_SHEETS_ID

class ExpenseBot:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing SheetsClient...")
        sheets_client = SheetsClient(GOOGLE_SHEETS_ID)
        
        self.logger.info("Initializing ExpenseTrackingAgent...")
        self.agent = ExpenseTrackingAgent(sheets_client)
        
        self.logger.info("Setting up Telegram bot...")
        self.app = Application.builder().token(TELEGRAM_TOKEN).build()
        
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(MessageHandler(filters.TEXT, self.handle_message))

    async def start_command(self, update: Update, context):
        self.logger.info("Received /start command")
        await update.message.reply_text(
            "Hello! I will help you track your expenses. Just send me the expense information."
        )

    async def handle_message(self, update: Update, context):
        self.logger.info(f"Received message: {update.message.text}")
        response = await self.agent.process_message(update.message.text)
        await update.message.reply_text(response)

    def run(self):
        self.logger.info("Starting bot polling...")
        self.app.run_polling()

