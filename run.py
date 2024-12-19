import logging
from src.bot.main import ExpenseBot

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    logger.info("Starting ExpenseBot...")
    bot = ExpenseBot()
    bot.run()