from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as seleniumEC
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
import time
import re

def detailed_inspection():
    """
    Detailed inspection script to find exact selectors for Agoda location and rating data
    """
    url = "YOUR_AGODA_URL_HERE"
    
    # Configure Firefox
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.set_preference("dom.webdriver.enabled", False)
    options.set_preference('useAutomationExtension', False)
    options.set_preference("general.useragent.override", 
                          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
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
            time.sleep(3)
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        # Find hotel cards
        hotel_cards = (
            soup.select('li[data-selenium="hotel-item"]') or
            soup.select('div[data-selenium="hotel-item"]') or
            soup.select('.PropertyCard')
        )
        
        print(f"Found {len(hotel_cards)} hotel cards")
        print("="*80)
        
        # Analyze first 3 cards in detail
        for i, card in enumerate(hotel_cards[:3]):
            print(f"\nDETAILED ANALYSIS OF HOTEL CARD {i+1}")
            print("="*80)
            
            # Save the card HTML for manual inspection
            with open(f"hotel_card_{i+1}_full.html", "w", encoding="utf-8") as f:
                f.write(card.prettify())
            
            # Find hotel name first
            name_elem = card.find("a")
            hotel_name = name_elem.get_text(strip=True) if name_elem else "Unknown Hotel"
            print(f"Hotel Name: {hotel_name}")
            
            print(f"\nALL TEXT CONTENT IN THIS CARD:")
            print("-" * 50)
            
            # Get all text elements with their parent info
            all_text_elements = []
            for elem in card.find_all(text=True):
                text = elem.strip()
                if text and len(text) > 0:
                    parent = elem.parent
                    all_text_elements.append({
                        'text': text,
                        'parent_tag': parent.name,
                        'parent_classes': parent.get('class', []),
                        'parent_id': parent.get('id', ''),
                        'data_attributes': {k: v for k, v in parent.attrs.items() if k.startswith('data-')}
                    })
            
            # Display all text elements
            for idx, elem_info in enumerate(all_text_elements):
                print(f"{idx+1:2d}. Text: '{elem_info['text'][:60]}...' ")
                print(f"    Tag: {elem_info['parent_tag']}")
                print(f"    Classes: {elem_info['parent_classes']}")
                print(f"    ID: {elem_info['parent_id']}")
                print(f"    Data attrs: {elem_info['data_attributes']}")
                print()
            
            # Look for potential location data
            print(f"\nPOTENTIAL LOCATION DATA:")
            print("-" * 50)
            location_keywords = ['km', 'mile', 'walk', 'from', 'to', 'near', 'road', 'street', 'area', 'district', 'center', 'mall', 'station']
            
            for idx, elem_info in enumerate(all_text_elements):
                text_lower = elem_info['text'].lower()
                if any(keyword in text_lower for keyword in location_keywords):
                    print(f"LOCATION CANDIDATE {idx+1}: '{elem_info['text']}'")
                    print(f"  CSS Selector: {elem_info['parent_tag']}")
                    if elem_info['parent_classes']:
                        print(f"  Class Selector: .{'.'.join(elem_info['parent_classes'])}")
                    if elem_info['data_attributes']:
                        print(f"  Data Selector: {elem_info['data_attributes']}")
                    print()
            
            # Look for potential rating data
            print(f"\nPOTENTIAL RATING DATA:")
            print("-" * 50)
            rating_keywords = ['score', 'rating', 'review', 'star', '/10', '/5', 'excellent', 'good', 'average', 'wonderful', 'superb']
            
            for idx, elem_info in enumerate(all_text_elements):
                text_lower = elem_info['text'].lower()
                has_rating_keyword = any(keyword in text_lower for keyword in rating_keywords)
                has_numbers = any(char.isdigit() for char in elem_info['text'])
                has_slash = '/' in elem_info['text']
                
                if has_rating_keyword or (has_numbers and has_slash) or (has_numbers and len(elem_info['text']) <= 10):
                    print(f"RATING CANDIDATE {idx+1}: '{elem_info['text']}'")
                    print(f"  CSS Selector: {elem_info['parent_tag']}")
                    if elem_info['parent_classes']:
                        print(f"  Class Selector: .{'.'.join(elem_info['parent_classes'])}")
                    if elem_info['data_attributes']:
                        print(f"  Data Selector: {elem_info['data_attributes']}")
                    print()
            
            # Look for price data (for comparison)
            print(f"\nPOTENTIAL PRICE DATA:")
            print("-" * 50)
            
            for idx, elem_info in enumerate(all_text_elements):
                text = elem_info['text']
                has_currency = any(currency in text for currency in ['₹', '$', '€', '£'])
                has_numbers = any(char.isdigit() for char in text)
                has_comma = ',' in text
                
                if has_currency or (has_numbers and has_comma):
                    print(f"PRICE CANDIDATE {idx+1}: '{elem_info['text']}'")
                    print(f"  CSS Selector: {elem_info['parent_tag']}")
                    if elem_info['parent_classes']:
                        print(f"  Class Selector: .{'.'.join(elem_info['parent_classes'])}")
                    if elem_info['data_attributes']:
                        print(f"  Data Selector: {elem_info['data_attributes']}")
                    print()
            
            print("\n" + "="*80)
        
        # Save the full page source
        with open("full_agoda_page.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        
        print(f"\nFILES CREATED:")
        print("- hotel_card_1_full.html")
        print("- hotel_card_2_full.html") 
        print("- hotel_card_3_full.html")
        print("- full_agoda_page.html")
        
        print(f"\nNEXT STEPS:")
        print("1. Look at the 'LOCATION CANDIDATE' and 'RATING CANDIDATE' sections above")
        print("2. Find the selectors that consistently appear for location and rating")
        print("3. Open the saved HTML files in a browser to visually inspect")
        print("4. Use browser DevTools to right-click on location/rating text and 'Inspect'")
        print("5. Copy the exact CSS selectors from the DevTools")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    detailed_inspection()