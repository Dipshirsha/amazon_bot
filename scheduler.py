import schedule
import time
import threading
import asyncio
import logging
from datetime import datetime

# Configure logging for scheduler
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class DealScheduler:
    def __init__(self, bot):
        self.bot = bot
        self.is_running = False
        self.scheduler_thread = None
    
    def schedule_daily_deals(self):
        """Schedule daily deal announcements"""

        def run_all_categories_midnight():
            categories = [
                ("fashion", 15),
                ("electronics", 20),
                ("home", 10),
                ("sports", 15),
                ("books", 10)
            ]
            for name, discount in categories:
                try:
                    log_msg = f"Scheduled Post - Category: {name.upper()}, Type: Product, Min Discount: {discount}%"
                    logger.info(log_msg)
                    asyncio.run(self.bot.send_deals_to_channel(name, min_discount=discount))
                    time.sleep(10)
                except Exception as e:
                    logger.error(f"Error posting {name} at midnight: {e}")

        schedule.clear()
        
        # Core: all categories at midnight
        schedule.every().day.at("00:00").do(run_all_categories_midnight)

        # (Optional: keep your extra time slots below, using the same style if you want)
        def run_morning_deals():
            logger.info("Scheduled Post - Type: Summary, Slot: Morning")
            try:
                asyncio.run(self.bot.send_daily_deals_summary())
            except Exception as e:
                logger.error(f"Error in morning deals: {e}")

        def run_evening_deals():
            logger.info("Scheduled Post - Type: Summary, Slot: Evening")
            try:
                asyncio.run(self.bot.send_daily_deals_summary())
            except Exception as e:
                logger.error(f"Error in evening deals: {e}")

        def run_flash_deals():
            logger.info("Scheduled Post - Type: Flash Deal")
            try:
                products = self.bot.scraper.scrape_search_results()
                if products:
                    best_deals_df = self.bot.scraper.filter_best_deals(products)
                    flash_deals = best_deals_df[best_deals_df['discount_percent'] > 40]
                    if not flash_deals.empty:
                        asyncio.run(self.bot.send_flash_deal(flash_deals.iloc[0]))
                        logger.info(f"Flash deal sent: {flash_deals.iloc[0]['title'][:50]}...")
                    else:
                        logger.info("No flash deals found this time")
                else:
                    logger.info("No products found for flash deals")
            except Exception as e:
                logger.error(f"Error in flash deals: {e}")

        # Optional: uncomment to keep these
        # schedule.every().day.at("09:00").do(run_morning_deals)
        # schedule.every().day.at("18:00").do(run_evening_deals)
        # schedule.every(2).hours.do(run_flash_deals)

        logger.info("Scheduler configured:")
        logger.info("  - All categories: 12:00 AM")
        # logger.info("  - Morning deals: 9:00 AM")
        # logger.info("  - Evening deals: 6:00 PM")
        # logger.info("  - Flash deals: Every 2 hours")
    
    def start_scheduler(self):
        if self.is_running:
            logger.warning("Scheduler already running!")
            return
        self.is_running = True
        def run_scheduler():
            logger.info("Scheduler thread started")
            while self.is_running:
                try:
                    schedule.run_pending()
                    time.sleep(60)
                except Exception as e:
                    logger.error(f"Scheduler error: {e}")
                    time.sleep(60)
        self.scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        self.scheduler_thread.start()
        logger.info("Scheduler started successfully!")
    
    def stop_scheduler(self):
        self.is_running = False
        schedule.clear()
        logger.info("Scheduler stopped!")
    
    def get_next_run_time(self):
        next_run = schedule.next_run()
        if next_run:
            return next_run.strftime('%Y-%m-%d %H:%M:%S')
        return "No scheduled jobs"
    
    def list_scheduled_jobs(self):
        jobs = schedule.jobs
        if jobs:
            for job in jobs:
                logger.info(f"Scheduled job: {job}")
        else:
            logger.info("No scheduled jobs")
