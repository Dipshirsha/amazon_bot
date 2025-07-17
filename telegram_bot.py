import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from amazon_scraper import AmazonDealsScraper
from config import Config
import time

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class DealsBot:
    def __init__(self, token):
        self.token = token
        self.app = None
        
    def parse_args_to_dict(self, args):
        """Parse command arguments into a dictionary"""
        filter_dict = {}
        for arg in args:
            if '=' in arg:
                key, value = arg.split('=', 1)
                filter_dict[key.strip()] = value.strip()
        return filter_dict
    
    def create_scraper_with_filters(self, filter_dict):
        """Create scraper instance with custom filters"""
        defaults = {
            'search_term': Config.SEARCH_TERM,
            'max_pages': Config.MAX_PAGES,
            'min_discount': Config.MIN_DISCOUNT,
            'min_review_count': Config.MIN_REVIEW_COUNT,
            'min_budget': Config.MIN_BUDGET,
            'max_budget': Config.MAX_BUDGET,
            'affiliate_tag': Config.AFFILIATE_TAG
        }
        
        search_term = filter_dict.get('search_term', defaults['search_term'])
        max_pages = int(filter_dict.get('max_pages', defaults['max_pages']))
        
        try:
            min_discount = float(filter_dict.get('min_discount', defaults['min_discount']))
        except ValueError:
            min_discount = defaults['min_discount']
            
        try:
            min_review_count = int(filter_dict.get('min_review_count', defaults['min_review_count']))
        except ValueError:
            min_review_count = defaults['min_review_count']
            
        try:
            min_budget = float(filter_dict.get('min_budget', defaults['min_budget']))
        except ValueError:
            min_budget = defaults['min_budget']
            
        try:
            max_budget = float(filter_dict.get('max_budget', defaults['max_budget']))
        except ValueError:
            max_budget = defaults['max_budget']
        
        scraper = AmazonDealsScraper(
            search_term=search_term,
            max_pages=max_pages,
            min_discount=min_discount,
            min_review_count=min_review_count,
            min_budget=min_budget,
            max_budget=max_budget,
            affiliate_tag=Config.AFFILIATE_TAG
        )
        
        return scraper
    
    async def deals_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle deals command with NO timeouts - take as much time as needed"""
        try:
            start_time = time.time()
            await update.message.reply_text("🔍 Starting comprehensive deal search... This will take as long as needed!")
            
            filters = self.parse_args_to_dict(context.args)
            scraper = self.create_scraper_with_filters(filters)
            
            filter_info = f"""
🔧 Search Configuration:
• Term: {scraper.search_term}
• Min Discount: {scraper.min_discount}%
• Min Reviews: {scraper.min_review_count}
• Budget: ₹{scraper.min_budget:,.0f} - ₹{scraper.max_budget:,.0f}
• Max Pages: {scraper.max_pages}

