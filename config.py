import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram Bot Configuration
    BOT_TOKEN = os.getenv('BOT_TOKEN', '7680961829:AAH80RDjOAsJUbFihPO3Az9mOgQO57pLe2M')
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', BOT_TOKEN)  # Use BOT_TOKEN as fallback
    CHANNEL_ID = os.getenv('CHANNEL_ID', '-1002774376445')
    
    # Amazon Scraper Configuration
    AFFILIATE_TAG = os.getenv('AFFILIATE_TAG', 'dip090-21')
    SEARCH_TERM = os.getenv('SEARCH_TERM', 'laptop')
    MAX_PAGES = int(os.getenv('MAX_PAGES', '3'))
    MIN_DISCOUNT = float(os.getenv('MIN_DISCOUNT', '15'))
    MIN_REVIEW_COUNT = int(os.getenv('MIN_REVIEW_COUNT', '50'))
    MIN_BUDGET = float(os.getenv('MIN_BUDGET', '20000'))
    MAX_BUDGET = float(os.getenv('MAX_BUDGET', '150000'))
    
    # Scheduler Configuration
    MORNING_DEALS_TIME = os.getenv('MORNING_DEALS_TIME', '09:00')
    EVENING_DEALS_TIME = os.getenv('EVENING_DEALS_TIME', '18:00')
    FLASH_DEALS_INTERVAL = int(os.getenv('FLASH_DEALS_INTERVAL', '1'))  # hours
