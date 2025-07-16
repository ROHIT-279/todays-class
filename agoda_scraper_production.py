from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import (
    NoSuchElementException, 
    TimeoutException, 
    ElementNotInteractableException,
    ElementClickInterceptedException,
    WebDriverException
)
import time
import pandas as pd
import logging
import traceback

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def dismiss_consent_banner(driver):
    """Try to dismiss any consent banners that might be blocking interactions"""
    consent_selectors = [
        'button[data-selenium="consent-banner-accept"]',
        'button[id*="consent"]',
        'button[class*="consent"]',
        'button:contains("Accept")',
        'button:contains("OK")',
        'button:contains("Agree")',
        '.consent-banner button',
        '.cookie-banner button',
        '#consent-banner button'
    ]
    
    for selector in consent_selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for element in elements:
                if element.is_displayed() and element.is_enabled():
                    logger.info(f"Dismissing consent banner with selector: {selector}")
                    element.click()
                    time.sleep(2)
                    return True
        except Exception as e:
            logger.debug(f"Error dismissing consent with selector {selector}: {str(e)}")
            continue
    
    return False

def scroll_to_element(driver, element):
    """Scroll to an element to make it visible"""
    try:
        driver.execute_script("arguments[0].scrollIntoView(true);", element)
        time.sleep(1)
    except Exception as e:
        logger.debug(f"Error scrolling to element: {str(e)}")