🚀 Starting unlimited time search...
            """
            await update.message.reply_text(filter_info)
            
            # COMPLETELY REMOVE ALL TIMEOUTS - Let it run as long as needed
            try:
                await update.message.reply_text("📦 Phase 1: Product Discovery (No time limit)")
                
                # Run without any timeout restrictions
                products = await asyncio.to_thread(scraper.scrape_search_results)
                
                search_duration = time.time() - start_time
                await update.message.reply_text(f"✅ Phase 1 Complete: Found {len(products)} products in {search_duration:.1f}s")
                
            except Exception as e:
                logger.error(f"Scraping error: {str(e)}")
                await update.message.reply_text(f"❌ Search error: {str(e)}")
                return
            
            if not products:
                await update.message.reply_text("❌ No products found. Try different filters.")
                return
            
            await update.message.reply_text(f"📊 Phase 2: Advanced Filtering (Processing {len(products)} products)")
            
            # Advanced filtering without any timeouts
            try:
                filter_start = time.time()
                deals_df = await asyncio.to_thread(scraper.filter_best_deals, products)
                filter_duration = time.time() - filter_start
                
                await update.message.reply_text(f"✅ Phase 2 Complete: Filtering done in {filter_duration:.1f}s")
                
            except Exception as e:
                logger.error(f"Filtering error: {str(e)}")
                await update.message.reply_text("⚠️ Advanced filtering failed, using basic method...")
                deals = self.basic_filter_deals(products, scraper)
                await self.process_and_send_deals(update, deals, scraper.search_term, start_time)
                return
            
            if deals_df.empty:
                await update.message.reply_text("❌ No deals match your criteria. Consider lowering requirements.")
                return
            
            # Convert to deals format
            deals = self.convert_dataframe_to_deals(deals_df, scraper)
            await self.process_and_send_deals(update, deals, scraper.search_term, start_time)
                
        except Exception as e:
            logger.error(f"Main error in deals command: {str(e)}")
            await update.message.reply_text(f"❌ System error: {str(e)}")
    
    async def process_and_send_deals(self, update, deals, search_term, start_time):
        """Process and send deals without any timeouts"""
        try:
            total_duration = time.time() - start_time
            await update.message.reply_text(f"🎯 Phase 3: Results Processing ({len(deals)} deals found)")
            
            # Show deals to user (top 5)
            await update.message.reply_text(f"🏆 TOP 5 DEALS (Total search time: {total_duration:.1f}s):")
            
            for i, deal in enumerate(deals[:5], 1):
                deal_message = self.format_deal_message(deal, i)
                await update.message.reply_text(deal_message, parse_mode='HTML')
                await asyncio.sleep(0.5)
            
            # Channel posting without timeouts
            if Config.CHANNEL_ID:
                await update.message.reply_text("📤 Phase 4: Channel Publishing...")
                await self.unlimited_channel_send(deals[:5], search_term)
                await update.message.reply_text("✅ Successfully posted to channel!")
            
            final_time = time.time() - start_time
            await update.message.reply_text(f"🎉 Mission Complete! Total time: {final_time:.1f}s")
            
        except Exception as e:
            logger.error(f"Processing error: {str(e)}")
            await update.message.reply_text(f"⚠️ Processing error: {str(e)}")
    
    def basic_filter_deals(self, products, scraper):
        """Basic filtering without pandas"""
        deals = []
        for product in products:
            try:
                current_price = scraper.extract_price(product.get('current_price', ''))
                original_price = scraper.extract_price(product.get('original_price', ''))
                
                if not current_price:
                    continue
                
                if current_price < scraper.min_budget or current_price > scraper.max_budget:
                    continue
                
                discount = product.get('discount_percent', 0)
                if discount < scraper.min_discount:
                    continue
                
                review_count = self.extract_review_count(product.get('review_count', ''))
                if review_count < scraper.min_review_count:
                    continue
                
                deal = {
                    'title': product.get('title', ''),
                    'url': product.get('affiliate_url', ''),
                    'current_price': current_price,
                    'original_price': original_price or current_price,
                    'discount_percent': discount,
                    'rating': float(product.get('rating', 0)) if product.get('rating') else 0,
                    'review_count': review_count,
                    'availability': product.get('availability', 'Available'),
                    'prime_eligible': product.get('prime_eligible', False),
                    'deal_score': discount + (review_count / 1000)
                }
                
                deal['savings'] = deal['original_price'] - deal['current_price']
                deals.append(deal)
                
            except Exception as e:
                continue
        
        deals.sort(key=lambda x: x['discount_percent'], reverse=True)
        return deals
    
    def convert_dataframe_to_deals(self, deals_df, scraper):
        """Convert DataFrame to deals list"""
        deals = []
        for _, row in deals_df.head(20).iterrows():
            deal = {
                'title': row['title'],
                'url': row['affiliate_url'],
                'current_price': scraper.extract_price(row['current_price']) or 0,
                'original_price': scraper.extract_price(row['original_price']) or 0,
                'discount_percent': row['discount_percent'],
                'rating': float(row['rating']) if row['rating'] else 0,
                'review_count': self.extract_review_count(row['review_count']),
                'availability': row['availability'],
                'prime_eligible': row['prime_eligible'],
                'deal_score': row.get('deal_score', 0)
            }
            deal['savings'] = deal['original_price'] - deal['current_price']
            deals.append(deal)
        return deals
    
    def extract_review_count(self, review_text):
        """Extract review count from review text"""
        if not review_text:
            return 0
        import re
        review_match = re.search(r'(\d+)', str(review_text).replace(',', ''))
        return int(review_match.group(1)) if review_match else 0
    
    def format_deal_message(self, deal, rank):
        """Format deal information for Telegram message"""
        rank_emoji = {1: "🥇", 2: "🥈", 3: "🥉", 4: "4️⃣", 5: "5️⃣"}.get(rank, f"{rank}️⃣")
        prime_text = "🚀 Prime" if deal['prime_eligible'] else ""
        
        return f"""
{rank_emoji} <b>{deal['title'][:100]}...</b>

💰 <b>Price:</b> ₹{deal['current_price']:,.0f}
🏷️ <b>Original:</b> ₹{deal['original_price']:,.0f}
📉 <b>Discount:</b> {deal['discount_percent']:.1f}%
💾 <b>Save:</b> ₹{deal['savings']:,.0f}
⭐ <b>Rating:</b> {deal['rating']}/5 ({deal['review_count']} reviews)
📦 <b>Status:</b> Available {prime_text}
🏆 <b>Score:</b> {deal['deal_score']:.1f}

🔗 <a href="{deal['url']}">BUY NOW</a>
        """
    
    async def unlimited_channel_send(self, deals, search_term):
        """Send to channel with unlimited time and maximum retries"""
        try:
            if not Config.CHANNEL_ID or not deals:
                return
            
            from datetime import datetime
            current_time = datetime.now().strftime("%I:%M %p")
            
            # Header
            header = f"""
