from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import pandas as pd
import requests
import json
import time
import os
from datetime import datetime
import urllib.parse
import re
import logging
from PIL import Image
from io import BytesIO

class FacebookAdsDetailedScraper:
    def __init__(self, headless=False):
        """Initialize the scraper with browser options and setup directories."""
        self.options = webdriver.ChromeOptions()
        if headless:
            self.options.add_argument('--headless')
        self.options.add_argument('--disable-gpu')
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')
        self.options.add_argument('--window-size=1920,1080')
        
        # Setup directories
        self.base_dir = 'facebook_ads_data'
        self.images_dir = os.path.join(self.base_dir, 'images')
        self.data_dir = os.path.join(self.base_dir, 'data')
        self.setup_directories()
        
        # Setup logging
        logging.basicConfig(
            filename='fb_ads_scraper.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
    def setup_directories(self):
        """Create necessary directories if they don't exist."""
        for directory in [self.base_dir, self.images_dir, self.data_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)

    def setup_driver(self):
        """Set up and return a new webdriver instance."""
        return webdriver.Chrome(options=self.options)

    def wait_for_element(self, driver, selector, by=By.CSS_SELECTOR, timeout=10):
        """Wait for an element to be present and return it."""
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, selector))
        )

    def download_image(self, url, domain, ad_id):
        """Download and save image with error handling."""
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                img = Image.open(BytesIO(response.content))
                filename = f"{domain}_{ad_id}_{int(time.time())}.jpg"
                filepath = os.path.join(self.images_dir, filename)
                img.save(filepath)
                return filepath
        except Exception as e:
            logging.error(f"Error downloading image: {str(e)}")
            return None

    def extract_ad_details(self, ad_element, domain):
        """Extract all available details from an ad element."""
        try:
            ad_data = {
                'domain': domain,
                'scrape_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'ad_id': '',
                'status': '',
                'start_date': '',
                'end_date': '',
                'ad_copy': '',
                'platform': '',
                'impressions': '',
                'spend_range': '',
                'currency': '',
                'page_name': '',
                'page_id': '',
                'image_paths': [],
                'cta_button': '',
                'languages': '',
                'countries': ''
            }

            # Extract ad ID from URL or element
            try:
                ad_id_elem = ad_element.find_element(By.CSS_SELECTOR, "[data-ad-id]")
                ad_data['ad_id'] = ad_id_elem.get_attribute('data-ad-id')
            except:
                logging.warning("Could not extract ad ID")

            # Extract ad copy
            try:
                ad_copy_elem = ad_element.find_element(By.CSS_SELECTOR, "div[class*='_7jyr']")
                ad_data['ad_copy'] = ad_copy_elem.text.strip()
            except:
                logging.warning("Could not extract ad copy")

            # Extract dates
            try:
                dates_elem = ad_element.find_element(By.CSS_SELECTOR, "span[class*='_7jys']")
                dates_text = dates_elem.text
                if ' - ' in dates_text:
                    start, end = dates_text.split(' - ')
                    ad_data['start_date'] = start.strip()
                    ad_data['end_date'] = end.strip()
            except:
                logging.warning("Could not extract dates")

            # Extract images
            try:
                image_elements = ad_element.find_elements(By.CSS_SELECTOR, "img[class*='_7jyp']")
                for img in image_elements:
                    img_url = img.get_attribute('src')
                    if img_url:
                        image_path = self.download_image(img_url, domain, ad_data['ad_id'])
                        if image_path:
                            ad_data['image_paths'].append(image_path)
            except:
                logging.warning("Could not extract images")

            # Extract platform distribution
            try:
                platform_elem = ad_element.find_element(By.CSS_SELECTOR, "div[class*='_7jyt']")
                ad_data['platform'] = platform_elem.text.strip()
            except:
                logging.warning("Could not extract platform distribution")

            # Extract spend information
            try:
                spend_elem = ad_element.find_element(By.CSS_SELECTOR, "div[class*='_7jyu']")
                ad_data['spend_range'] = spend_elem.text.strip()
            except:
                logging.warning("Could not extract spend information")

            # Extract page information
            try:
                page_elem = ad_element.find_element(By.CSS_SELECTOR, "a[class*='_231w']")
                ad_data['page_name'] = page_elem.text.strip()
                ad_data['page_id'] = page_elem.get_attribute('href').split('/')[-1]
            except:
                logging.warning("Could not extract page information")

            return ad_data
        except Exception as e:
            logging.error(f"Error extracting ad details: {str(e)}")
            return None

    def scroll_to_load_more(self, driver, max_scrolls=10):
        """Scroll the page to load more ads."""
        last_height = driver.execute_script("return document.body.scrollHeight")
        scrolls = 0
        
        while scrolls < max_scrolls:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            new_height = driver.execute_script("return document.body.scrollHeight")
            
            if new_height == last_height:
                break
                
            last_height = new_height
            scrolls += 1

    def save_ad_data(self, ads_data, domain):
        """Save the collected ad data to CSV and JSON formats."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save as CSV
        csv_filename = os.path.join(self.data_dir, f'{domain}_ads_{timestamp}.csv')
        pd.DataFrame(ads_data).to_csv(csv_filename, index=False)
        
        # Save as JSON
        json_filename = os.path.join(self.data_dir, f'{domain}_ads_{timestamp}.json')
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(ads_data, f, ensure_ascii=False, indent=4)

    def scrape_domain(self, domain):
        """Scrape all ads for a specific domain."""
        driver = self.setup_driver()
        ads_data = []
        
        try:
            url = f"https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country=ALL&q={domain}&sort_data[direction]=desc&sort_data[mode]=relevancy_monthly_grouped&search_type=keyword_unordered&media_type=all"
            driver.get(url)
            time.sleep(5)  # Initial load wait
            
            # Scroll to load more ads
            self.scroll_to_load_more(driver)
            
            # Find all ad elements
            ad_elements = driver.find_elements(By.CSS_SELECTOR, "div[class*='_7jvm']")  # Adjust selector as needed
            
            for ad_element in ad_elements:
                ad_data = self.extract_ad_details(ad_element, domain)
                if ad_data:
                    ads_data.append(ad_data)
                    logging.info(f"Successfully scraped ad {ad_data['ad_id']} for {domain}")
            
            # Save the collected data
            if ads_data:
                self.save_ad_data(ads_data, domain)
                logging.info(f"Successfully saved {len(ads_data)} ads for {domain}")
            
        except Exception as e:
            logging.error(f"Error scraping domain {domain}: {str(e)}")
        finally:
            driver.quit()
        
        return len(ads_data)

    def run(self, input_file, delay_between_domains=10):
        """Main method to run the scraper."""
        try:
            domains = pd.read_csv(input_file)['shop_domain'].tolist()
            
            for domain in domains:
                logging.info(f"Starting scrape for {domain}")
                print(f"Scraping ads for {domain}...")
                
                num_ads = self.scrape_domain(domain)
                print(f"Scraped {num_ads} ads for {domain}")
                
                time.sleep(delay_between_domains)
                
            print("Scraping completed! Check the facebook_ads_data directory for results.")
            
        except Exception as e:
            logging.error(f"Error in main scraper execution: {str(e)}")
            print(f"An error occurred. Check fb_ads_scraper.log for details.")

# Usage example
if __name__ == "__main__":
    scraper = FacebookAdsDetailedScraper(headless=False)
    scraper.run("shop_domain.csv", delay_between_domains=10)