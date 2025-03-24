from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import json
import time
import random
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Setup Chrome options
chrome_options = Options()
chrome_options.add_argument("--headless")  # Run in headless mode
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--enable-unsafe-swiftshader")  # Address WebGL issue
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")  # Anti-detection

# Initialize the WebDriver
try:
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    logging.info("WebDriver initialized successfully")
except Exception as e:
    logging.error(f"Failed to initialize WebDriver: {e}")
    exit(1)

def scrape_facebook_ads(search_query="example"):
    try:
        # Navigate to the Facebook Ads Library
        url = f"https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country=ALL&q={search_query}&sort_data[direction]=desc&sort_data[mode]=relevancy_monthly_grouped&search_type=keyword_unordered&media_type=all"
        driver.get(url)
        logging.info(f"Navigated to URL: {url}")
        
        # Wait for ads to load
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div._99s5"))
        )
        logging.info("Ad containers detected")
        
        # Scroll to load more ads
        for _ in range(3):  # Scroll 3 times to ensure 10+ ads load
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(random.uniform(2, 4))  # Random delay to mimic human behavior
        
        # Find ad containers (limit to top 10)
        ad_elements = driver.find_elements(By.CSS_SELECTOR, "div._99s5")[:10]
        logging.info(f"Found {len(ad_elements)} ad elements")
        
        ads_data = []
        
        for i, ad in enumerate(ad_elements, 1):
            ad_dict = {}
            logging.info(f"Scraping ad {i}")
            
            try:
                ad_id_elem = ad.find_element(By.XPATH, ".//span[contains(text(), 'ID:')]")
                ad_dict["Library_ID"] = ad_id_elem.text.replace("ID: ", "").strip()
            except:
                ad_dict["Library_ID"] = "N/A"
            
            try:
                start_date_elem = ad.find_element(By.XPATH, ".//span[contains(text(), 'Started running on')]")
                ad_dict["Started_Running_On"] = start_date_elem.text.replace("Started running on ", "").strip()
            except:
                ad_dict["Started_Running_On"] = "N/A"
            
            try:
                platform_elem = ad.find_element(By.XPATH, ".//div[contains(text(), 'Platforms:')]")
                ad_dict["Platform"] = platform_elem.text.replace("Platforms: ", "").strip()
            except:
                ad_dict["Platform"] = "N/A"
            
            try:
                metadata_elem = ad.find_element(By.XPATH, ".//div[contains(@class, '_9cfz')]")
                ad_dict["Metadata"] = metadata_elem.text.strip()
            except:
                ad_dict["Metadata"] = "N/A"
            
            try:
                text_elem = ad.find_element(By.XPATH, ".//div[contains(@class, '_4ik4 _4ik5')]")
                ad_dict["Text"] = text_elem.text.strip()
            except:
                ad_dict["Text"] = "N/A"
            
            try:
                media_elem = ad.find_element(By.XPATH, ".//img | .//video")
                if "img" in media_elem.tag_name:
                    ad_dict["Image_or_Video"] = media_elem.get_attribute("src")
                elif "video" in media_elem.tag_name:
                    ad_dict["Image_or_Video"] = media_elem.get_attribute("src")
                else:
                    ad_dict["Image_or_Video"] = "N/A"
            except:
                ad_dict["Image_or_Video"] = "N/A"
            
            ads_data.append(ad_dict)
        
        return ads_data
    
    except Exception as e:
        logging.error(f"Error scraping ads: {e}")
        return []
    
    finally:
        driver.quit()
        logging.info("WebDriver closed")

def save_to_json(data, filename="facebook_ads.json"):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    logging.info(f"Data saved to {filename}")

if __name__ == "__main__":
    search_term = "FlipKart"  # Replace with your desired search term
    ads = scrape_facebook_ads(search_term)
    
    if ads:
        save_to_json(ads)
    else:
        logging.warning("No ads scraped.")