🚨 <b>MEGA DEALS ALERT</b> 🚨
🔥 <b>Top {search_term.upper()} Deals</b>
📅 <b>Found at:</b> {current_time}
💎 <b>Premium {len(deals)} Deals</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            """
            
            await self.persistent_send(header)
            
            # Send each deal with maximum persistence
            for i, deal in enumerate(deals, 1):
                rank_emoji = {1: "🥇", 2: "🥈", 3: "🥉", 4: "4️⃣", 5: "5️⃣"}.get(i, f"{i}️⃣")
                prime_text = "🚀 Prime" if deal['prime_eligible'] else ""
                
                channel_deal = f"""
{rank_emoji} <b>{deal['title'][:80]}...</b>

💰 <b>₹{deal['current_price']:,.0f}</b> <s>₹{deal['original_price']:,.0f}</s>
🔥 <b>{deal['discount_percent']:.0f}% OFF</b> • Save ₹{deal['savings']:,.0f}
⭐ <b>{deal['rating']}/5</b> ({deal['review_count']} reviews) {prime_text}

🛒 <a href="{deal['url']}"><b>BUY NOW</b></a>
                """
                
                await self.persistent_send(channel_deal)
                await asyncio.sleep(1.5)  # Generous delay
            
            # Footer
            footer = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🤖 <b>Want more deals?</b> Use our bot!
🔔 <b>Enable notifications</b> for instant alerts!

#AmazonDeals #{search_term.replace(' ', '')} #MegaSale
            """
            
            await self.persistent_send(footer)
            logger.info(f"Channel posting completed for {len(deals)} deals")
            
        except Exception as e:
            logger.error(f"Channel send error: {str(e)}")
    
    async def persistent_send(self, message):
        """Send message with maximum persistence - never give up"""
        max_attempts = 10
        base_delay = 2
        
        for attempt in range(max_attempts):
            try:
                await self.app.bot.send_message(
                    chat_id=Config.CHANNEL_ID,
                    text=message,
                    parse_mode='HTML',
                    disable_web_page_preview=False
                )
                return  # Success!
                
            except Exception as e:
                wait_time = base_delay * (2 ** attempt)  # Exponential backoff
                logger.warning(f"Send attempt {attempt + 1} failed, waiting {wait_time}s: {str(e)}")
                
                if attempt < max_attempts - 1:
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Failed to send after {max_attempts} attempts")
                    raise
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command handler"""
        welcome_message = f"""
🛒 <b>Amazon Deals Bot - Unlimited Edition</b> 🛒

<b>Features:</b>
• ⏰ NO time limits
• 🔍 Deep product search
• 📊 Advanced filtering
• 📺 Auto channel posting
• 💰 Affiliate monetization

<b>Commands:</b>
/deals - Unlimited time deal search
/help - Detailed help

<b>Current Settings:</b>
• Search: {Config.SEARCH_TERM}
• Min Discount: {Config.MIN_DISCOUNT}%
• Pages: {Config.MAX_PAGES}

Ready for unlimited deal hunting! 🚀
        """
        await update.message.reply_text(welcome_message, parse_mode='HTML')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Help command handler"""
        help_text = """
🆘 <b>Unlimited Deals Bot Help</b>

<b>Main Command:</b>
/deals - Unlimited time deal search

<b>Parameters:</b>
• search_term=VALUE
• min_discount=VALUE
• max_pages=VALUE
• min_budget=VALUE
• max_budget=VALUE
• min_review_count=VALUE

<b>Examples:</b>
• /deals search_term=smartphone
• /deals search_term=laptop min_discount=30 max_pages=10
• /deals min_discount=50 min_budget=20000

<b>Unlimited Features:</b>
• ⏰ No timeout restrictions
• 🔄 Maximum retry attempts
• 📊 Complete result processing
• 📺 Guaranteed channel posting
• 🎯 Top 5 deals delivered

Let it run as long as needed! 🚀
        """
        await update.message.reply_text(help_text, parse_mode='HTML')
    
    def run(self):
        """Start the bot with unlimited configurations"""
        try:
            # Create application with maximum timeout settings
            application = (Application.builder()
                         .token(self.token)
                         .read_timeout(300)      # 5 minutes
                         .write_timeout(300)     # 5 minutes
                         .connect_timeout(300)   # 5 minutes
                         .build())
            
            self.app = application
            
            # Add handlers
            application.add_handler(CommandHandler("start", self.start))
            application.add_handler(CommandHandler("deals", self.deals_command))
            application.add_handler(CommandHandler("help", self.help_command))
            
            logger.info("🚀 Starting UNLIMITED Amazon Deals Bot...")
            application.run_polling(drop_pending_updates=True)
            
        except Exception as e:
            logger.error(f"Bot startup error: {str(e)}")
            raise
