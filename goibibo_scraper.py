from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import pandas as pd
import time

# Setup ChromeDriver
options = Options()
options.add_argument("--headless")  # Run headless for better compatibility
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920,1080")
options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

# Use system chrome driver instead of hardcoded Windows path
driver = webdriver.Chrome(options=options)

# Goibibo Darjeeling hotels URL (updated)
url = "https://www.goibibo.com/hotels/hotel-listing/?checkin=2025-07-28&checkout=2025-07-29&roomString=1-2-0&searchText=Darjeeling&locusId=CTIXB&locusType=city&cityCode=CTIXB"
driver.get(url)
print("🔍 Opening hotel listing page...")
time.sleep(10)

# Scroll down to load full hotel list
driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
time.sleep(10)

# Wait for hotel cards to appear
try:
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div.HotelCardstyles__HotelCardWrapDiv-sc-1s80tyk-8"))
    )
    print("✅ Hotel cards loaded")
except:
    print("❌ Hotel cards not found — possible JS issue or class name changed")
    
    # Let's try to find any hotel-related elements
    print("🔍 Searching for alternative selectors...")
    soup = BeautifulSoup(driver.page_source, "lxml")
    
    # Save the page source for debugging
    with open("page_source.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    print("📄 Page source saved to page_source.html for analysis")

# Parse page
soup = BeautifulSoup(driver.page_source, "lxml")
cards = soup.select("div.HotelCardstyles__HotelCardWrapDiv-sc-1s80tyk-8")

print(f"Found {len(cards)} hotel cards with original selector")

# Try alternative selectors if original doesn't work
if not cards:
    print("🔍 Trying alternative selectors...")
    
    # Common hotel card patterns
    alternative_selectors = [
        "div[data-testid*='hotel']",
        "div[class*='hotel']",
        "div[class*='Hotel']",
        "div[class*='card']",
        "div[class*='Card']",
        ".hotel-card",
        ".HotelCard",
        "[data-cy*='hotel']"
    ]
    
    for selector in alternative_selectors:
        cards = soup.select(selector)
        if cards:
            print(f"✅ Found {len(cards)} elements with selector: {selector}")
            break
    
    # If still no luck, let's see what elements exist
    if not cards:
        print("🔍 Looking for any div elements with class attributes...")
        all_divs = soup.find_all("div", class_=True)[:10]  # First 10 divs with classes
        for i, div in enumerate(all_divs):
            print(f"Div {i}: {div.get('class')}")

hotels = []
for card in cards:
    name = card.find("h3")
    price = card.find("span", class_="PriceSection__Amount-sc-1jefptr-1")
    rating = card.find("span", class_="ReviewScore__NumberWrapper-sc-1cjefq8-1")

    if name:
        hotels.append({
            "Hotel Name": name.get_text(strip=True),
            "Price": price.get_text(strip=True) if price else "N/A",
            "Rating": rating.get_text(strip=True) if rating else "N/A"
        })

driver.quit()

# Save to CSV
df = pd.DataFrame(hotels)
df.to_csv("goibibo_darjeeling_hotels.csv", index=False)
print(f"✅ {len(hotels)} hotels scraped and saved to 'goibibo_darjeeling_hotels.csv'")