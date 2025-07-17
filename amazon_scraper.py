from bs4 import BeautifulSoup
import requests
import pandas as pd
import numpy as np
import time
import re
from urllib.parse import urljoin, urlparse, parse_qs, urlencode
from datetime import datetime

class AmazonDealsScraper:
    def __init__(self, search_term="laptop", max_pages=5, min_discount=10, 
                 min_review_count=10, min_budget=0, max_budget=float('inf'),
                 affiliate_tag="dip090-21"):
        self.search_term = search_term
        self.max_pages = max_pages
        self.min_discount = min_discount
        self.min_review_count = min_review_count
        self.min_budget = min_budget
        self.max_budget = max_budget
        self.affiliate_tag = affiliate_tag
        self.base_url = "https://www.amazon.in"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'en-IN,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }

    def convert_to_affiliate_link(self, product_url):
        """Convert regular Amazon product URL to affiliate link"""
        if not self.affiliate_tag:
            return product_url
        
        try:
            # Extract ASIN from URL
            asin = None
            if '/dp/' in product_url:
                asin = product_url.split('/dp/')[1].split('/')[0].split('?')[0]
            elif '/gp/product/' in product_url:
                asin = product_url.split('/gp/product/')[1].split('/')[0].split('?')[0]
            
            if not asin:
                return product_url
            
            # Create affiliate link
            affiliate_url = f"https://www.amazon.in/dp/{asin}?tag={self.affiliate_tag}"
            return affiliate_url
            
        except Exception as e:
            print(f"Error converting to affiliate link: {e}")
            return product_url

    def extract_price(self, price_text):
        """Extract numeric price from Indian price string (Ã¢â€šÂ¹)"""
        if not price_text:
            return None
        price_clean = price_text.replace('Ã¢â€šÂ¹', '').replace(',', '')
        price_match = re.search(r'[\d,]+\.?\d*', price_clean)
        return float(price_match.group()) if price_match else None

    def is_available(self, soup):
        """Check if product is available in India"""
        availability_indicators = [
            "In stock", "Available", "Only.*left in stock",
            "Usually dispatched", "Ships from and sold by Amazon"
        ]
        
        availability_section = soup.find("div", {"id": "availability"})
        if availability_section:
            availability_text = availability_section.get_text().strip()
            
            unavailable_indicators = [
                "Currently unavailable", "Out of stock", "Temporarily out of stock",
                "This item is not available", "Item not available"
            ]
            
            for indicator in unavailable_indicators:
                if indicator.lower() in availability_text.lower():
                    return False
            
            for indicator in availability_indicators:
                if re.search(indicator, availability_text, re.IGNORECASE):
                    return True
        
        add_to_cart = soup.find("input", {"id": "add-to-cart-button"})
        if add_to_cart and not add_to_cart.get("disabled"):
            return True
        
        buy_now = soup.find("input", {"id": "buy-now-button"})
        if buy_now and not buy_now.get("disabled"):
            return True
        
        return False

    def get_product_details(self, soup, original_url):
        """Extract product details from individual product page"""
        details = {
            'title': '', 'current_price': '', 'original_price': '',
            'discount_percent': 0, 'rating': '', 'review_count': '',
            'availability': '', 'prime_eligible': False, 'is_available': False,
            'original_url': original_url,
            'affiliate_url': self.convert_to_affiliate_link(original_url)
        }

        try:
            details['is_available'] = self.is_available(soup)
            
            if not details['is_available']:
                return details

            # Title
            title_elem = soup.find("span", {"id": "productTitle"})
            details['title'] = title_elem.text.strip() if title_elem else ""

            # Current Price
            price_selectors = [
                "span.a-price-whole",
                "span#priceblock_ourprice",
                "span#priceblock_dealprice",
                "span.a-price.a-text-price.a-size-medium.apexPriceToPay span.a-offscreen",
                "span.a-price-symbol + span.a-price-whole"
            ]
            
            current_price = ""
            for selector in price_selectors:
                price_elem = soup.select_one(selector)
                if price_elem:
                    current_price = price_elem.text.strip()
                    break
            details['current_price'] = current_price

            # Original Price
            original_price_selectors = [
                "span.a-price.a-text-price span.a-offscreen",
                "span#listPrice",
                "span.a-price-was span.a-offscreen"
            ]
            
            original_price = ""
            for selector in original_price_selectors:
                price_elem = soup.select_one(selector)
                if price_elem:
                    original_price = price_elem.text.strip()
                    break
            details['original_price'] = original_price

            # Calculate discount
            current_price_num = self.extract_price(current_price)
            original_price_num = self.extract_price(original_price)
            details['discount_percent'] = self.calculate_discount(current_price_num, original_price_num)

            # Rating
            rating_elem = soup.select_one("span.a-icon-alt")
            if rating_elem:
                rating_text = rating_elem.text.strip()
                rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                details['rating'] = rating_match.group(1) if rating_match else ""

            # Review Count
            review_elem = soup.select_one("span#acrCustomerReviewText")
            details['review_count'] = review_elem.text.strip() if review_elem else ""

            # Availability Status
            availability_elem = soup.select_one("div#availability span")
            details['availability'] = availability_elem.text.strip() if availability_elem else "Available"

            # Prime Eligible
            prime_elem = soup.select_one("span.a-icon-prime")
            details['prime_eligible'] = bool(prime_elem)

        except Exception as e:
            print(f"Error extracting product details: {e}")

        return details

    def calculate_discount(self, current_price, original_price):
        """Calculate discount percentage"""
        if not current_price or not original_price or original_price <= current_price:
            return 0
        return round(((original_price - current_price) / original_price) * 100, 2)

    def scrape_search_results(self):
        """Scrape multiple pages of search results from Amazon India"""
        all_products = []
        
        for page in range(1, self.max_pages + 1):
            print(f"Scraping Amazon India page {page} of {self.max_pages}...")
            
            search_url = f"{self.base_url}/s?k={self.search_term}&page={page}"
            
            try:
                response = requests.get(search_url, headers=self.headers)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, "html.parser")
                
                product_links = soup.find_all("a", {"class": "a-link-normal"})
                product_urls = []
                
                for link in product_links:
                    href = link.get('href')
                    if href and '/dp/' in href:
                        full_url = urljoin(self.base_url, href)
                        product_urls.append(full_url)
                
                product_urls = list(set(product_urls))
                
                for url in product_urls[:10]:
                    try:
                        time.sleep(1)
                        product_response = requests.get(url, headers=self.headers)
                        product_soup = BeautifulSoup(product_response.content, "html.parser")
                        
                        product_details = self.get_product_details(product_soup, url)
                        
                        if product_details['is_available']:
                            product_details['page'] = page
                            all_products.append(product_details)
                            print(f"Found available product: {product_details['title'][:50]}...")
                            
                    except Exception as e:
                        print(f"Error scraping product {url}: {e}")
                        continue
                
                time.sleep(2)
                
            except Exception as e:
                print(f"Error scraping page {page}: {e}")
                continue
        
        return all_products

    def filter_best_deals(self, products):
        """Filter and rank available products by best deals"""
        df = pd.DataFrame(products)
        if df.empty:
            return df

        df = df[df['is_available'] == True]
        df = df[df['title'] != '']
        df = df[df['current_price'] != '']

        df['current_price_num'] = df['current_price'].apply(self.extract_price)
        df['original_price_num'] = df['original_price'].apply(self.extract_price)

        df = df[(df['current_price_num'] >= self.min_budget) & 
                (df['current_price_num'] <= self.max_budget)]
        df = df[df['discount_percent'] >= self.min_discount]

        df['rating_num'] = pd.to_numeric(df['rating'], errors='coerce')

        df['review_count_num'] = df['review_count'].apply(
            lambda x: int(re.search(r'(\d+)', str(x).replace(',', '')).group(1)) 
            if x and re.search(r'(\d+)', str(x).replace(',', '')) else 0
        )

        df = df[df['review_count_num'] >= self.min_review_count]

        df['deal_score'] = (
            df['discount_percent'] * 0.4 +
            df['rating_num'].fillna(0) * 10 * 0.3 +
            np.log1p(df['review_count_num']) * 0.7
        )

        df = df.sort_values('deal_score', ascending=False)
        return df

    def save_to_csv(self, df, filename=None):
        """Save available products to CSV file"""
        if df.empty:
            print("No available products found to save.")
            return df

        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f'amazon_india_affiliate_deals_{timestamp}.csv'

        output_columns = [
            'title', 'current_price', 'original_price', 'discount_percent',
            'rating', 'review_count', 'availability', 'prime_eligible',
            'deal_score', 'page', 'original_url', 'affiliate_url'
        ]

        df_output = df[output_columns].copy()
        df_output.to_csv(filename, index=False)
        print(f"Available products with affiliate links saved to {filename}")
        return df_output

    def display_filter_summary(self):
        """Display current filter settings"""
        print("\n" + "="*50)
        print("FILTER SETTINGS SUMMARY")
        print("="*50)
        print(f"Search Term: {self.search_term}")
        print(f"Max Pages: {self.max_pages}")
        print(f"Min Discount: {self.min_discount}%")
        print(f"Min Review Count: {self.min_review_count}")
        print(f"Affiliate Tag: {self.affiliate_tag}")
        if self.min_budget > 0:
            print(f"Min Budget: Ã¢â€šÂ¹{self.min_budget:,.0f}")
        if self.max_budget != float('inf'):
            print(f"Max Budget: Ã¢â€šÂ¹{self.max_budget:,.0f}")
        print("="*50)