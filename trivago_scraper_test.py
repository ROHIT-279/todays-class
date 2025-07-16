#!/usr/bin/env python3
"""
Test version of Trivago scraper - limited to 2 pages and faster execution
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException, 
    ElementClickInterceptedException,
    StaleElementReferenceException,
    WebDriverException
)
import time
import pandas as pd
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TrivagoScraperTest:
    def __init__(self):
        self.driver = None
        self.hotels_data = []
        self.current_page = 1
        self.max_pages = 2  # Limited for testing
        
    def setup_driver(self):
        """Setup Chrome driver"""
        options = Options()
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        # options.add_argument("--headless")  # Uncomment for headless mode
        
        try:
            self.driver = webdriver.Chrome(options=options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            logger.info("Chrome driver initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Chrome driver: {e}")
            return False
    
    def safe_click(self, element, element_name="element"):
        """Try multiple click methods"""
        click_methods = [
            ("regular", lambda: element.click()),
            ("javascript", lambda: self.driver.execute_script("arguments[0].click();", element)),
            ("action_chains", lambda: ActionChains(self.driver).move_to_element(element).click().perform())
        ]
        
        for method_name, click_method in click_methods:
            try:
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                time.sleep(0.5)  # Reduced delay for testing
                click_method()
                logger.info(f"Successfully clicked {element_name} using {method_name}")
                return True
            except Exception as e:
                logger.debug(f"{method_name} click failed for {element_name}: {e}")
                continue
        
        logger.error(f"All click methods failed for {element_name}")
        return False
    
    def extract_hotel_info(self, hotel_span, hotel_index):
        """Extract hotel information - simplified for testing"""
        hotel_data = {
            'hotel_index': hotel_index,
            'hotel_name': '',
            'price': '',
            'rating': '',
            'location': '',
            'amenities': [],
            'page_number': self.current_page,
            'extraction_time': datetime.now().isoformat()
        }
        
        try:
            logger.info(f"Extracting data for hotel #{hotel_index}")
            
            # Click on the hotel span
            if not self.safe_click(hotel_span, f"hotel span #{hotel_index}"):
                logger.warning(f"Failed to click hotel span #{hotel_index}")
                return None
            
            time.sleep(1)  # Reduced delay
            
            # Try to click jGuHr8 element if it exists
            jGuHr8_elements = self.driver.find_elements(By.CLASS_NAME, "jGuHr8")
            if jGuHr8_elements:
                logger.info(f"Found jGuHr8 element, clicking...")
                if self.safe_click(jGuHr8_elements[0], "jGuHr8 element"):
                    time.sleep(1)  # Reduced delay
            
            # Extract information from _eNcRc elements
            eNcRc_elements = self.driver.find_elements(By.CLASS_NAME, "_eNcRc")
            logger.info(f"Found {len(eNcRc_elements)} _eNcRc elements")
            
            extracted_texts = []
            for eNcRc_element in eNcRc_elements:
                try:
                    # Try p tags first
                    p_tags = eNcRc_element.find_elements(By.TAG_NAME, "p")
                    if p_tags:
                        for p_tag in p_tags:
                            text = p_tag.text.strip()
                            if text:
                                extracted_texts.append(text)
                    else:
                        # Get text from element itself
                        text = eNcRc_element.text.strip()
                        if text:
                            extracted_texts.append(text)
                except Exception as e:
                    logger.debug(f"Error extracting text: {e}")
            
            # Simple categorization
            if extracted_texts:
                hotel_data['hotel_name'] = extracted_texts[0] if extracted_texts else f"Hotel #{hotel_index}"
                hotel_data['amenities'] = extracted_texts[1:] if len(extracted_texts) > 1 else []
                
                # Look for price and rating patterns
                for text in extracted_texts:
                    if any(char in text for char in ['₹', '$', 'Rs', 'INR', 'price']):
                        hotel_data['price'] = text
                    elif any(word in text.lower() for word in ['rating', 'star', 'review']) and any(char.isdigit() for char in text):
                        hotel_data['rating'] = text
                    elif any(word in text.lower() for word in ['km', 'distance', 'location', 'near']):
                        hotel_data['location'] = text
            
            # Try to close modal quickly
            self.close_modal_quick()
            
            return hotel_data
            
        except Exception as e:
            logger.error(f"Error extracting hotel info for #{hotel_index}: {e}")
            self.close_modal_quick()
            return None
    
    def close_modal_quick(self):
        """Quick modal closing"""
        try:
            # Try ESC key first (fastest)
            from selenium.webdriver.common.keys import Keys
            self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            time.sleep(0.5)
            return True
        except:
            pass
        
        # Try close button
        close_selectors = ["_2rUXqG.Fhm_fk", "[class*='_2rUXqG']"]
        for selector in close_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    elements[0].click()
                    time.sleep(0.5)
                    return True
            except:
                continue
        
        return False
    
    def find_hotel_spans(self):
        """Find hotel spans"""
        selectors = [
            (By.CLASS_NAME, "_1Wh5Tf"),
            (By.CSS_SELECTOR, "[class*='_1Wh5Tf']")
        ]
        
        for by, selector in selectors:
            try:
                elements = self.driver.find_elements(by, selector)
                if elements:
                    logger.info(f"Found {len(elements)} hotel spans with selector: {selector}")
                    return elements
            except Exception as e:
                logger.debug(f"Error with selector {selector}: {e}")
        
        return []
    
    def run_test(self):
        """Run the test scraper"""
        if not self.setup_driver():
            return False
        
        try:
            url = "https://www.trivago.in/en-IN/lm/hotels-darjeeling-india?search=200-80950;dr-20250721-20250722#"
            logger.info(f"Loading: {url}")
            self.driver.get(url)
            
            time.sleep(3)  # Wait for page load
            logger.info(f"Page title: {self.driver.title}")
            
            # Process first page only for quick test
            logger.info("Processing first page...")
            hotel_spans = self.find_hotel_spans()
            
            if not hotel_spans:
                logger.warning("No hotel spans found")
                return False
            
            logger.info(f"Found {len(hotel_spans)} hotels, processing first 3 for testing...")
            
            # Process only first 3 hotels for quick test
            for index, span in enumerate(hotel_spans[:3]):
                try:
                    hotel_data = self.extract_hotel_info(span, index + 1)
                    if hotel_data:
                        self.hotels_data.append(hotel_data)
                        logger.info(f"Extracted: {hotel_data['hotel_name']}")
                    else:
                        logger.warning(f"Failed to extract data for hotel #{index + 1}")
                except Exception as e:
                    logger.error(f"Error processing hotel #{index + 1}: {e}")
                    continue
            
            # Save test results
            self.save_test_results()
            
            return True
            
        except Exception as e:
            logger.error(f"Error during test: {e}")
            return False
        finally:
            if self.driver:
                self.driver.quit()
                logger.info("Driver closed")
    
    def save_test_results(self):
        """Save test results to CSV"""
        if not self.hotels_data:
            logger.warning("No hotel data to save")
            return
        
        try:
            # Convert amenities list to string
            for hotel in self.hotels_data:
                hotel['amenities'] = " | ".join(hotel['amenities'])
            
            # Create DataFrame and save
            df = pd.DataFrame(self.hotels_data)
            filename = f"trivago_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df.to_csv(filename, index=False, encoding='utf-8')
            
            logger.info(f"Saved {len(self.hotels_data)} test hotels to {filename}")
            
            # Print results
            print(f"\n=== TEST RESULTS ===")
            print(f"Hotels processed: {len(self.hotels_data)}")
            print(f"Data saved to: {filename}")
            print(f"\nExtracted hotels:")
            for i, hotel in enumerate(self.hotels_data):
                print(f"  {i+1}. {hotel['hotel_name']}")
                print(f"     Price: {hotel['price']}")
                print(f"     Rating: {hotel['rating']}")
                print(f"     Amenities: {hotel['amenities'][:100]}...")
                print()
            
        except Exception as e:
            logger.error(f"Error saving test results: {e}")

def main():
    """Main test function"""
    print("=== Trivago Scraper Test ===")
    print("Testing with first 3 hotels from first page...")
    
    scraper = TrivagoScraperTest()
    success = scraper.run_test()
    
    if success:
        print("✅ Test completed successfully!")
        print("You can now run the full scraper: python3 trivago_scraper_complete.py")
    else:
        print("❌ Test failed!")
        print("Check the logs for error details")

if __name__ == "__main__":
    main()