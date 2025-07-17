# -*- coding: utf-8 -*-
import sys
import os

# Fix encoding issues for Windows
if sys.platform.startswith('win'):
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import csv
import random
import json
import re
from urllib.parse import urljoin, urlparse

class AgodaUltimateScraper:
    def __init__(self, search_url):
        self.search_url = search_url
        self.base_url = "https://www.agoda.com"
        self.all_hotels = []
        self.driver = None
        
    def create_stealth_driver(self):
        """Create Firefox driver with maximum stealth and incognito mode"""
        print("[STEALTH] Initializing Firefox in INCOGNITO MODE...")
        
        options = Options()
        
        # INCOGNITO MODE - Your excellent suggestion!
        options.add_argument("--private-window")
        options.add_argument("--private")
        
        # Maximum stealth configuration
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins")
        options.add_argument("--disable-images")  # Faster loading
        
        # Stealth preferences
        options.set_preference("dom.webdriver.enabled", False)
        options.set_preference("useAutomationExtension", False)
        options.set_preference("general.useragent.override", 
                              "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
        
        # Performance optimization
        options.set_preference("network.http.pipelining", True)
        options.set_preference("network.http.proxy.pipelining", True)
        options.set_preference("network.http.pipelining.maxrequests", 8)
        options.set_preference("content.notify.interval", 500000)
        options.set_preference("content.notify.ontimer", True)
        options.set_preference("content.switch.threshold", 250000)
        
        # Disable images for speed (proxy-like behavior)
        options.set_preference("permissions.default.image", 2)
        
        # Create driver
        self.driver = webdriver.Firefox(options=options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        print("[SUCCESS] Firefox incognito mode initialized successfully!")
        return self.driver
    
    def smart_wait(self, selector, timeout=15, multiple=False):
        """Smart waiting with multiple strategies"""
        try:
            if multiple:
                return WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
                )
            else:
                return WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
        except TimeoutException:
            return None
    
    def close_popups(self):
        """Close any popups or overlays"""
        popup_selectors = [
            'button[aria-label="Close"]',
            '.close-button',
            '[data-selenium="close-button"]',
            'button[data-testid="close-button"]',
            '.modal-close',
            '.popup-close'
        ]
        
        for selector in popup_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if element.is_displayed():
                        element.click()
                        time.sleep(0.5)
            except:
                continue
    
    def progressive_scroll(self, iterations=10):
        """Optimized scrolling to load content"""
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        
        for i in range(iterations):
            # Scroll in small increments
            scroll_position = (i + 1) * (1.0 / iterations)
            self.driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight * {scroll_position});")
            
            # Random human-like delays
            time.sleep(random.uniform(1.5, 2.5))
            
            # Check if new content loaded
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height != last_height:
                last_height = new_height
                time.sleep(1)
    
    def extract_basic_hotel_info(self, card):
        """Extract basic hotel information from search results"""
        # Hotel name and link using your exact selector
        name_elem = card.select_one('a.TextLink__TextLinkStyled-sc-upxc4y-1.iA-DeZb')
        if not name_elem:
            return None
            
        name = name_elem.get_text(strip=True)
        hotel_link = name_elem.get('href')
        
        if not name or not hotel_link:
            return None
        
        # Clean promotional text
        name = re.sub(r'(Limited time offer|Expires in|SUPER WEDNESDAY|NIGHT OWL|MONSOON|BOOK EARLY).*$', '', name, flags=re.IGNORECASE).strip()
        
        # Extract price
        price = "N/A"
        price_elem = card.select_one('span[data-selenium="display-price"]')
        if price_elem:
            price = price_elem.get_text(strip=True)
        
        # Extract location
        location = "N/A"
        location_elem = card.select_one('[data-selenium="hotel-location"]')
        if location_elem:
            location = location_elem.get_text(strip=True)
        
        # Extract rating
        rating = "N/A"
        rating_elem = card.select_one('span[data-selenium="hotel-rating"]')
        if rating_elem:
            rating = rating_elem.get_text(strip=True)
        
        # Construct full URL
        if hotel_link.startswith('/'):
            hotel_url = urljoin(self.base_url, hotel_link)
        else:
            hotel_url = hotel_link
            
        return {
            'name': name,
            'price': price,
            'location': location,
            'rating': rating,
            'url': hotel_url
        }
    
    def extract_room_categories(self, hotel_info):
        """Extract room categories from individual hotel page using exact selectors"""
        try:
            print(f"  -> Visiting: {hotel_info['name']}")
            self.driver.get(hotel_info['url'])
            
            # Wait for room content using your exact selector
            room_container = self.smart_wait('div.MasterRoom__HotelName[data-selenium="masterroom-title-name"]', timeout=10)
            if not room_container:
                print("  [WARNING] Room container not found, trying alternative...")
                time.sleep(2)
            
            # Click "View All Rooms" button using your exact selector
            try:
                view_all_btn = self.driver.find_element(By.CSS_SELECTOR, 'button[id="property-room-grid-root-tab-2"]')
                if view_all_btn.is_displayed() and view_all_btn.is_enabled():
                    print("  [ACTION] Clicking 'View All Rooms'...")
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", view_all_btn)
                    time.sleep(1)
                    view_all_btn.click()
                    time.sleep(2)
            except Exception as e:
                print(f"  [WARNING] View All Rooms button not found: {e}")
            
            # Scroll to load room content
            self.progressive_scroll(iterations=5)
            
            # Extract room categories using your exact selectors
            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            room_categories = []
            
            # Primary selector: RoomGrid-titleCounterNormal
            room_elements = soup.select('.RoomGrid-titleCounterNormal')
            
            # Secondary selector: Your room class
            if not room_elements:
                room_elements = soup.select('.af0e5-box.af0e5-bg-generic-base-transparent.af0e5-fill-generic-base-subtle')
            
            # Extract and clean room names
            for room_elem in room_elements:
                room_text = room_elem.get_text(strip=True)
                
                # Skip invalid entries
                if (not room_text or len(room_text) < 3 or len(room_text) > 80 or
                    any(skip in room_text.lower() for skip in ['select', 'choose', 'book', 'price', 'available', 'guest'])):
                    continue
                
                # Clean and validate
                room_text = re.sub(r'(Limited time offer|Expires in|SUPER WEDNESDAY|NIGHT OWL).*$', '', room_text, flags=re.IGNORECASE).strip()
                
                if room_text and room_text not in room_categories:
                    room_categories.append(room_text)
            
            # Fallback: Look for room-related keywords
            if not room_categories:
                all_text = soup.get_text()
                potential_rooms = re.findall(r'[A-Z][a-z\s]*(?:Room|Suite|Deluxe|Standard|Premium|Executive|King|Queen|Twin|Double)[A-Za-z\s]*', all_text)
                
                for room in potential_rooms[:5]:  # Limit to 5
                    room = room.strip()
                    if 10 <= len(room) <= 50 and room not in room_categories:
                        room_categories.append(room)
            
            print(f"  [SUCCESS] Found {len(room_categories)} room types: {room_categories}")
            return room_categories
            
        except Exception as e:
            print(f"  [ERROR] Error extracting rooms: {e}")
            return []
    
    def navigate_back_safely(self):
        """Navigate back to search results safely"""
        try:
            self.driver.back()
            time.sleep(random.uniform(2, 4))
            
            # Wait for search results to reload
            self.smart_wait('li[data-selenium="hotel-item"], div[data-selenium="hotel-item"]', timeout=10)
            
        except Exception as e:
            print(f"  [WARNING] Navigation error: {e}")
            # Fallback: refresh the search page
            self.driver.get(self.search_url)
            time.sleep(3)
    
    def scrape_page(self, page_num):
        """Scrape a single page of results"""
        print(f"\n[PAGE] Scraping page {page_num}...")
        
        # Progressive scrolling to load all content
        self.progressive_scroll()
        
        # Parse page content
        soup = BeautifulSoup(self.driver.page_source, "html.parser")
        
        # Find hotel cards
        hotel_cards = soup.select('li[data-selenium="hotel-item"]')
        if not hotel_cards:
            hotel_cards = soup.select('div[data-selenium="hotel-item"]')
        
        print(f"[HOTELS] Found {len(hotel_cards)} hotels on page {page_num}")
        
        page_hotels = []
        
        for i, card in enumerate(hotel_cards):
            try:
                # Extract basic info
                hotel_info = self.extract_basic_hotel_info(card)
                if not hotel_info:
                    continue
                
                print(f"\n[HOTEL] Processing hotel {i+1}/{len(hotel_cards)}: {hotel_info['name']}")
                
                # Extract room categories
                room_categories = self.extract_room_categories(hotel_info)
                
                # Navigate back to search results
                self.navigate_back_safely()
                
                # Create final hotel data
                hotel_data = {
                    "name": hotel_info['name'],
                    "price": hotel_info['price'],
                    "location": hotel_info['location'],
                    "rating": hotel_info['rating'],
                    "room_categories": ", ".join(room_categories) if room_categories else "N/A",
                    "total_room_types": len(room_categories),
                    "url": hotel_info['url']
                }
                
                page_hotels.append(hotel_data)
                print(f"[ADDED] Added: {hotel_info['name']} | {len(room_categories)} room types")
                
                # Respectful delay
                time.sleep(random.uniform(1, 3))
                
            except Exception as e:
                print(f"[ERROR] Error processing hotel {i+1}: {e}")
                continue
        
        return page_hotels
    
    def try_next_page(self):
        """Try to navigate to next page"""
        next_selectors = [
            'button[data-selenium="pagination-next"]',
            'button.pagination2__next',
            'button[aria-label="Next page"]'
        ]
        
        for selector in next_selectors:
            try:
                next_btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                if (next_btn.is_displayed() and next_btn.is_enabled() and 
                    "disabled" not in next_btn.get_attribute("class")):
                    
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", next_btn)
                    time.sleep(1)
                    next_btn.click()
                    time.sleep(random.uniform(4, 6))
                    return True
            except:
                continue
        return False
    
    def run(self):
        """Main scraping execution"""
        print("=" * 60)
        print("STARTING ULTIMATE AGODA SCRAPER WITH ROOM CATEGORIES")
        print("=" * 60)
        
        # Create stealth driver
        self.create_stealth_driver()
        
        try:
            # Navigate to search page
            print(f"[NAVIGATE] Navigating to: {self.search_url}")
            self.driver.get(self.search_url)
            time.sleep(3)
            
            # Close popups
            self.close_popups()
            
            # Wait for initial content
            if not self.smart_wait('li[data-selenium="hotel-item"], div[data-selenium="hotel-item"]', timeout=20):
                print("[ERROR] No hotel listings found!")
                return
            
            page_num = 1
            
            while True:
                # Scrape current page
                page_hotels = self.scrape_page(page_num)
                self.all_hotels.extend(page_hotels)
                
                # Try to go to next page
                if not self.try_next_page():
                    print("[END] No more pages available")
                    break
                
                page_num += 1
                
                # Safety limit
                if page_num > 25:
                    print("[LIMIT] Reached maximum page limit")
                    break
            
            # Save results
            self.save_results()
            
        except Exception as e:
            print(f"[CRITICAL] Critical error: {e}")
            
        finally:
            if self.driver:
                self.driver.quit()
                print("[CLOSED] Browser closed")
    
    def save_results(self):
        """Save scraped results to files"""
        # Remove duplicates
        unique_hotels = []
        seen_names = set()
        
        for hotel in self.all_hotels:
            if hotel['name'] not in seen_names:
                unique_hotels.append(hotel)
                seen_names.add(hotel['name'])
        
        print("\n" + "=" * 60)
        print("SCRAPING COMPLETE!")
        print("=" * 60)
        print(f"[RESULTS] Total unique hotels: {len(unique_hotels)}")
        
        # Save CSV
        with open("agoda_ultimate_results.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["name", "price", "location", "rating", "room_categories", "total_room_types", "url"])
            writer.writeheader()
            writer.writerows(unique_hotels)
        
        # Save JSON
        with open("agoda_ultimate_results.json", "w", encoding="utf-8") as f:
            json.dump(unique_hotels, f, indent=2, ensure_ascii=False)
        
        # Statistics
        total_rooms = sum(hotel["total_room_types"] for hotel in unique_hotels)
        avg_rooms = total_rooms / len(unique_hotels) if unique_hotels else 0
        
        print("\n" + "=" * 60)
        print("FINAL STATISTICS")
        print("=" * 60)
        print(f"[HOTELS] Total hotels scraped: {len(unique_hotels)}")
        print(f"[ROOMS] Total room categories: {total_rooms}")
        print(f"[AVERAGE] Average rooms per hotel: {avg_rooms:.1f}")
        print("\n" + "=" * 60)
        print("FILES SAVED")
        print("=" * 60)
        print("  - agoda_ultimate_results.csv")
        print("  - agoda_ultimate_results.json")
        print("=" * 60)

def main():
    """Main function to run the scraper"""
    # Replace with your actual Agoda search URL
    search_url = "YOUR_AGODA_URL_HERE"
    
    print("Agoda Ultimate Scraper - Room Categories Edition")
    print("Windows Compatible Version")
    print("-" * 50)
    
    scraper = AgodaUltimateScraper(search_url)
    scraper.run()

if __name__ == "__main__":
    main()