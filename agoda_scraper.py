from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as seleniumEC
from selenium.webdriver.common.by import By
import time
import pandas as pd

def scrape_and_save():
    url = "https://www.agoda.com/en-in/search?guid=ac34b805-fbbb-4a54-91f6-72bd44251297&asq=oSBZUdCJkTqIcAJrG1AX8Jufa9Vwpz6XltTHq4n%2B9gNpSLc%2BT%2BpB%2F8FnmmA8sOyAJ0WZY5hpLWEr%2Fk8qr78gW4DMS7e7llLtqq76yKsoLJ2OoQ3gw8ln%2FUAwfEcSpHO4IoT8r2EKxXsqX%2FNiA5fxsgqQMycviD3CIWSJVwpQ8sqLB7kVtS1F64bq7yiJpY541pwsBzifP5NpR6wrJ1u54kHb%2BKC2e3zym6tmyvlzCzM%3D&city=10863&tick=638881978745&locale=en-in&ckuid=0782016a-40d3-4e7a-86a4-8cab9dacec41&prid=0&gclid=Cj0KCQjw-NfDBhDyARIsAD-ILeBXva5TJhq-jGK3Si0BOfvtLo82iIstmv4-XMoqfU56Mshxz_UezUkaAhwMEALw_wcB&currency=INR&correlationId=55168ae7-8bc1-4224-a8eb-86ba246be729&analyticsSessionId=-1950121884218971931&pageTypeId=1&realLanguageId=15&languageId=1&origin=IN&stateCode=WB&cid=1922885&tag=6f147157-60b8-459f-af1a-9935d44970e9&userId=0782016a-40d3-4e7a-86a4-8cab9dacec41&whitelabelid=1&loginLvl=0&storefrontId=3&currencyId=27&currencyCode=INR&htmlLanguage=en-in&cultureInfoName=en-in&machineName=sg-pc-6h-acm-web-user-8697c4cd7c-gmgqx&trafficGroupId=5&trafficSubGroupId=122&aid=82361&useFullPageLogin=true&cttp=4&isRealUser=true&mode=production&browserFamily=Chrome&cdnDomain=agoda.net&checkIn=2025-08-12&checkOut=2025-08-13&rooms=1&adults=2&children=0&priceCur=INR&los=1&textToSearch=Darjeeling&travellerType=1&familyMode=off&ds=cgN73pCK5wrspJ7h&productType=-1"
    driver = webdriver.Firefox()
    driver.get(url)
    WebDriverWait(driver, 10).until(seleniumEC.presence_of_all_elements_located((By.CSS_SELECTOR, 'li[data-selenium="hotel-item"]')))
    response = ""
    hotels = set()
    iterations = 8
    while iterations > 0:
        try:
            soupResponse = BeautifulSoup(driver.page_source, "html.parser")
            hasAdded = True
            while hasAdded:
                hasAdded = False
                for hotel in soupResponse.select('li[data-selenium="hotel-item"]'):
                    if hotel not in hotels:
                        hotels.add(hotel)
                        response += str(hotel)
                        hasAdded = True
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight* 0.75);")
                time.sleep(3)
            load_more_res_elements = driver.find_elements(By.CSS_SELECTOR, 'button[data-selenium="pagination-next-btn"]')
            if load_more_res_elements:
                load_more_res_elements[0].click()
            else:
                break
            time.sleep(5)
            iterations -= 1
        except Exception as e:
            print(e)
            break
    driver.close()

    # Save raw HTML for reference
    with open("unstructuredData_agoda.html", "w", encoding="utf-8") as f:
        f.write(response)

    # Now structure the data and save to CSV
    soup = BeautifulSoup(response, "html.parser")
    hotels_data = []
    for card in soup.select('li[data-selenium="hotel-item"]'):
        name = card.select_one('[data-selenium="hotel-name"]')
        price = card.select_one('[data-selenium="hotel-price"]')
        rating = card.select_one('[data-selenium="review-score"]')
        hotels_data.append({
            "name": name.get_text(strip=True) if name else "",
            "price": price.get_text(strip=True) if price else "",
            "rating": rating.get_text(strip=True) if rating else ""
        })
    df = pd.DataFrame(hotels_data)
    df.to_csv("agoda_hotels_structured.csv", index=False, encoding="utf-8")
    print(f"Saved {len(hotels_data)} hotels to agoda_hotels_structured.csv")

if __name__ == "__main__":
    scrape_and_save()