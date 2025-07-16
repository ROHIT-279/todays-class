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

def scrape():
    url = "YOUR_AGODA_URL_HERE"
    
    # Configure Firefox to be more stealthy
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.set_preference("dom.webdriver.enabled", False)
    options.set_preference('useAutomationExtension', False)
    options.set_preference("general.useragent.override", 
                          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    driver = webdriver.Firefox(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    try:
        driver.get(url)
        
        # Wait for initial page load and handle potential overlays
        time.sleep(3)
        
        # Try to close any popups/overlays
        try:
            close_buttons = driver.find_elements(By.CSS_SELECTOR, 'button[aria-label="Close"], .close-button, [data-selenium="close-button"]')
            for button in close_buttons:
                try:
                    button.click()
                    time.sleep(1)
                except:
                    pass
        except:
            pass
        
        # Wait for hotel listings to load
        WebDriverWait(driver, 20).until(
            seleniumEC.presence_of_all_elements_located((By.CSS_SELECTOR, 'li[data-selenium="hotel-item"], div[data-selenium="hotel-item"], .PropertyCard'))
        )
        
        all_hotels = []
        page_number = 1
        
        while True:
            print(f"Scraping page {page_number}...")
            
            # Scroll gradually to load all content
            last_height = driver.execute_script("return document.body.scrollHeight")
            
            # Progressive scrolling to trigger lazy loading
            for i in range(10):  # Increased scroll iterations
                scroll_position = (i + 1) * 0.1
                driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight * {scroll_position});")
                time.sleep(random.uniform(1.5, 2.5))  # Random delays to look more human
                
                # Check if new content loaded
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height != last_height:
                    last_height = new_height
                    time.sleep(2)
            
            # Wait for content to settle
            time.sleep(3)
            
            soup = BeautifulSoup(driver.page_source, "html.parser")
            
            # Multiple selectors for hotel cards (Agoda changes these frequently)
            hotel_cards = (
                soup.select('li[data-selenium="hotel-item"]') or
                soup.select('div[data-selenium="hotel-item"]') or
                soup.select('.PropertyCard') or
                soup.select('[data-element-name="hotel-item"]') or
                soup.select('div[data-testid="property-card"]')
            )
            
            print(f"Found {len(hotel_cards)} hotel cards on page {page_number}")
            
            for card in hotel_cards:
                try:
                    # Extract name with multiple fallbacks
                    name = "N/A"
                    name_selectors = [
                        'h3[data-selenium="hotel-name"] a',
                        'h3[data-selenium="hotel-name"]',
                        'a[data-selenium="hotel-name"]',
                        '.PropertyCard__Name a',
                        '.PropertyCard__Name',
                        'h3 a',
                        'h2 a',
                        'a[href*="/hotel/"]'
                    ]
                    
                    for selector in name_selectors:
                        name_elem = card.select_one(selector)
                        if name_elem:
                            name = name_elem.get_text(strip=True)
                            break
                    
                    # Extract price with multiple fallbacks
                    price = "N/A"
                    price_selectors = [
                        'span[data-selenium="display-price"]',
                        '.PropertyCard__Price',
                        '[data-selenium="price-display"]',
                        '.Price',
                        'span[data-testid="price-display"]',
                        '.property-card-price',
                        'span[class*="price"]',
                        'div[class*="price"]'
                    ]
                    
                    for selector in price_selectors:
                        price_elem = card.select_one(selector)
                        if price_elem:
                            price = price_elem.get_text(strip=True)
                            break
                    
                    # Extract location with multiple fallbacks
                    location = "N/A"
                    location_selectors = [
                        '[data-selenium="hotel-location"]',
                        '.PropertyCard__Location',
                        '[data-selenium="location-name"]',
                        '.hotel-location',
                        'div[class*="location"]',
                        'span[class*="location"]',
                        'div[class*="address"]',
                        'p[class*="location"]'
                    ]
                    
                    for selector in location_selectors:
                        location_elem = card.select_one(selector)
                        if location_elem:
                            location = location_elem.get_text(strip=True)
                            break
                    
                    # Extract rating with multiple fallbacks
                    rating = "N/A"
                    rating_selectors = [
                        'span[data-selenium="hotel-rating"]',
                        '.PropertyCard__Rating',
                        '[data-selenium="rating-display"]',
                        '.review-score',
                        'div[class*="rating"]',
                        'span[class*="rating"]',
                        'div[class*="score"]',
                        'span[class*="score"]'
                    ]
                    
                    for selector in rating_selectors:
                        rating_elem = card.select_one(selector)
                        if rating_elem:
                            rating = rating_elem.get_text(strip=True)
                            break
                    
                    # Only add if we have at least a name
                    if name != "N/A":
                        hotel_data = {
                            "name": name,
                            "price": price,
                            "location": location,
                            "rating": rating
                        }
                        all_hotels.append(hotel_data)
                        print(f"Added hotel: {name}")
                    
                except Exception as e:
                    print(f"Error parsing hotel card: {e}")
                    continue
            
            # Try to find and click next page button with multiple selectors
            next_clicked = False
            next_selectors = [
                'button[data-selenium="pagination-next"]',
                'button.pagination2__next',
                'button[aria-label="Next page"]',
                'a[data-selenium="pagination-next"]',
                '.pagination__next',
                'button[class*="next"]',
                'a[class*="next"]'
            ]
            
            for selector in next_selectors:
                try:
                    next_button = driver.find_element(By.CSS_SELECTOR, selector)
                    
                    # Check if button is enabled
                    if ("disabled" not in next_button.get_attribute("class") and 
                        next_button.is_enabled() and 
                        next_button.is_displayed()):
                        
                        # Scroll to button and click
                        driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                        time.sleep(2)
                        
                        # Try clicking with ActionChains for better reliability
                        actions = ActionChains(driver)
                        actions.move_to_element(next_button).click().perform()
                        
                        print(f"Clicked next button using selector: {selector}")
                        next_clicked = True
                        time.sleep(random.uniform(4, 6))  # Wait for page load
                        break
                        
                except Exception as e:
                    print(f"Selector {selector} failed: {e}")
                    continue
            
            if not next_clicked:
                print("No more pages or unable to find next button")
                break
            
            page_number += 1
            
            # Safety check to prevent infinite loops
            if page_number > 50:  # Adjust as needed
                print("Maximum pages reached")
                break
    
    finally:
        # Remove duplicates based on hotel name
        unique_hotels = []
        seen_names = set()
        
        for hotel in all_hotels:
            if hotel["name"] not in seen_names:
                unique_hotels.append(hotel)
                seen_names.add(hotel["name"])
        
        print(f"Total unique hotels found: {len(unique_hotels)}")
        
        # Save to CSV
        with open("agoda_hotels_improved.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["name", "price", "location", "rating"])
            writer.writeheader()
            for hotel in unique_hotels:
                writer.writerow(hotel)
        
        # Also save as JSON for easier inspection
        with open("agoda_hotels_improved.json", "w", encoding="utf-8") as f:
            json.dump(unique_hotels, f, indent=2, ensure_ascii=False)
        
        driver.quit()

if __name__ == "__main__":
    scrape()