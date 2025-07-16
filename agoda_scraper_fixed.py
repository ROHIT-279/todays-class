from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
import time
import pandas as pd
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def scrape_and_save():
    # Set up headless Firefox options
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    url = "https://www.agoda.com/en-in/search?guid=ac34b805-fbbb-4a54-91f6-72bd44251297&asq=oSBZUdCJkTqIcAJrG1AX8Jufa9Vwpz6XltTHq4n%2B9gNpSLc%2BT%2BpB%2F8FnmmA8sOyAJ0WZY5hpLWEr%2Fk8qr78gW4DMS7e7llLtqq76yKsoLJ2OoQ3gw8ln%2FUAwfEcSpHO4IoT8r2EKxXsqX%2FNiA5fxsgqQMycviD3CIWSJVwpQ8sqLB7kVtS1F64bq7yiJpY541pwsBzifP5NpR6wrJ1u54kHb%2BKC2e3zym6tmyvlzCzM%3D&city=10863&tick=638881978745&locale=en-in&ckuid=0782016a-40d3-4e7a-86a4-8cab9dacec41&prid=0&gclid=Cj0KCQjw-NfDBhDyARIsAD-ILeBXva5TJhq-jGK3Si0BOfvtLo82iIstmv4-XMoqfU56Mshxz_UezUkaAhwMEALw_wcB&currency=INR&correlationId=55168ae7-8bc1-4224-a8eb-86ba246be729&analyticsSessionId=-1950121884218971931&pageTypeId=1&realLanguageId=15&languageId=1&origin=IN&stateCode=WB&cid=1922885&tag=6f147157-60b8-459f-af1a-9935d44970e9&userId=0782016a-40d3-4e7a-86a4-8cab9dacec41&whitelabelid=1&loginLvl=0&storefrontId=3&currencyId=27&currencyCode=INR&htmlLanguage=en-in&cultureInfoName=en-in&machineName=sg-pc-6h-acm-web-user-8697c4cd7c-gmgqx&trafficGroupId=5&trafficSubGroupId=122&aid=82361&useFullPageLogin=true&cttp=4&isRealUser=true&mode=production&browserFamily=Chrome&cdnDomain=agoda.net&checkIn=2025-08-12&checkOut=2025-08-13&rooms=1&adults=2&children=0&priceCur=INR&los=1&textToSearch=Darjeeling&travellerType=1&familyMode=off&ds=cgN73pCK5wrspJ7h&productType=-1"
    
    driver = webdriver.Firefox(options=options)
    
    try:
        logger.info("Loading page...")
        driver.get(url)
        
        # Wait for hotels to load
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'ol[data-selenium="hotel-list"]'))
        )
        
        all_hotels_html = []
        seen_hotel_ids = set()  # Track unique hotels by ID instead of full HTML
        max_iterations = 3  # Reduce for testing
        
        for iteration in range(max_iterations):
            logger.info(f"Iteration {iteration + 1}/{max_iterations}")
            
            try:
                # Scroll down to load more hotels
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(3)
                
                # Get current page source
                soup = BeautifulSoup(driver.page_source, "html.parser")
                
                # Find all hotel items
                hotel_items = soup.select('ol[data-selenium="hotel-list"] li')
                
                logger.info(f"Found {len(hotel_items)} hotel items on page")
                
                # Add new hotels to our collection
                for hotel in hotel_items:
                    # Create a unique identifier for each hotel
                    hotel_id = hotel.get('data-selenium-hotel-id') or hotel.get('id') or str(hash(str(hotel)[:100]))
                    
                    if hotel_id not in seen_hotel_ids:
                        seen_hotel_ids.add(hotel_id)
                        all_hotels_html.append(str(hotel))
                
                # Try to click "Load More" or "Next Page" button
                try:
                    next_button = driver.find_element(By.CSS_SELECTOR, 'button[data-selenium="pagination-next-btn"]')
                    if next_button.is_enabled():
                        next_button.click()
                        time.sleep(5)
                    else:
                        logger.info("Next button not enabled, stopping")
                        break
                except Exception as e:
                    logger.info(f"No next button found or error clicking: {e}")
                    break
                    
            except Exception as e:
                logger.error(f"Error in iteration {iteration + 1}: {e}")
                break
        
        # Save raw HTML
        logger.info(f"Saving {len(all_hotels_html)} hotels to HTML file")
        with open("unstructuredData_agoda.html", "w", encoding="utf-8") as f:
            f.write('<html><body>')
            f.write('\n'.join(all_hotels_html))
            f.write('</body></html>')
        
        # Parse the collected HTML data
        combined_html = '\n'.join(all_hotels_html)
        soup = BeautifulSoup(combined_html, "html.parser")
        
        # Extract structured data with multiple selector strategies
        hotels_data = []
        
        # Try multiple CSS selectors for different elements
        hotel_selectors = [
            'li[data-selenium="hotel-item"]',
            'li[data-element-name="hotel-item"]',
            'li[data-testid="hotel-item"]',
            'li[id*="hotel"]',
            'li[class*="hotel"]'
        ]
        
        name_selectors = [
            '[data-selenium="hotel-name"]',
            '[data-element-name="hotel-name"]',
            '[data-testid="hotel-name"]',
            'h3',
            'h4',
            '.hotel-name',
            '.property-name',
            'a[href*="hotel"]'
        ]
        
        price_selectors = [
            '[data-selenium="hotel-price"]',
            '[data-element-name="hotel-price"]',
            '[data-testid="hotel-price"]',
            '.price',
            '.hotel-price',
            '.property-price',
            '[class*="price"]',
            '[id*="price"]'
        ]
        
        rating_selectors = [
            '[data-selenium="review-score"]',
            '[data-element-name="review-score"]',
            '[data-testid="review-score"]',
            '.rating',
            '.review-score',
            '.score',
            '[class*="rating"]',
            '[class*="score"]'
        ]
        
        # Find hotels using multiple selectors
        hotels_found = []
        for selector in hotel_selectors:
            found = soup.select(selector)
            if found:
                hotels_found = found
                logger.info(f"Found {len(found)} hotels using selector: {selector}")
                break
        
        if not hotels_found:
            # Fallback: try to find any list items that might contain hotel data
            hotels_found = soup.select('li')
            logger.info(f"Fallback: Found {len(hotels_found)} li elements")
        
        for hotel in hotels_found:
            # Extract hotel name
            name = ""
            for selector in name_selectors:
                name_element = hotel.select_one(selector)
                if name_element:
                    name = name_element.get_text(strip=True)
                    if name:
                        break
            
            # Extract price
            price = ""
            for selector in price_selectors:
                price_element = hotel.select_one(selector)
                if price_element:
                    price = price_element.get_text(strip=True)
                    if price:
                        break
            
            # Extract rating
            rating = ""
            for selector in rating_selectors:
                rating_element = hotel.select_one(selector)
                if rating_element:
                    rating = rating_element.get_text(strip=True)
                    if rating:
                        break
            
            # Only add if we found at least some data
            if name or price or rating:
                hotels_data.append({
                    "name": name,
                    "price": price,
                    "rating": rating
                })
        
        # Save to CSV
        if hotels_data:
            df = pd.DataFrame(hotels_data)
            df.to_csv("agoda_hotels_structured.csv", index=False, encoding="utf-8")
            logger.info(f"Saved {len(hotels_data)} hotels to agoda_hotels_structured.csv")
            
            # Print first few records for verification
            print("First 5 hotels found:")
            print(df.head())
        else:
            logger.warning("No hotel data found!")
            
            # Debug: Let's see what we actually got
            print("Debug: First 500 characters of HTML:")
            print(combined_html[:500])
            
            # Save debug info
            with open("debug_output.txt", "w", encoding="utf-8") as f:
                f.write("=== DEBUG INFO ===\n")
                f.write(f"Total hotels found: {len(hotels_found)}\n")
                f.write(f"HTML length: {len(combined_html)}\n")
                f.write(f"First 1000 chars of HTML:\n{combined_html[:1000]}\n")
                f.write("\n=== SAMPLE HOTEL HTML ===\n")
                for i, hotel in enumerate(hotels_found[:3]):
                    f.write(f"\n--- Hotel {i+1} ---\n")
                    f.write(str(hotel)[:500])
                    
    except Exception as e:
        logger.error(f"Error during scraping: {e}")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    scrape_and_save()