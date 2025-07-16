from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
import time

def test_agoda_structure():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    url = "https://www.agoda.com/en-in/search?guid=ac34b805-fbbb-4a54-91f6-72bd44251297&asq=oSBZUdCJkTqIcAJrG1AX8Jufa9Vwpz6XltTHq4n%2B9gNpSLc%2BT%2BpB%2F8FnmmA8sOyAJ0WZY5hpLWEr%2Fk8qr78gW4DMS7e7llLtqq76yKsoLJ2OoQ3gw8ln%2FUAwfEcSpHO4IoT8r2EKxXsqX%2FNiA5fxsgqQMycviD3CIWSJVwpQ8sqLB7kVtS1F64bq7yiJpY541pwsBzifP5NpR6wrJ1u54kHb%2BKC2e3zym6tmyvlzCzM%3D&city=10863&tick=638881978745&locale=en-in&ckuid=0782016a-40d3-4e7a-86a4-8cab9dacec41&prid=0&gclid=Cj0KCQjw-NfDBhDyARIsAD-ILeBXva5TJhq-jGK3Si0BOfvtLo82iIstmv4-XMoqfU56Mshxz_UezUkaAhwMEALw_wcB&currency=INR&correlationId=55168ae7-8bc1-4224-a8eb-86ba246be729&analyticsSessionId=-1950121884218971931&pageTypeId=1&realLanguageId=15&languageId=1&origin=IN&stateCode=WB&cid=1922885&tag=6f147157-60b8-459f-af1a-9935d44970e9&userId=0782016a-40d3-4e7a-86a4-8cab9dacec41&whitelabelid=1&loginLvl=0&storefrontId=3&currencyId=27&currencyCode=INR&htmlLanguage=en-in&cultureInfoName=en-in&machineName=sg-pc-6h-acm-web-user-8697c4cd7c-gmgqx&trafficGroupId=5&trafficSubGroupId=122&aid=82361&useFullPageLogin=true&cttp=4&isRealUser=true&mode=production&browserFamily=Chrome&cdnDomain=agoda.net&checkIn=2025-08-12&checkOut=2025-08-13&rooms=1&adults=2&children=0&priceCur=INR&los=1&textToSearch=Darjeeling&travellerType=1&familyMode=off&ds=cgN73pCK5wrspJ7h&productType=-1"
    
    driver = webdriver.Firefox(options=options)
    
    try:
        print("Loading page...")
        driver.get(url)
        
        # Wait for page to load
        time.sleep(10)
        
        # Get page source
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        print(f"Page title: {soup.title.text if soup.title else 'No title'}")
        
        # Check for different possible hotel list containers
        containers = [
            'ol[data-selenium="hotel-list"]',
            'ul[data-selenium="hotel-list"]',
            'div[data-selenium="hotel-list"]',
            'ol[data-element-name="hotel-list"]',
            'ul[data-element-name="hotel-list"]',
            'div[data-element-name="hotel-list"]',
            'ol[data-testid="hotel-list"]',
            'ul[data-testid="hotel-list"]',
            'div[data-testid="hotel-list"]'
        ]
        
        print("\n=== Checking container selectors ===")
        for container in containers:
            found = soup.select(container)
            if found:
                print(f"✓ Found {len(found)} elements with selector: {container}")
                # Check what's inside
                for i, elem in enumerate(found[:2]):
                    children = elem.find_all(['li', 'div'], recursive=False)
                    print(f"  Container {i+1} has {len(children)} direct children")
            else:
                print(f"✗ No elements found with selector: {container}")
        
        # Try to find hotel items directly
        hotel_selectors = [
            'li[data-selenium="hotel-item"]',
            'div[data-selenium="hotel-item"]',
            'li[data-element-name="hotel-item"]',
            'div[data-element-name="hotel-item"]',
            'li[data-testid="hotel-item"]',
            'div[data-testid="hotel-item"]',
            'li[id*="hotel"]',
            'div[id*="hotel"]'
        ]
        
        print("\n=== Checking hotel item selectors ===")
        for selector in hotel_selectors:
            found = soup.select(selector)
            if found:
                print(f"✓ Found {len(found)} hotel items with selector: {selector}")
                # Show sample
                if found:
                    print(f"  Sample hotel HTML (first 200 chars):")
                    print(f"    {str(found[0])[:200]}...")
            else:
                print(f"✗ No hotel items found with selector: {selector}")
        
        # Find all li elements and check their attributes
        all_li = soup.select('li')
        print(f"\n=== Found {len(all_li)} total <li> elements ===")
        
        data_attributes = {}
        for li in all_li[:20]:  # Check first 20 li elements
            for attr in li.attrs:
                if attr.startswith('data-'):
                    if attr not in data_attributes:
                        data_attributes[attr] = []
                    data_attributes[attr].append(li.attrs[attr])
        
        print("Common data attributes found:")
        for attr, values in data_attributes.items():
            unique_values = list(set(values))
            print(f"  {attr}: {unique_values[:5]}...")  # Show first 5 unique values
        
        # Save sample HTML for manual inspection
        with open("sample_html.html", "w", encoding="utf-8") as f:
            f.write(str(soup))
        
        print("\n=== Sample HTML saved to sample_html.html ===")
        
    except Exception as e:
        print(f"Error: {e}")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    test_agoda_structure()