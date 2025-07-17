from telegram_bot import DealsBot
from config import Config
import logging

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    """Main function to run the bot"""
    try:
        # Get token from Config
        token = Config.TELEGRAM_BOT_TOKEN
        
        if not token or token == "your_actual_bot_token_here":
            print("❌ Error: TELEGRAM_BOT_TOKEN not found!")
            print("Please follow these steps:")
            print("1. Get a bot token from @BotFather on Telegram")
            print("2. Update the .env file with your actual token")
            print("3. Or update the config.py file directly")
            return
        
        # Create and run bot
        bot = DealsBot(token)
        bot.run()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Error running bot: {str(e)}")
        raise

if __name__ == '__main__':
    main()
