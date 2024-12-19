import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_SHEETS_ID = os.getenv("GOOGLE_SHEETS_ID")
GOOGLE_CREDENTIALS = os.getenv("GOOGLE_CREDENTIALS")
HIS_TG_ID = os.getenv("HIS_TG_ID")
HER_TG_ID = os.getenv("HER_TG_ID")