def scrape_and_save():
    # Set up headless Firefox options
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    
    url = "https://www.agoda.com/en-in/search?guid=ac34b805-fbbb-4a54-91f6-72bd44251297&asq=oSBZUdCJkTqIcAJrG1AX8Jufa9Vwpz6XltTHq4n%2B9gNpSLc%2BT%2BpB%2F8FnmmA8sOyAJ0WZY5hpLWEr%2Fk8qr78gW4DMS7e7llLtqq76yKsoLJ2OoQ3gw8ln%2FUAwfEcSpHO4IoT8r2EKxXsqX%2FNiA5fxsgqQMycviD3CIWSJVwpQ8sqLB7kVtS1F64bq7yiJpY541pwsBzifP5NpR6wrJ1u54kHb%2BKC2e3zym6tmyvlzCzM%3D&city=10863&tick=638881978745&locale=en-in&ckuid=0782016a-40d3-4e7a-86a4-8cab9dacec41&prid=0&gclid=Cj0KCQjw-NfDBhDyARIsAD-ILeBXva5TJhq-jGK3Si0BOfvtLo82iIstmv4-XMoqfU56Mshxz_UezUkaAhwMEALw_wcB&currency=INR&correlationId=55168ae7-8bc1-4224-a8eb-86ba246be729&analyticsSessionId=-1950121884218971931&pageTypeId=1&realLanguageId=15&languageId=1&origin=IN&stateCode=WB&cid=1922885&tag=6f147157-60b8-459f-af1a-9935d44970e9&userId=0782016a-40d3-4e7a-86a4-8cab9dacec41&whitelabelid=1&loginLvl=0&storefrontId=3&currencyId=27&currencyCode=INR&htmlLanguage=en-in&cultureInfoName=en-in&machineName=sg-pc-6h-acm-web-user-8697c4cd7c-gmgqx&trafficGroupId=5&trafficSubGroupId=122&aid=82361&useFullPageLogin=true&cttp=4&isRealUser=true&mode=production&browserFamily=Chrome&cdnDomain=agoda.net&checkIn=2025-08-12&checkOut=2025-08-13&rooms=1&adults=2&children=0&priceCur=INR&los=1&textToSearch=Darjeeling&travellerType=1&familyMode=off&ds=cgN73pCK5wrspJ7h&productType=-1"
    
    driver = None
    
    try:
        logger.info("Initializing Firefox driver...")
        driver = webdriver.Firefox(options=options)
        
        logger.info("Loading page...")
        driver.get(url)
        
        # Try to dismiss consent banners early
        time.sleep(3)
        dismiss_consent_banner(driver)
        
        # Wait for hotels to load with better error handling
        logger.info("Waiting for hotels to load...")
        try:
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'li[data-selenium="hotel-item"]'))
            )
            logger.info("Hotels loaded successfully")
        except TimeoutException:
            logger.error("Timeout waiting for hotels to load")
            # Try to save page source for debugging
            with open("debug_page_source.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            logger.info("Page source saved to debug_page_source.html")
            return
        
        # Give extra time for dynamic content to load
        time.sleep(10)
        
        all_hotels_html = []
        seen_hotel_ids = set()
        max_iterations = 3  # Increased iterations
        
        for iteration in range(max_iterations):
            logger.info(f"Iteration {iteration + 1}/{max_iterations}")
            
            try:
                # Scroll down to load more hotels
                logger.info("Scrolling to load more content...")
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(3)
                
                # Get current page source
                soup = BeautifulSoup(driver.page_source, "html.parser")
                
                # Find all hotel items using the selector we know works
                hotel_items = soup.select('li[data-selenium="hotel-item"]')
                
                logger.info(f"Found {len(hotel_items)} hotel items on page")
                
                if len(hotel_items) == 0:
                    logger.warning("No hotel items found! Checking page structure...")
                    # Save debug info
                    with open("debug_no_hotels.html", "w", encoding="utf-8") as f:
                        f.write(driver.page_source)
                    logger.info("Debug page saved to debug_no_hotels.html")
                    break
                
                # Add new hotels to our collection
                for hotel in hotel_items:
                    # Use hotel ID as unique identifier
                    hotel_id = hotel.get('data-hotelid') or str(hash(str(hotel)[:100]))
                    
                    if hotel_id not in seen_hotel_ids:
                        seen_hotel_ids.add(hotel_id)
                        all_hotels_html.append(str(hotel))
                        logger.info(f"Added hotel with ID: {hotel_id}")
                
                # Try to find and click next page/load more button with better error handling
                logger.info("Looking for pagination buttons...")
                try:
                    # Dismiss any consent banners first
                    dismiss_consent_banner(driver)
                    
                    # Look for pagination or load more buttons
                    next_selectors = [
                        'button[data-selenium="pagination-next-btn"]',
                        'button[aria-label="Next page"]',
                        '.pagination-next',
                        '.load-more-btn',
                        'button[class*="next"]',
                        'a[aria-label="Next page"]',
                        '#paginationNext'
                    ]
                    
                    clicked = False
                    for selector in next_selectors:
                        try:
                            logger.info(f"Trying selector: {selector}")
                            elements = driver.find_elements(By.CSS_SELECTOR, selector)
                            
                            if elements:
                                logger.info(f"Found {len(elements)} elements with selector: {selector}")
                                next_button = elements[0]
                                
                                if next_button.is_enabled() and next_button.is_displayed():
                                    logger.info(f"Attempting to click next button with selector: {selector}")
                                    
                                    # Try multiple click strategies
                                    click_attempts = [
                                        lambda: next_button.click(),  # Direct click
                                        lambda: driver.execute_script("arguments[0].click();", next_button),  # JavaScript click
                                        lambda: ActionChains(driver).move_to_element(next_button).click().perform()  # Action chain
                                    ]
                                    
                                    for attempt_num, click_method in enumerate(click_attempts):
                                        try:
                                            # Scroll to element first
                                            scroll_to_element(driver, next_button)
                                            
                                            # Try to dismiss any overlays
                                            dismiss_consent_banner(driver)
                                            
                                            # Attempt click
                                            click_method()
                                            logger.info(f"Successfully clicked next button using method {attempt_num + 1}")
                                            time.sleep(5)
                                            clicked = True
                                            break
                                            
                                        except ElementClickInterceptedException as e:
                                            logger.warning(f"Click intercepted on attempt {attempt_num + 1}: {str(e)}")
                                            if attempt_num < len(click_attempts) - 1:
                                                time.sleep(2)
                                                continue
                                            else:
                                                logger.error("All click attempts failed due to interception")
                                                
                                        except Exception as e:
                                            logger.warning(f"Click attempt {attempt_num + 1} failed: {str(e)}")
                                            continue
                                    
                                    if clicked:
                                        break
                                else:
                                    logger.info(f"Button found but not clickable: {selector}")
                            else:
                                logger.info(f"No elements found with selector: {selector}")
                                
                        except Exception as e:
                            logger.info(f"Error with selector {selector}: {str(e)}")
                            continue
                    
                    if not clicked:
                        logger.info("No next button found or clickable, stopping pagination")
                        break
                        
                except Exception as e:
                    logger.error(f"Error in pagination logic: {str(e)}")
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    break
                    
            except Exception as e:
                logger.error(f"Error in iteration {iteration + 1}: {str(e)}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                break
        
        logger.info(f"Collected {len(all_hotels_html)} unique hotels")
        
        if len(all_hotels_html) == 0:
            logger.error("No hotels collected! Check debug files.")
            return
        
        # Save raw HTML
        with open("unstructuredData_agoda.html", "w", encoding="utf-8") as f:
            f.write('<html><body>')
            f.write('\n'.join(all_hotels_html))
            f.write('</body></html>')
        
        # Parse the collected HTML data
        combined_html = '\n'.join(all_hotels_html)
        soup = BeautifulSoup(combined_html, "html.parser")
        
        # Extract structured data using multiple strategies
        hotels_data = []
        
        # Find all hotel items
        hotel_cards = soup.select('li[data-selenium="hotel-item"]')
        logger.info(f"Processing {len(hotel_cards)} hotel cards for data extraction")
        
        for i, card in enumerate(hotel_cards):
            logger.info(f"Processing hotel {i+1}")
            
            # Extract hotel name - try multiple selectors
            name = ""
            name_selectors = [
                '[data-selenium="hotel-name"]',
                'h3 a',
                'h3',
                'h4',
                'h2',
                '.hotel-name',
                '.property-name',
                'a[href*="hotel"]',
                '[class*="name"]',
                '[class*="title"]',
                '[class*="PropertyName"]'
            ]
            
            for selector in name_selectors:
                try:
                    name_element = card.select_one(selector)
                    if name_element:
                        name = name_element.get_text(strip=True)
                        if name and len(name) > 3:  # Valid name
                            break
                except Exception as e:
                    logger.debug(f"Error with name selector {selector}: {str(e)}")
                    continue
            
            # Extract price - try multiple selectors
            price = ""
            price_selectors = [
                '[data-selenium="hotel-price"]',
                '.price',
                '[class*="price"]',
                '[class*="Price"]',
                '[class*="rate"]',
                '[class*="cost"]',
                'span:-soup-contains("Rs")',
                'span:-soup-contains("INR")',
                'span:-soup-contains("₹")'
            ]
            
            for selector in price_selectors:
                try:
                    price_element = card.select_one(selector)
                    if price_element:
                        price_text = price_element.get_text(strip=True)
                        if price_text and ('Rs' in price_text or 'INR' in price_text or '₹' in price_text or price_text.replace(',', '').replace('.', '').isdigit()):
                            price = price_text
                            break
                except Exception as e:
                    logger.debug(f"Error with price selector {selector}: {str(e)}")
                    continue
            
            # Extract rating - try multiple selectors
            rating = ""
            rating_selectors = [
                '[data-selenium="review-score"]',
                '.rating',
                '.review-score',
                '.score',
                '[class*="rating"]',
                '[class*="Rating"]',
                '[class*="score"]',
                '[class*="Score"]',
                '[class*="review"]',
                '[class*="Review"]'
            ]
            
            for selector in rating_selectors:
                try:
                    rating_element = card.select_one(selector)
                    if rating_element:
                        rating_text = rating_element.get_text(strip=True)
                        if rating_text and (rating_text.replace('.', '').isdigit() or 'out of' in rating_text.lower()):
                            rating = rating_text
                            break
                except Exception as e:
                    logger.debug(f"Error with rating selector {selector}: {str(e)}")
                    continue
            
            # Extract hotel ID
            hotel_id = card.get('data-hotelid', '')
            
            # Only add if we found at least a name
            if name:
                hotels_data.append({
                    "hotel_id": hotel_id,
                    "name": name,
                    "price": price,
                    "rating": rating
                })
                logger.info(f"Extracted: {name[:50]}...")
        
        # Save to CSV
        if hotels_data:
            df = pd.DataFrame(hotels_data)
            df.to_csv("agoda_hotels_structured.csv", index=False, encoding="utf-8")
            logger.info(f"Saved {len(hotels_data)} hotels to agoda_hotels_structured.csv")
            
            # Print first few records for verification
            print("First 5 hotels found:")
            print(df.head())
            
            # Print summary
            print(f"\nSummary:")
            print(f"Total hotels: {len(hotels_data)}")
            print(f"Hotels with prices: {len([h for h in hotels_data if h['price']])}")
            print(f"Hotels with ratings: {len([h for h in hotels_data if h['rating']])}")
            
        else:
            logger.warning("No hotel data found!")
            
            # Save debug info
            with open("debug_output.txt", "w", encoding="utf-8") as f:
                f.write("=== DEBUG INFO ===\n")
                f.write(f"Total hotel cards found: {len(hotel_cards)}\n")
                f.write(f"HTML length: {len(combined_html)}\n")
                f.write(f"First 1000 chars of HTML:\n{combined_html[:1000]}\n")
                f.write("\n=== SAMPLE HOTEL HTML ===\n")
                for i, hotel in enumerate(hotel_cards[:3]):
                    f.write(f"\n--- Hotel {i+1} ---\n")
                    f.write(str(hotel)[:1000])
                    f.write("\n")
                    
    except WebDriverException as e:
        logger.error(f"WebDriver error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
    except Exception as e:
        logger.error(f"Unexpected error during scraping: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
    finally:
        if driver:
            try:
                driver.quit()
                logger.info("Driver closed successfully")
            except Exception as e:
                logger.error(f"Error closing driver: {str(e)}")

if __name__ == "__main__":
    scrape_and_save()