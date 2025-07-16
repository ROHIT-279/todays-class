from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as seleniumEC
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
import time
import json

def debug_agoda_structure():
    """
    Debug script to inspect Agoda HTML structure and find correct selectors
    """
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
        time.sleep(5)
        
        # Wait for hotel listings to load
        WebDriverWait(driver, 20).until(
            seleniumEC.presence_of_all_elements_located((By.CSS_SELECTOR, 'li[data-selenium="hotel-item"], div[data-selenium="hotel-item"], .PropertyCard'))
        )
        
        # Scroll to load some content
        for i in range(3):
            driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight * {(i+1) * 0.3});")
            time.sleep(2)
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        # Find hotel cards
        hotel_cards = (
            soup.select('li[data-selenium="hotel-item"]') or
            soup.select('div[data-selenium="hotel-item"]') or
            soup.select('.PropertyCard') or
            soup.select('[data-element-name="hotel-item"]')
        )
        
        print(f"Found {len(hotel_cards)} hotel cards")
        
        # Analyze first few cards to understand structure
        for i, card in enumerate(hotel_cards[:3]):  # Only analyze first 3 cards
            print(f"\n{'='*60}")
            print(f"ANALYZING HOTEL CARD {i+1}")
            print(f"{'='*60}")
            
            # Save HTML structure for inspection
            with open(f"hotel_card_{i+1}_structure.html", "w", encoding="utf-8") as f:
                f.write(str(card.prettify()))
            
            print(f"HTML structure saved to hotel_card_{i+1}_structure.html")
            
            # Look for all possible text elements that could be location or rating
            print("\nAll text elements with their classes:")
            for elem in card.find_all(['span', 'div', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                text = elem.get_text(strip=True)
                if text and len(text) > 0:
                    classes = elem.get('class', [])
                    data_attrs = {k: v for k, v in elem.attrs.items() if k.startswith('data-')}
                    print(f"  Text: '{text[:50]}...' | Tag: {elem.name} | Classes: {classes} | Data: {data_attrs}")
            
            # Look for specific patterns
            print("\nLooking for location patterns:")
            location_patterns = ['km', 'mile', 'walk', 'distance', 'location', 'address', 'area', 'district']
            for elem in card.find_all(text=True):
                text = elem.strip().lower()
                if any(pattern in text for pattern in location_patterns):
                    parent = elem.parent
                    print(f"  Found location-like text: '{elem.strip()[:50]}...' | Parent: {parent.name} | Classes: {parent.get('class', [])}")
            
            print("\nLooking for rating patterns:")
            rating_patterns = ['score', 'rating', 'review', 'star', '/10', '/5', 'excellent', 'good', 'average']
            for elem in card.find_all(text=True):
                text = elem.strip().lower()
                if any(pattern in text for pattern in rating_patterns) or any(char.isdigit() for char in text):
                    parent = elem.parent
                    print(f"  Found rating-like text: '{elem.strip()[:50]}...' | Parent: {parent.name} | Classes: {parent.get('class', [])}")
        
        # Look for pagination buttons
        print(f"\n{'='*60}")
        print("ANALYZING PAGINATION BUTTONS")
        print(f"{'='*60}")
        
        pagination_elements = soup.find_all(['button', 'a'], string=lambda text: text and ('next' in text.lower() or 'page' in text.lower()))
        for elem in pagination_elements:
            print(f"Pagination element: {elem.name} | Text: '{elem.get_text(strip=True)}' | Classes: {elem.get('class', [])} | Data: {elem.get('data-selenium', 'N/A')}")
        
        # Also look for elements with pagination-related classes
        pagination_classes = soup.find_all(class_=lambda x: x and any(keyword in ' '.join(x).lower() for keyword in ['next', 'pagination', 'page']))
        for elem in pagination_classes:
            print(f"Pagination class: {elem.name} | Classes: {elem.get('class', [])} | Text: '{elem.get_text(strip=True)[:30]}...'")
        
        # Save full page source for manual inspection
        with open("full_page_source.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        
        print(f"\nFull page source saved to full_page_source.html")
        print("You can open this file in a browser to inspect the structure manually")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    debug_agoda_structure()