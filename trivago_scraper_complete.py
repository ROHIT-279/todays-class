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
import re
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trivago_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TrivagoScraper:
    def __init__(self, headless=False):
        self.driver = None
        self.hotels_data = []
        self.current_page = 1
        self.max_pages = 20  # Safety limit
        self.headless = headless
        
    def setup_driver(self):
        """Setup Chrome driver with optimized options"""
        options = Options()
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        if self.headless:
            options.add_argument("--headless")
        
        try:
            self.driver = webdriver.Chrome(options=options)
            # Hide automation indicators
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            logger.info("Chrome driver initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Chrome driver: {e}")
            return False
    
    def wait_and_find_elements(self, by, value, timeout=10, multiple=True):
        """Wait for elements and return them with error handling"""
        try:
            wait = WebDriverWait(self.driver, timeout)
            if multiple:
                elements = wait.until(EC.presence_of_all_elements_located((by, value)))
            else:
                elements = wait.until(EC.presence_of_element_located((by, value)))
            return elements
        except TimeoutException:
            logger.warning(f"Timeout waiting for elements: {value}")
            return [] if multiple else None
        except Exception as e:
            logger.error(f"Error finding elements {value}: {e}")
            return [] if multiple else None
    
    def safe_click(self, element, element_name="element"):
        """Try multiple click methods with error handling"""
        click_methods = [
            ("regular", lambda: element.click()),
            ("javascript", lambda: self.driver.execute_script("arguments[0].click();", element)),
            ("action_chains", lambda: ActionChains(self.driver).move_to_element(element).click().perform()),
            ("offset", lambda: ActionChains(self.driver).move_to_element_with_offset(element, 5, 5).click().perform())
        ]
        
        for method_name, click_method in click_methods:
            try:
                # Scroll element into view
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});", element)
                time.sleep(1)
                
                # Try the click method
                click_method()
                logger.info(f"Successfully clicked {element_name} using {method_name} method")
                return True
            except Exception as e:
                logger.debug(f"{method_name} click failed for {element_name}: {e}")
                continue
        
        logger.error(f"All click methods failed for {element_name}")
        return False
    
    def extract_hotel_info(self, hotel_span, hotel_index):
        """Extract hotel information from a hotel span element"""
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
            
            time.sleep(2)  # Wait for modal to load
            
            # Try to click jGuHr8 element if it exists
            jGuHr8_elements = self.driver.find_elements(By.CLASS_NAME, "jGuHr8")
            if jGuHr8_elements:
                logger.info(f"Found {len(jGuHr8_elements)} jGuHr8 elements")
                if self.safe_click(jGuHr8_elements[0], "jGuHr8 element"):
                    time.sleep(3)  # Wait as requested
            
            # Extract information from _eNcRc elements
            eNcRc_elements = self.driver.find_elements(By.CLASS_NAME, "_eNcRc")
            logger.info(f"Found {len(eNcRc_elements)} _eNcRc elements")
            
            extracted_texts = []
            for eNcRc_index, eNcRc_element in enumerate(eNcRc_elements):
                try:
                    # Try to find p tags within the element
                    p_tags = eNcRc_element.find_elements(By.TAG_NAME, "p")
                    if p_tags:
                        for p_tag in p_tags:
                            p_text = p_tag.text.strip()
                            if p_text:
                                extracted_texts.append(p_text)
                                logger.info(f"Extracted text: {p_text}")
                    else:
                        # If no p tags, get text from the element itself
                        element_text = eNcRc_element.text.strip()
                        if element_text:
                            extracted_texts.append(element_text)
                            logger.info(f"Extracted direct text: {element_text}")
                except Exception as e:
                    logger.error(f"Error extracting from _eNcRc element #{eNcRc_index}: {e}")
            
            # Process extracted texts to categorize information
            self.categorize_hotel_info(extracted_texts, hotel_data)
            
            # Try to close the modal
            self.close_modal()
            
            return hotel_data
            
        except Exception as e:
            logger.error(f"Error extracting hotel info for #{hotel_index}: {e}")
            self.close_modal()  # Try to close modal even if extraction failed
            return None
    
    def categorize_hotel_info(self, texts, hotel_data):
        """Categorize extracted texts into hotel information fields"""
        for text in texts:
            text_lower = text.lower()
            
            # Try to identify hotel name (usually the first longer text)
            if not hotel_data['hotel_name'] and len(text) > 10 and not any(char.isdigit() for char in text[:5]):
                hotel_data['hotel_name'] = text
                
            # Try to identify price (contains currency symbols or price indicators)
            elif any(indicator in text_lower for indicator in ['₹', 'rs', 'inr', 'price', '$', '€']):
                hotel_data['price'] = text
                
            # Try to identify rating (contains numbers and rating indicators)
            elif any(indicator in text_lower for indicator in ['rating', 'star', 'review', 'score']) and any(char.isdigit() for char in text):
                hotel_data['rating'] = text
                
            # Try to identify location (contains location indicators)
            elif any(indicator in text_lower for indicator in ['location', 'address', 'km', 'distance', 'near']):
                hotel_data['location'] = text
                
            # Everything else goes to amenities
            else:
                hotel_data['amenities'].append(text)
    
    def close_modal(self):
        """Try to close any open modal"""
        close_selectors = [
            "_2rUXqG.Fhm_fk",
            "_2rUXqG Fhm_fk",
            "[class*='_2rUXqG']",
            "[class*='Fhm_fk']",
            "button[aria-label='Close']",
            ".close-button",
            "[data-testid='close']"
        ]
        
        for selector in close_selectors:
            try:
                if "." in selector and " " not in selector:
                    elements = self.driver.find_elements(By.CLASS_NAME, selector)
                else:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                
                if elements:
                    logger.info(f"Found {len(elements)} close elements with selector: {selector}")
                    if self.safe_click(elements[0], "close element"):
                        time.sleep(1)
                        return True
            except Exception as e:
                logger.debug(f"Error with close selector {selector}: {e}")
                continue
        
        # Try ESC key as last resort
        try:
            from selenium.webdriver.common.keys import Keys
            self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            logger.info("Sent ESC key to close modal")
            time.sleep(1)
            return True
        except Exception as e:
            logger.debug(f"ESC key failed: {e}")
        
        return False
    
    def check_next_page(self):
        """Check if there's a next page and navigate to it"""
        next_page_selectors = [
            "button[aria-label='Next page']",
            "button[data-testid='next-page']",
            ".pagination-next",
            "[class*='next']",
            "button:contains('Next')",
            "a[aria-label='Next']"
        ]
        
        for selector in next_page_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if element.is_enabled() and element.is_displayed():
                        logger.info(f"Found next page button with selector: {selector}")
                        if self.safe_click(element, "next page button"):
                            self.current_page += 1
                            logger.info(f"Successfully navigated to page {self.current_page}")
                            time.sleep(5)  # Wait for page to load
                            return True
            except Exception as e:
                logger.debug(f"Error with next page selector {selector}: {e}")
                continue
        
        logger.info("No next page button found or clickable")
        return False
    
    def scrape_all_pages(self, base_url):
        """Main scraping function that iterates through all pages"""
        if not self.setup_driver():
            return False
        
        try:
            logger.info(f"Starting scrape of: {base_url}")
            self.driver.get(base_url)
            
            # Wait for initial page load
            time.sleep(5)
            logger.info(f"Page title: {self.driver.title}")
            logger.info(f"Current URL: {self.driver.current_url}")
            
            while self.current_page <= self.max_pages:
                logger.info(f"Scraping page {self.current_page}")
                
                # Find hotel spans on current page
                hotel_spans = self.find_hotel_spans()
                
                if not hotel_spans:
                    logger.warning(f"No hotel spans found on page {self.current_page}")
                    if self.current_page == 1:
                        # Save debug info for first page
                        self.save_debug_info()
                    break
                
                logger.info(f"Found {len(hotel_spans)} hotels on page {self.current_page}")
                
                # Extract data from each hotel
                for index, span in enumerate(hotel_spans):
                    try:
                        hotel_data = self.extract_hotel_info(span, index + 1)
                        if hotel_data:
                            self.hotels_data.append(hotel_data)
                            logger.info(f"Successfully extracted data for hotel #{index + 1}")
                        else:
                            logger.warning(f"Failed to extract data for hotel #{index + 1}")
                    except Exception as e:
                        logger.error(f"Error processing hotel #{index + 1}: {e}")
                        continue
                
                # Try to go to next page
                if not self.check_next_page():
                    logger.info("No more pages found, scraping complete")
                    break
                
                # Safety check
                if self.current_page > self.max_pages:
                    logger.warning(f"Reached maximum page limit ({self.max_pages})")
                    break
            
            # Save results to CSV
            self.save_to_csv()
            
            return True
            
        except Exception as e:
            logger.error(f"Error during scraping: {e}")
            return False
        finally:
            if self.driver:
                self.driver.quit()
                logger.info("Driver closed")
    
    def find_hotel_spans(self):
        """Find hotel spans using multiple methods"""
        selectors = [
            (By.CLASS_NAME, "_1Wh5Tf"),
            (By.CSS_SELECTOR, "[class*='_1Wh5Tf']"),
            (By.CSS_SELECTOR, "[class*='hotel']"),
            (By.CSS_SELECTOR, "[data-testid*='hotel']")
        ]
        
        for by, selector in selectors:
            try:
                elements = self.driver.find_elements(by, selector)
                if elements:
                    logger.info(f"Found {len(elements)} hotel spans with selector: {selector}")
                    return elements
            except Exception as e:
                logger.debug(f"Error with selector {selector}: {e}")
                continue
        
        logger.warning("No hotel spans found with any selector")
        return []
    
    def save_debug_info(self):
        """Save page source and element information for debugging"""
        try:
            # Save page source
            with open(f"trivago_debug_page_{self.current_page}.html", "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            logger.info(f"Page source saved to trivago_debug_page_{self.current_page}.html")
            
            # Save element information
            debug_info = []
            all_spans = self.driver.find_elements(By.TAG_NAME, "span")
            for i, span in enumerate(all_spans[:20]):  # First 20 spans
                class_attr = span.get_attribute("class")
                if class_attr:
                    debug_info.append(f"Span {i+1}: {class_attr}")
            
            with open(f"trivago_debug_elements_{self.current_page}.txt", "w", encoding="utf-8") as f:
                f.write("\n".join(debug_info))
            logger.info(f"Element info saved to trivago_debug_elements_{self.current_page}.txt")
            
        except Exception as e:
            logger.error(f"Error saving debug info: {e}")
    
    def save_to_csv(self):
        """Save extracted hotel data to CSV file"""
        if not self.hotels_data:
            logger.warning("No hotel data to save")
            return
        
        try:
            # Convert amenities list to string
            for hotel in self.hotels_data:
                hotel['amenities'] = " | ".join(hotel['amenities'])
            
            # Create DataFrame and save to CSV
            df = pd.DataFrame(self.hotels_data)
            filename = f"trivago_hotels_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df.to_csv(filename, index=False, encoding='utf-8')
            
            logger.info(f"Saved {len(self.hotels_data)} hotels to {filename}")
            
            # Print summary
            print(f"\n=== SCRAPING SUMMARY ===")
            print(f"Total hotels extracted: {len(self.hotels_data)}")
            print(f"Pages scraped: {self.current_page}")
            print(f"Hotels with names: {len([h for h in self.hotels_data if h['hotel_name']])}")
            print(f"Hotels with prices: {len([h for h in self.hotels_data if h['price']])}")
            print(f"Hotels with ratings: {len([h for h in self.hotels_data if h['rating']])}")
            print(f"Data saved to: {filename}")
            
            # Show first few records
            print(f"\nFirst 3 hotels:")
            for i, hotel in enumerate(self.hotels_data[:3]):
                print(f"  {i+1}. {hotel['hotel_name'][:50]}...")
                print(f"     Price: {hotel['price']}")
                print(f"     Rating: {hotel['rating']}")
                print(f"     Page: {hotel['page_number']}")
                print()
            
        except Exception as e:
            logger.error(f"Error saving to CSV: {e}")

def main():
    """Main function to run the scraper"""
    # Trivago URL for Darjeeling hotels
    url = "https://www.trivago.in/en-IN/lm/hotels-darjeeling-india?search=200-80950;dr-20250721-20250722#"
    
    # Create scraper instance
    scraper = TrivagoScraper(headless=False)  # Set to True for headless mode
    
    # Start scraping
    logger.info("Starting Trivago hotel scraper...")
    success = scraper.scrape_all_pages(url)
    
    if success:
        logger.info("Scraping completed successfully!")
    else:
        logger.error("Scraping failed!")

if __name__ == "__main__":
    main()