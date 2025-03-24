from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.keys import Keys
import pandas as pd
import requests
import json
import time
import os
from datetime import datetime
import logging
from PIL import Image
from io import BytesIO

class FacebookAdsDetailedScraper:
    def __init__(self, email, password, headless=False):
        """Initialize the scraper with login credentials and browser options."""
        self.email = email
        self.password = password
        
        self.options = webdriver.ChromeOptions()
        self.options = webdriver.ChromeOptions()
        if headless:
            self.options.add_argument('--headless=new')
        self.options.add_argument('--disable-gpu')
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')
        self.options.add_argument('--window-size=1920,1080')
        self.options.add_argument('--disable-notifications')
        self.options.add_argument('--disable-webgl')
        self.options.add_argument('--disable-software-rasterizer')
        self.options.add_argument('--enable-unsafe-swiftshader')
        self.options.add_argument('--log-level=3')
        self.options.add_argument('--disable-logging')
        
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

    def login_to_facebook(self, driver):
        """Log in to Facebook."""
        try:
            driver.get("https://www.facebook.com")
            time.sleep(3)
            
            # Handle cookie consent if present
            try:
                cookie_button = driver.find_element(By.XPATH, "//button[contains(string(), 'Allow') or contains(string(), 'Accept')]")
                cookie_button.click()
                time.sleep(1)
            except:
                pass
            
            # Enter email
            email_field = driver.find_element(By.ID, "email")
            email_field.send_keys(self.email)
            
            # Enter password
            password_field = driver.find_element(By.ID, "pass")
            password_field.send_keys(self.password)
            
            # Click login button
            login_button = driver.find_element(By.NAME, "login")
            login_button.click()
            
            # Wait for login to complete
            time.sleep(5)
            
            return True
        except Exception as e:
            logging.error(f"Login failed: {str(e)}")
            return False

    def extract_ad_details(self, ad_element):
        """Extract all available details from an ad element."""
        ad_data = {
            'scrape_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'ad_id': '',
            'ad_copy': '',
            'start_date': '',
            'end_date': '',
            'platform': '',
            'impressions': '',
            'spend_range': '',
            'page_name': '',
            'image_paths': []
        }
        
        try:
            # Extract ad copy
            ad_copy_elements = ad_element.find_elements(By.CSS_SELECTOR, 'div[data-testid="ad_text"]')
            if ad_copy_elements:
                ad_data['ad_copy'] = ad_copy_elements[0].text.strip()
            
            # Extract dates
            date_elements = ad_element.find_elements(By.CSS_SELECTOR, 'span[data-testid="ad_date"]')
            if date_elements:
                date_text = date_elements[0].text
                if ' - ' in date_text:
                    start, end = date_text.split(' - ')
                    ad_data['start_date'] = start.strip()
                    ad_data['end_date'] = end.strip()
            
            # Extract spend range
            spend_elements = ad_element.find_elements(By.CSS_SELECTOR, 'div[data-testid="ad_spend"]')
            if spend_elements:
                ad_data['spend_range'] = spend_elements[0].text.strip()
            
            # Extract page name
            page_elements = ad_element.find_elements(By.CSS_SELECTOR, 'a[data-testid="ad_page_name"]')
            if page_elements:
                ad_data['page_name'] = page_elements[0].text.strip()
            
            # Extract platforms
            platform_elements = ad_element.find_elements(By.CSS_SELECTOR, 'div[data-testid="ad_platforms"]')
            if platform_elements:
                ad_data['platform'] = platform_elements[0].text.strip()
            
            # Extract images
            image_elements = ad_element.find_elements(By.CSS_SELECTOR, 'img[data-testid="ad_image"]')
            for img in image_elements:
                img_url = img.get_attribute('src')
                if img_url:
                    ad_data['image_paths'].append(img_url)
            
            return ad_data
        except Exception as e:
            logging.error(f"Error extracting ad details: {str(e)}")
            return None

    def scroll_and_load_ads(self, driver, max_scrolls=20):
        """Scroll the page to load more ads."""
        ad_elements = set()
        scroll_count = 0
        while scroll_count < max_scrolls:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(5)  # Increased wait time for content to load
            current_ads = driver.find_elements(By.CSS_SELECTOR, 'div[role="article"]')  # Adjusted for dynamic elements
            new_ads_count = len(set(current_ads) - ad_elements)
            ad_elements.update(current_ads)
            scroll_count += 1 if new_ads_count == 0 else 0
            if scroll_count >= 3:  # No new ads loaded after 3 scrolls
                break
        return list(ad_elements)


    def scrape_domain(self, domain):
        """Scrape all ads for a specific domain."""
        driver = webdriver.Chrome(options=self.options)
        ads_data = []
        
        try:
            # Login first
            if not self.login_to_facebook(driver):
                raise Exception("Failed to login to Facebook")
            
            # Navigate to Ad Library
            url = f"https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country=ALL&q={domain}&sort_data[direction]=desc&sort_data[mode]=relevancy_monthly_grouped&search_type=keyword_unordered&media_type=all"
            driver.get(url)
            time.sleep(5)
            
            # Load ads by scrolling
            ad_elements = self.scroll_and_load_ads(driver)
            logging.info(f"Found {len(ad_elements)} ads for {domain}")
            
            # Extract data from each ad
            for ad_element in ad_elements:
                ad_data = self.extract_ad_details(ad_element)
                if ad_data:
                    ad_data['domain'] = domain
                    ads_data.append(ad_data)
            
            # Save the collected data
            if ads_data:
                self.save_ad_data(ads_data, domain)
                
        except Exception as e:
            logging.error(f"Error scraping domain {domain}: {str(e)}")
        finally:
            driver.quit()
        
        return len(ads_data)

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

    def run(self, input_file, delay_between_domains=10):
        """Main method to run the scraper."""
        try:
            # Read domains from CSV file
            domains = pd.read_csv(input_file)['shop_domain'].tolist()
            
            total_ads = 0
            for domain in domains:
                logging.info(f"Starting scrape for {domain}")
                print(f"Scraping ads for {domain}...")
                
                num_ads = self.scrape_domain(domain)
                total_ads += num_ads
                print(f"Scraped {num_ads} ads for {domain}")
                
                time.sleep(delay_between_domains)
            
            print(f"Scraping completed! Total ads scraped: {total_ads}")
            print("Check the facebook_ads_data directory for results.")
            
        except Exception as e:
            logging.error(f"Error in main scraper execution: {str(e)}")
            print(f"An error occurred. Check fb_ads_scraper.log for details.")

if __name__ == "__main__":
    #credientials 
    FB_EMAIL = "gatthewarshubham145@gmail.com"
    FB_PASSWORD = "Shubham@2004"
    
    scraper = FacebookAdsDetailedScraper(
        email=FB_EMAIL,
        password=FB_PASSWORD,
        headless=False
    )
    scraper.run("shop_domains.csv", delay_between_domains=10)