from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import json
import time
import datetime
import logging
from typing import List, Dict
import os
import random
import urllib.parse

class FacebookAdScraper:
    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password
        self.base_url = "https://www.facebook.com/ads/library/"
        self.setup_logging()
        self.setup_driver()

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('fb_scraper.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def setup_driver(self):
        """Setup Chrome driver with necessary options"""
        options = Options()
        options.add_argument('--disable-notifications')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--start-maximized')
        options.add_argument('--disable-gpu')
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.wait = WebDriverWait(self.driver, 20)
        
        # Additional anti-detection measures
        self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            '''
        })

    def random_sleep(self, min_seconds=2, max_seconds=5):
        time.sleep(random.uniform(min_seconds, max_seconds))

    def login(self) -> bool:
        """Login to Facebook"""
        try:
            self.driver.get("https://www.facebook.com")
            self.random_sleep(3, 5)
            
            # Enter email
            email_field = self.wait.until(
                EC.presence_of_element_located((By.ID, "email"))
            )
            email_field.send_keys(self.email)
            
            # Enter password
            password_field = self.driver.find_element(By.ID, "pass")
            password_field.send_keys(self.password)
            
            # Click login button
            login_button = self.driver.find_element(By.NAME, "login")
            login_button.click()
            
            # Wait for login to complete
            self.random_sleep(5, 7)
            
            # Verify login success
            return "login" not in self.driver.current_url
            
        except Exception as e:
            self.logger.error(f"Login failed: {str(e)}")
            return False

    def search_company(self, company_name: str):
        """Search for company ads using direct URL navigation"""
        try:
            # Encode company name for URL
            encoded_company = urllib.parse.quote(company_name)
            search_url = f"{self.base_url}?active_status=all&ad_type=all&country=ALL&q={encoded_company}&sort_data[direction]=desc&sort_data[mode]=relevancy_monthly_grouped"
            
            self.logger.info(f"Navigating to search URL: {search_url}")
            self.driver.get(search_url)
            self.random_sleep(5, 7)
            
            # Wait for page load
            self.wait.until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Try different ways to verify results are loaded
            result_found = False
            self.logger.info("Checking for ad results...")
            
            selectors = [
                "div[role='article']",
                "div[data-testid='ad_card']",
                "div[aria-label*='advertisement']",
                "div[class*='_7jvw']",  # Common Facebook ad container class
                "div[class*='x1yztbdb']"  # Another common ad class
            ]
            
            for selector in selectors:
                try:
                    elements = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
                    )
                    if elements:
                        result_found = True
                        self.logger.info(f"Found {len(elements)} elements with selector: {selector}")
                        break
                except:
                    continue
            
            if not result_found:
                # Try scrolling to trigger content load
                self.logger.info("No results found initially, trying to scroll...")
                for _ in range(3):
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    self.random_sleep(2, 3)
                    
                    for selector in selectors:
                        try:
                            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                            if elements:
                                result_found = True
                                self.logger.info(f"Found {len(elements)} elements after scrolling")
                                break
                        except:
                            continue
                    
                    if result_found:
                        break
            
            if not result_found:
                raise Exception("No ad results found after multiple attempts")
            
        except Exception as e:
            self.logger.error(f"Search failed: {str(e)}")
            raise

    def extract_ad_data(self, ad_element) -> Dict:
        """Extract data from individual ad element with enhanced error handling"""
        try:
            # Wait for ad element to be fully loaded
            WebDriverWait(self.driver, 10).until(
                EC.visibility_of(ad_element)
            )
            
            # Scroll element into view
            self.driver.execute_script("arguments[0].scrollIntoView(true);", ad_element)
            self.random_sleep(1, 2)
            
            ad_data = {
                "ad_id": ad_element.get_attribute("id") or "Unknown",
                "scrape_date": datetime.datetime.now().isoformat(),
                "text_content": "",
                "start_date": "Unknown",
                "platform": [],
                "metadata": {},
                "media_urls": []
            }
            
            # Extract text content
            try:
                ad_data["text_content"] = ad_element.text
            except:
                self.logger.warning("Failed to extract text content")
            
            # Extract start date
            try:
                date_element = ad_element.find_element(By.XPATH, ".//span[contains(text(), 'Started running on')]")
                ad_data["start_date"] = date_element.text
            except:
                self.logger.warning("Failed to extract start date")
            
            # Extract media URLs
            try:
                images = ad_element.find_elements(By.TAG_NAME, "img")
                videos = ad_element.find_elements(By.TAG_NAME, "video")
                
                ad_data["media_urls"].extend([img.get_attribute("src") for img in images if img.get_attribute("src")])
                ad_data["media_urls"].extend([video.get_attribute("src") for video in videos if video.get_attribute("src")])
            except:
                self.logger.warning("Failed to extract media URLs")
            
            return ad_data
            
        except Exception as e:
            self.logger.error(f"Error extracting ad data: {str(e)}")
            return None

    def scrape_ads(self, company_name: str, num_ads: int = 10) -> List[Dict]:
        """Main method to scrape ads"""
        ads_data = []
        try:
            if not self.login():
                raise Exception("Failed to login")

            self.search_company(company_name)
            
            # Initialize scroll position
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            
            while len(ads_data) < num_ads:
                # Find all ad elements currently visible
                ad_elements = self.driver.find_elements(By.CSS_SELECTOR, "div[role='article']")
                
                for ad_element in ad_elements:
                    if len(ads_data) >= num_ads:
                        break
                        
                    ad_data = self.extract_ad_data(ad_element)
                    if ad_data and ad_data not in ads_data:  # Avoid duplicates
                        ads_data.append(ad_data)
                        self.logger.info(f"Scraped ad {len(ads_data)} of {num_ads}")
                
                if len(ads_data) >= num_ads:
                    break
                    
                # Scroll down to load more ads
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                self.random_sleep(2, 3)
                
                # Check if we've reached the bottom
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height

        except Exception as e:
            self.logger.error(f"Error during scraping: {str(e)}")
            raise
        finally:
            self.driver.quit()

        return ads_data

    def save_to_json(self, data: List[Dict], filename: str):
        """Save scraped data to JSON file"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.logger.info(f"Data saved to {filename}")
        except Exception as e:
            self.logger.error(f"Error saving to JSON: {str(e)}")

def main():
   
    email = "gatthewarshubham145@gmail.com"
    password = "Shubham@2004"
    company_name = "Flipkart"  # Company to search for
    
    try:
        scraper = FacebookAdScraper(email, password)
        ads_data = scraper.scrape_ads(company_name, num_ads=10)
        
        if ads_data:
            output_file = f"facebook_ads_{company_name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            scraper.save_to_json(ads_data, output_file)
            print(f"Successfully scraped {len(ads_data)} ads and saved to {output_file}")
        else:
            print("No ads were scraped")
            
    except Exception as e:
        print(f"Script failed with error: {str(e)}")
        logging.error(f"Script failed with error: {str(e)}")

if __name__ == "__main__":
    main()