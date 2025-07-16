from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as seleniumEC
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.action_chains import ActionChains
import time
import csv
import random
import json
import re

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
    
    # Clean extra spaces and return
    return name.strip()

def extract_from_multiple_elements(card, selectors, data_type=""):
    """Extract data using multiple selectors and return first non-empty result"""
    for selector in selectors:
        try:
            elements = card.select(selector)
            for elem in elements:
                text = elem.get_text(strip=True)
                if text and text != "N/A" and len(text) > 0:
                    # Additional validation for specific data types
                    if data_type == "location":
                        # Look for location indicators
                        location_indicators = ['km', 'mile', 'walk', 'from', 'to', 'near', 'road', 'street', 'area', 'district']
                        if any(indicator in text.lower() for indicator in location_indicators):
                            return text
                    elif data_type == "rating":
                        # Look for rating indicators
                        if (any(char.isdigit() for char in text) and 
                            ('/' in text or 'score' in text.lower() or 'rating' in text.lower() or 
                             'review' in text.lower() or len(text) <= 10)):
                            return text
                    elif data_type == "price":
                        # Look for price indicators
                        if (any(char.isdigit() for char in text) and 
                            any(currency in text for currency in ['₹', '$', '€', '£', ','])):
                            return text
                    else:
                        return text
        except Exception as e:
            continue
    return "N/A"

