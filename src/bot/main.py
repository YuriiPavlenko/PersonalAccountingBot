import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from telegram.error import Conflict
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
        
        # Add handlers
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(MessageHandler(filters.TEXT, self.handle_message))
        self.app.add_handler(CallbackQueryHandler(self.handle_button))
        
        # Add error handler
        self.app.add_error_handler(self.error_handler)
        
        # Store pending expenses
        self.pending_expenses = {}

    async def start_command(self, update: Update, context):
        self.logger.info("Received /start command")
        await update.message.reply_text(
            "Hello! I will help you track your expenses. Just send me the expense information."
        )

    async def handle_message(self, update: Update, context):
        chat_id = update.message.chat_id
        self.logger.info(f"Received message from chat_id {chat_id}: {update.message.text}")
        
        if chat_id in self.pending_expenses:
            self.logger.info(f"Found pending expense for chat_id {chat_id}, processing correction")
            expense_data = await self.agent.process_correction(
                self.pending_expenses[chat_id],
                update.message.text
            )
        else:
            self.logger.info(f"Processing new expense for chat_id {chat_id}")
            expense_data = await self.agent.process_message(update.message.text)
        
        if expense_data:
            self.logger.info(f"Storing pending expense for chat_id {chat_id}: {expense_data}")
            self.pending_expenses[chat_id] = expense_data
            
            keyboard = [
                [
                    InlineKeyboardButton("Yes ✅", callback_data="confirm"),
                    InlineKeyboardButton("No ❌", callback_data="reject")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            self.logger.info(f"Sending confirmation request to chat_id {chat_id}")
            await update.message.reply_text(
                f"I'll add this expense:\n{expense_data['summary']}\n\nIs this correct?",  # Use only the formatted summary
                reply_markup=reply_markup
            )
        else:
            self.logger.warning(f"Failed to process expense for chat_id {chat_id}")
            await update.message.reply_text("I couldn't understand the expense. Please try again.")

    async def handle_button(self, update: Update, context):
        query = update.callback_query
        chat_id = query.message.chat_id
        self.logger.info(f"Received button callback from chat_id {chat_id}: {query.data}")
        await query.answer()
        self.logger.info(f"Answered callback query for chat_id {chat_id}")
        
        if chat_id not in self.pending_expenses:
            self.logger.warning(f"No pending expense found for chat_id {chat_id}")
            await query.message.reply_text("No pending expense found. Please start over.")
            return
        
        if query.data == "confirm":
            self.logger.info(f"Processing confirmation for chat_id {chat_id}")
            try:
                expense_data = self.pending_expenses[chat_id]
                self.logger.info(f"Writing expense data: {expense_data}")
                await self.agent.write_expense(expense_data)
                self.logger.info(f"Successfully recorded expense for chat_id {chat_id}")
                await query.message.reply_text("✅ Expense successfully recorded!")
            except Exception as e:
                self.logger.error(f"Failed to record expense for chat_id {chat_id}: {str(e)}")
                await query.message.reply_text(f"❌ Failed to record expense: {str(e)}")
            finally:
                self.logger.info(f"Clearing pending expense for chat_id {chat_id}")
                del self.pending_expenses[chat_id]
        
        elif query.data == "reject":
            self.logger.info(f"User rejected expense for chat_id {chat_id}")
            await query.message.reply_text(
                "Please tell me what needs to be corrected, and I'll adjust the entry."
            )

    async def error_handler(self, update: Update, context):
        """Handle errors caused by updates."""
        self.logger.error(f"Update {update} caused error {context.error}")
        
        if isinstance(context.error, Conflict):
            self.logger.error("Bot instance conflict detected. Another instance is already running.")
            # You might want to exit the application here
            import sys
            sys.exit(1)
        else:
            # Handle other errors
            if update and update.effective_message:
                await update.effective_message.reply_text(
                    "Sorry, something went wrong. Please try again later."
                )

    def run(self):
        """Run the bot."""
        self.logger.info("Starting bot polling...")
        try:
            self.app.run_polling()
        except Exception as e:
            self.logger.error(f"Error running bot: {e}")
            raise

