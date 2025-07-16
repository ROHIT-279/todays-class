from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as seleniumEC
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import csv
import random
import json
import re
from urllib.parse import urljoin

def is_promotional_text(text):
    """Filter out promotional/offer text from hotel names"""
    promotional_keywords = [
        'limited time offer', 'expires in', 'super wednesday', 'night owl', 
        'monsoon', 'book early', 'flash sale', 'last minute', 'hot deal'
    ]
    return any(keyword in text.lower() for keyword in promotional_keywords)

def clean_hotel_name(name):
    """Clean hotel name by removing promotional text and extra spaces"""
    if not name or name == "N/A":
        return "N/A"
    
    # Remove promotional text patterns
    name = re.sub(r'Limited time offer.*?$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'Expires in.*?$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'SUPER WEDNESDAY.*?$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'NIGHT OWL.*?$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'MONSOON.*?$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'BOOK EARLY.*?$', '', name, flags=re.IGNORECASE)
    
    return name.strip()

def extract_from_multiple_elements(card, selectors, data_type=""):
    """Extract data using multiple selectors and return first non-empty result"""
    for selector in selectors:
        try:
            elements = card.select(selector)
            for elem in elements:
                text = elem.get_text(strip=True)
                if text and text != "N/A" and len(text) > 0:
                    if data_type == "location":
                        location_indicators = ['km', 'mile', 'walk', 'from', 'to', 'near', 'road', 'street', 'area', 'district']
                        if any(indicator in text.lower() for indicator in location_indicators):
                            return text
                    elif data_type == "rating":
                        if (any(char.isdigit() for char in text) and 
                            ('/' in text or 'score' in text.lower() or 'rating' in text.lower() or 
                             'review' in text.lower() or len(text) <= 10)):
                            return text
                    elif data_type == "price":
                        if (any(char.isdigit() for char in text) and 
                            any(currency in text for currency in ['₹', '$', '€', '£', ','])):
                            return text
                    else:
                        return text
        except Exception as e:
            continue
    return "N/A"

def extract_room_categories(driver, hotel_url, base_url):
    """Extract room categories from individual hotel page"""
    try:
        print(f"  → Visiting hotel page: {hotel_url}")
        driver.get(hotel_url)
        
        # Wait for room content to load
        try:
            WebDriverWait(driver, 15).until(
                seleniumEC.presence_of_element_located((By.CSS_SELECTOR, 
                    'div[class="MasterRoom__HotelName"], div[data-selenium="masterroom-title-name"], .RoomGrid-titleCounterNormal'))
            )
        except TimeoutException:
            print("  ⚠️  Room content not found, trying alternative selectors...")
            time.sleep(3)
        
        # Try to click "View All Rooms" button if it exists
        try:
            view_all_buttons = driver.find_elements(By.CSS_SELECTOR, 
                'button[id="property-room-grid-root-tab-2"], button[class*="af0e5-box"][class*="af0e5-text-product-primary"]')
            
            for button in view_all_buttons:
                if button.is_displayed() and button.is_enabled():
                    print("  📋 Found 'View All Rooms' button, clicking...")
                    driver.execute_script("arguments[0].scrollIntoView(true);", button)
                    time.sleep(2)
                    button.click()
                    time.sleep(3)
                    break
        except Exception as e:
            print(f"  ⚠️  No 'View All Rooms' button found: {e}")
        
        # Scroll to load all room content
        for i in range(3):
            driver.execute_script("window.scrollBy(0, window.innerHeight);")
            time.sleep(1)
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        # Extract room categories with multiple selectors
        room_categories = []
        
        # Try different selectors for room containers
        room_selectors = [
            'div[class*="MasterRoom__HotelName"]',
            'div[data-selenium="masterroom-title-name"]',
            'div[class*="RoomGrid-titleCounterNormal"]',
            'div[class*="af0e5-box af0e5-bg-generic-base-transparent"]',
            'div[class*="room-card"]',
            'div[class*="room-item"]',
            'div[class*="room-type"]',
            'div[class*="room-container"]'
        ]
        
        room_elements = []
        for selector in room_selectors:
            elements = soup.select(selector)
            if elements:
                room_elements.extend(elements)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_rooms = []
        for room in room_elements:
            room_text = room.get_text(strip=True)
            if room_text and room_text not in seen:
                seen.add(room_text)
                unique_rooms.append(room)
        
        # Extract room names/categories
        for room in unique_rooms:
            room_text = room.get_text(strip=True)
            
            # Skip if it's too short or contains promotional text
            if (len(room_text) < 3 or len(room_text) > 100 or 
                is_promotional_text(room_text) or
                any(skip_word in room_text.lower() for skip_word in 
                    ['select', 'choose', 'book', 'available', 'price', 'currency', 'guest', 'night'])):
                continue
            
            # Clean and validate room category
            room_category = clean_hotel_name(room_text)
            if room_category != "N/A" and room_category not in room_categories:
                room_categories.append(room_category)
        
        # If no room categories found, try alternative extraction
        if not room_categories:
            # Look for any text that might be room names
            all_text_elements = soup.find_all(text=True)
            potential_rooms = []
            
            for text in all_text_elements:
                text = text.strip()
                if (text and 10 <= len(text) <= 50 and 
                    any(room_word in text.lower() for room_word in 
                        ['room', 'suite', 'deluxe', 'standard', 'premium', 'executive', 'junior', 'king', 'queen', 'twin', 'double'])):
                    potential_rooms.append(text)
            
            # Remove duplicates and clean
            for room in list(set(potential_rooms))[:5]:  # Limit to 5 rooms
                clean_room = clean_hotel_name(room)
                if clean_room != "N/A" and not is_promotional_text(clean_room):
                    room_categories.append(clean_room)
        
        print(f"  🏨 Found {len(room_categories)} room categories: {room_categories}")
        return room_categories
        
    except Exception as e:
        print(f"  ❌ Error extracting room categories: {e}")
        return []

def create_optimized_driver():
    """Create optimized Firefox driver with incognito mode and anti-detection"""
    options = Options()
    
    # INCOGNITO MODE - Your excellent suggestion!
    options.add_argument("--private-window")
    options.add_argument("--private")
    
    # Enhanced anti-detection
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    
    # Set preferences for stealth
    options.set_preference("dom.webdriver.enabled", False)
    options.set_preference('useAutomationExtension', False)
    options.set_preference("general.useragent.override", 
                          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    
    # Performance optimizations
    options.set_preference("network.http.pipelining", True)
    options.set_preference("network.http.proxy.pipelining", True)
    options.set_preference("network.http.pipelining.maxrequests", 8)
    options.set_preference("content.notify.interval", 500000)
    options.set_preference("content.notify.ontimer", True)
    options.set_preference("content.switch.threshold", 250000)
    
    # Disable images for faster loading (optional)
    options.set_preference("permissions.default.image", 2)
    
    driver = webdriver.Firefox(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver

def scrape_with_room_categories():
    """Main scraping function with room category extraction"""
    url = "YOUR_AGODA_URL_HERE"
    
    driver = create_optimized_driver()
    
    try:
        print("🚀 Starting Agoda scraper with room categories...")
        print("🕵️  Using incognito mode for enhanced privacy")
        
        driver.get(url)
        base_url = "https://www.agoda.com"
        
        # Wait for initial page load
        time.sleep(5)
        
        # Close popups
        try:
            close_selectors = [
                'button[aria-label="Close"]', '.close-button', '[data-selenium="close-button"]',
                'button[data-testid="close-button"]', '.modal-close', '.popup-close'
            ]
            
            for selector in close_selectors:
                try:
                    buttons = driver.find_elements(By.CSS_SELECTOR, selector)
                    for button in buttons:
                        if button.is_displayed():
                            button.click()
                            time.sleep(1)
                except:
                    continue
        except:
            pass
        
        # Wait for hotel listings
        WebDriverWait(driver, 25).until(
            seleniumEC.presence_of_all_elements_located((By.CSS_SELECTOR, 
                'li[data-selenium="hotel-item"], div[data-selenium="hotel-item"], .PropertyCard'))
        )
        
        all_hotels = []
        page_number = 1
        
        while True:
            print(f"\n📄 Scraping page {page_number}...")
            
            # Progressive scrolling
            last_height = driver.execute_script("return document.body.scrollHeight")
            
            for i in range(10):
                scroll_position = (i + 1) * 0.1
                driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight * {scroll_position});")
                time.sleep(random.uniform(2, 3))
                
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height != last_height:
                    last_height = new_height
                    time.sleep(2)
            
            soup = BeautifulSoup(driver.page_source, "html.parser")
            
            # Find hotel cards
            hotel_cards = []
            card_selectors = [
                'li[data-selenium="hotel-item"]',
                'div[data-selenium="hotel-item"]',
                '.PropertyCard'
            ]
            
            for selector in card_selectors:
                cards = soup.select(selector)
                if cards:
                    hotel_cards = cards
                    break
            
            print(f"🏨 Found {len(hotel_cards)} hotels on page {page_number}")
            
            for i, card in enumerate(hotel_cards):
                try:
                    # Extract basic hotel info
                    name_selectors = [
                        'a[class*="TextLink__TextLinkStyled-sc-upxc4y-1"]',
                        'h3[data-selenium="hotel-name"] a',
                        'a[data-selenium="hotel-name"]',
                        'h3 a[href*="/hotel/"]',
                        'a[href*="/hotel/"]'
                    ]
                    
                    name = "N/A"
                    hotel_link = None
                    
                    for selector in name_selectors:
                        name_elem = card.select_one(selector)
                        if name_elem:
                            name = name_elem.get_text(strip=True)
                            hotel_link = name_elem.get('href')
                            break
                    
                    name = clean_hotel_name(name)
                    
                    # Skip if name is promotional or empty
                    if (name == "N/A" or is_promotional_text(name) or 
                        len(name.strip()) == 0 or not hotel_link):
                        continue
                    
                    # Extract other basic info
                    price_selectors = [
                        'span[data-selenium="display-price"]',
                        '[data-selenium="price-display"]',
                        'span[class*="price"]'
                    ]
                    price = extract_from_multiple_elements(card, price_selectors, "price")
                    
                    location_selectors = [
                        '[data-selenium="hotel-location"]',
                        'div[class*="location"]',
                        'span[class*="location"]'
                    ]
                    location = extract_from_multiple_elements(card, location_selectors, "location")
                    
                    rating_selectors = [
                        'span[data-selenium="hotel-rating"]',
                        'div[class*="rating"]',
                        'span[class*="rating"]'
                    ]
                    rating = extract_from_multiple_elements(card, rating_selectors, "rating")
                    
                    # Construct full hotel URL
                    if hotel_link.startswith('/'):
                        hotel_url = urljoin(base_url, hotel_link)
                    else:
                        hotel_url = hotel_link
                    
                    print(f"\n🏨 Processing hotel {i+1}: {name}")
                    
                    # Extract room categories (the big enhancement!)
                    room_categories = extract_room_categories(driver, hotel_url, base_url)
                    
                    # Navigate back to search results
                    driver.back()
                    time.sleep(random.uniform(3, 5))
                    
                    # Wait for search results to reload
                    try:
                        WebDriverWait(driver, 10).until(
                            seleniumEC.presence_of_element_located((By.CSS_SELECTOR, 
                                'li[data-selenium="hotel-item"], div[data-selenium="hotel-item"]'))
                        )
                    except TimeoutException:
                        print("  ⚠️  Search results not loading, refreshing...")
                        driver.refresh()
                        time.sleep(5)
                    
                    # Create hotel data with room categories
                    hotel_data = {
                        "name": name,
                        "price": price,
                        "location": location,
                        "rating": rating,
                        "room_categories": ", ".join(room_categories) if room_categories else "N/A",
                        "total_room_types": len(room_categories)
                    }
                    
                    all_hotels.append(hotel_data)
                    print(f"✅ Added: {name} | Rooms: {len(room_categories)} | Categories: {', '.join(room_categories[:3])}...")
                    
                    # Small delay to be respectful
                    time.sleep(random.uniform(2, 4))
                    
                except Exception as e:
                    print(f"❌ Error processing hotel {i+1}: {e}")
                    continue
            
            # Try to go to next page
            next_clicked = False
            next_selectors = [
                'button[data-selenium="pagination-next"]',
                'button.pagination2__next',
                'button[aria-label="Next page"]'
            ]
            
            for selector in next_selectors:
                try:
                    next_button = driver.find_element(By.CSS_SELECTOR, selector)
                    if (next_button.is_displayed() and next_button.is_enabled() and 
                        "disabled" not in next_button.get_attribute("class")):
                        
                        driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                        time.sleep(2)
                        next_button.click()
                        print(f"➡️  Navigated to page {page_number + 1}")
                        next_clicked = True
                        time.sleep(random.uniform(5, 8))
                        break
                except:
                    continue
            
            if not next_clicked:
                print("🔚 No more pages found")
                break
            
            page_number += 1
            
            # Safety limit
            if page_number > 20:
                print("📊 Reached maximum page limit")
                break
    
    finally:
        # Remove duplicates and save results
        unique_hotels = []
        seen_names = set()
        
        for hotel in all_hotels:
            name = hotel["name"]
            if name not in seen_names and name != "N/A":
                unique_hotels.append(hotel)
                seen_names.add(name)
        
        print(f"\n📊 SCRAPING COMPLETE!")
        print(f"Total unique hotels found: {len(unique_hotels)}")
        
        # Save enhanced CSV with room categories
        with open("agoda_hotels_with_rooms.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["name", "price", "location", "rating", "room_categories", "total_room_types"])
            writer.writeheader()
            for hotel in unique_hotels:
                writer.writerow(hotel)
        
        # Save detailed JSON
        with open("agoda_hotels_with_rooms.json", "w", encoding="utf-8") as f:
            json.dump(unique_hotels, f, indent=2, ensure_ascii=False)
        
        print("\n📁 Files saved:")
        print("- agoda_hotels_with_rooms.csv")
        print("- agoda_hotels_with_rooms.json")
        
        # Statistics
        total_rooms = sum(hotel["total_room_types"] for hotel in unique_hotels)
        print(f"\n📈 Statistics:")
        print(f"- Total hotels: {len(unique_hotels)}")
        print(f"- Total room categories extracted: {total_rooms}")
        print(f"- Average room types per hotel: {total_rooms/len(unique_hotels):.1f}")
        
        driver.quit()

if __name__ == "__main__":
    scrape_with_room_categories()