def scrape():
    url = "YOUR_AGODA_URL_HERE"
    
    # Configure Firefox to be more stealthy
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.set_preference("dom.webdriver.enabled", False)
    options.set_preference('useAutomationExtension', False)
    options.set_preference("general.useragent.override", 
                          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = webdriver.Firefox(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    try:
        driver.get(url)
        
        # Wait for initial page load and handle potential overlays
        time.sleep(5)
        
        # Try to close any popups/overlays with more selectors
        try:
            close_selectors = [
                'button[aria-label="Close"]', '.close-button', '[data-selenium="close-button"]',
                'button[data-testid="close-button"]', '.modal-close', '.popup-close',
                'button[class*="close"]', 'span[class*="close"]', '.cross-button'
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
        
        # Wait for hotel listings to load with more selectors
        WebDriverWait(driver, 25).until(
            seleniumEC.presence_of_all_elements_located((By.CSS_SELECTOR, 
                'li[data-selenium="hotel-item"], div[data-selenium="hotel-item"], .PropertyCard, [data-testid="property-card"], .property-card'))
        )
        
        all_hotels = []
        page_number = 1
        
        while True:
            print(f"Scraping page {page_number}...")
            
            # More aggressive scrolling to load all content
            last_height = driver.execute_script("return document.body.scrollHeight")
            
            # Progressive scrolling with longer waits
            for i in range(15):  # More scroll iterations
                scroll_position = (i + 1) * 0.067  # Smaller increments
                driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight * {scroll_position});")
                time.sleep(random.uniform(2, 3))  # Longer delays
                
                # Check if new content loaded
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height != last_height:
                    last_height = new_height
                    time.sleep(3)
            
            # Final scroll to top and back down
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            
            soup = BeautifulSoup(driver.page_source, "html.parser")
            
            # More comprehensive selectors for hotel cards
            hotel_cards = []
            card_selectors = [
                'li[data-selenium="hotel-item"]',
                'div[data-selenium="hotel-item"]',
                '.PropertyCard',
                '[data-element-name="hotel-item"]',
                'div[data-testid="property-card"]',
                '.property-card',
                '[data-testid="property-item"]',
                '.hotel-item',
                '.search-result-item'
            ]
            
            for selector in card_selectors:
                cards = soup.select(selector)
                if cards:
                    hotel_cards = cards
                    break
            
            print(f"Found {len(hotel_cards)} hotel cards on page {page_number}")
            
            for i, card in enumerate(hotel_cards):
                try:
                    # Extract name with comprehensive selectors
                    name_selectors = [
                        'h3[data-selenium="hotel-name"] a',
                        'h3[data-selenium="hotel-name"]',
                        'a[data-selenium="hotel-name"]',
                        'h2[data-selenium="hotel-name"]',
                        'h1[data-selenium="hotel-name"]',
                        '[data-testid="hotel-name"]',
                        '[data-testid="property-name"]',
                        '.PropertyCard__Name a',
                        '.PropertyCard__Name',
                        '.hotel-name',
                        '.property-name',
                        'h3 a[href*="/hotel/"]',
                        'h2 a[href*="/hotel/"]',
                        'a[href*="/hotel/"]',
                        'h3',
                        'h2',
                        'h1'
                    ]
                    
                    name = extract_from_multiple_elements(card, name_selectors)
                    name = clean_hotel_name(name)
                    
                    # Skip if name is promotional text or empty
                    if (name == "N/A" or is_promotional_text(name) or 
                        len(name.strip()) == 0 or name.strip() == ""):
                        continue
                    
                    # Extract price with comprehensive selectors
                    price_selectors = [
                        'span[data-selenium="display-price"]',
                        '[data-selenium="price-display"]',
                        '[data-testid="price-display"]',
                        '[data-testid="price"]',
                        '.PropertyCard__Price',
                        '.price-display',
                        '.price',
                        '.hotel-price',
                        '.property-price',
                        'span[class*="price"]',
                        'div[class*="price"]',
                        'span[class*="Price"]',
                        'div[class*="Price"]',
                        'span[class*="cost"]',
                        'div[class*="cost"]'
                    ]
                    
                    price = extract_from_multiple_elements(card, price_selectors, "price")
                    
                    # Extract location with comprehensive selectors
                    location_selectors = [
                        '[data-selenium="hotel-location"]',
                        '[data-selenium="location-name"]',
                        '[data-selenium="location"]',
                        '[data-testid="location"]',
                        '[data-testid="hotel-location"]',
                        '[data-testid="distance"]',
                        '.PropertyCard__Location',
                        '.hotel-location',
                        '.property-location',
                        '.location',
                        '.distance',
                        '.location-info',
                        '.hotel-distance',
                        'div[class*="location"]',
                        'span[class*="location"]',
                        'div[class*="Location"]',
                        'span[class*="Location"]',
                        'div[class*="distance"]',
                        'span[class*="distance"]',
                        'div[class*="address"]',
                        'span[class*="address"]',
                        'p[class*="location"]',
                        'p[class*="address"]',
                        # Look for text containing location keywords
                        'div:contains("km")',
                        'span:contains("km")',
                        'div:contains("from")',
                        'span:contains("from")',
                        'div:contains("walk")',
                        'span:contains("walk")'
                    ]
                    
                    location = extract_from_multiple_elements(card, location_selectors, "location")
                    
                    # Extract rating with comprehensive selectors
                    rating_selectors = [
                        'span[data-selenium="hotel-rating"]',
                        '[data-selenium="rating-display"]',
                        '[data-selenium="rating"]',
                        '[data-testid="rating"]',
                        '[data-testid="hotel-rating"]',
                        '[data-testid="review-score"]',
                        '.PropertyCard__Rating',
                        '.hotel-rating',
                        '.property-rating',
                        '.rating',
                        '.review-score',
                        '.score',
                        '.rating-score',
                        'div[class*="rating"]',
                        'span[class*="rating"]',
                        'div[class*="Rating"]',
                        'span[class*="Rating"]',
                        'div[class*="score"]',
                        'span[class*="score"]',
                        'div[class*="Score"]',
                        'span[class*="Score"]',
                        'div[class*="review"]',
                        'span[class*="review"]',
                        'div[class*="Review"]',
                        'span[class*="Review"]',
                        # Look for text containing rating keywords
                        'div:contains("/")',
                        'span:contains("/")',
                        'div:contains("score")',
                        'span:contains("score")',
                        'div:contains("rating")',
                        'span:contains("rating")'
                    ]
                    
                    rating = extract_from_multiple_elements(card, rating_selectors, "rating")
                    
                    # Additional validation and cleaning
                    if price != "N/A":
                        price = re.sub(r'[^\d,₹$€£.]', '', price)
                    
                    if location != "N/A":
                        location = location[:100]  # Limit length
                    
                    if rating != "N/A":
                        rating = rating[:20]  # Limit length
                    
                    # Create hotel data
                    hotel_data = {
                        "name": name,
                        "price": price,
                        "location": location,
                        "rating": rating
                    }
                    
                    all_hotels.append(hotel_data)
                    print(f"Added hotel: {name} | Price: {price} | Location: {location} | Rating: {rating}")
                    
                except Exception as e:
                    print(f"Error parsing hotel card {i+1}: {e}")
                    continue
            
            # Enhanced pagination handling
            next_clicked = False
            next_selectors = [
                'button[data-selenium="pagination-next"]',
                'a[data-selenium="pagination-next"]',
                'button[data-testid="pagination-next"]',
                'a[data-testid="pagination-next"]',
                'button.pagination2__next',
                'a.pagination2__next',
                'button[aria-label="Next page"]',
                'a[aria-label="Next page"]',
                'button[aria-label*="Next"]',
                'a[aria-label*="Next"]',
                '.pagination__next',
                '.pagination-next',
                'button[class*="next"]',
                'a[class*="next"]',
                'button[class*="Next"]',
                'a[class*="Next"]',
                'button:contains("Next")',
                'a:contains("Next")',
                'button:contains("→")',
                'a:contains("→")'
            ]
            
            for selector in next_selectors:
                try:
                    next_buttons = driver.find_elements(By.CSS_SELECTOR, selector)
                    for next_button in next_buttons:
                        if (next_button.is_displayed() and 
                            next_button.is_enabled() and 
                            "disabled" not in next_button.get_attribute("class")):
                            
                            # Scroll to button
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
                            time.sleep(2)
                            
                            # Try multiple click methods
                            try:
                                next_button.click()
                            except:
                                try:
                                    actions = ActionChains(driver)
                                    actions.move_to_element(next_button).click().perform()
                                except:
                                    driver.execute_script("arguments[0].click();", next_button)
                            
                            print(f"Clicked next button using selector: {selector}")
                            next_clicked = True
                            time.sleep(random.uniform(5, 8))  # Longer wait for page load
                            break
                            
                except Exception as e:
                    print(f"Selector {selector} failed: {e}")
                    continue
                
                if next_clicked:
                    break
            
            if not next_clicked:
                print("No more pages or unable to find next button")
                break
            
            page_number += 1
            
            # Safety check
            if page_number > 100:  # Increased limit
                print("Maximum pages reached")
                break
    
    finally:
        # Remove duplicates and clean data
        unique_hotels = []
        seen_names = set()
        
        for hotel in all_hotels:
            name = hotel["name"]
            if name not in seen_names and name != "N/A" and not is_promotional_text(name):
                unique_hotels.append(hotel)
                seen_names.add(name)
        
        print(f"Total unique hotels found: {len(unique_hotels)}")
        
        # Save to CSV
        with open("agoda_hotels_improved_v2.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["name", "price", "location", "rating"])
            writer.writeheader()
            for hotel in unique_hotels:
                writer.writerow(hotel)
        
        # Also save as JSON for easier inspection
        with open("agoda_hotels_improved_v2.json", "w", encoding="utf-8") as f:
            json.dump(unique_hotels, f, indent=2, ensure_ascii=False)
        
        print("\nFiles saved:")
        print("- agoda_hotels_improved_v2.csv")
        print("- agoda_hotels_improved_v2.json")
        
        driver.quit()

if __name__ == "__main__":
    scrape()