from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import json
import time
import os
from datetime import datetime

class FacebookAdsScraper:
    def __init__(self):
        self.setup_chrome_options()
        self.results = []
        
    def setup_chrome_options(self):
        """Set up Chrome options for the scraper"""
        self.options = webdriver.ChromeOptions()
        self.options.add_argument('--disable-gpu')
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')
        self.options.add_argument('--window-size=1920,1080')
        self.options.add_argument('--disable-blink-features=AutomationControlled')
        self.options.add_argument('--disable-notifications')
        
        # Add user agent
        self.options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

    def create_driver(self):
        """Create and return a new webdriver instance"""
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=self.options)

    def wait_for_element(self, driver, selector, by=By.CSS_SELECTOR, timeout=10):
        """Wait for an element to be present"""
        try:
            element = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by, selector))
            )
            return element
        except TimeoutException:
            print(f"Timeout waiting for element: {selector}")
            return None

    def extract_ad_data(self, ad_element):
        """Extract data from a single ad element"""
        ad_data = {
            'ad_id': '',
            'ad_text': '',
            'advertiser': '',
            'status': '',
            'platform': '',
            'start_date': '',
            'demographics': '',
            'location': '',
            'impressions': '',
            'link': '',
            'scraped_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        try:
            # Extract ad text
            text_elements = ad_element.find_elements(By.CSS_SELECTOR, 'div[style*="white-space"]')
            if text_elements:
                ad_data['ad_text'] = text_elements[0].text.strip()

            # Extract advertiser name
            advertiser_element = ad_element.find_element(By.CSS_SELECTOR, 'a[role="link"]')
            if advertiser_element:
                ad_data['advertiser'] = advertiser_element.text.strip()

            # Extract status and dates
            status_elements = ad_element.find_elements(By.CSS_SELECTOR, 'span[style*="color"]')
            for element in status_elements:
                text = element.text.strip()
                if 'Active' in text or 'Inactive' in text:
                    ad_data['status'] = text
                elif 'Started running on' in text:
                    ad_data['start_date'] = text.replace('Started running on ', '')

            # Extract platform distribution
            platform_element = ad_element.find_element(By.CSS_SELECTOR, 'div[style*="display: flex"]')
            if platform_element:
                ad_data['platform'] = platform_element.text.strip()

            # Extract link if available
            link_elements = ad_element.find_elements(By.CSS_SELECTOR, 'a[href*="https"]')
            if link_elements:
                ad_data['link'] = link_elements[0].get_attribute('href')

        except Exception as e:
            print(f"Error extracting ad data: {str(e)}")

        return ad_data

    def scroll_page(self, driver, scroll_pause=2):
        """Scroll the page to load more content"""
        last_height = driver.execute_script("return document.body.scrollHeight")
        
        for _ in range(5):  # Scroll 5 times
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(scroll_pause)
            
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

    def scrape_domain(self, domain):
        """Scrape ads for a specific domain"""
        print(f"Starting to scrape ads for {domain}")
        driver = self.create_driver()
        
        try:
            # Construct and load URL
            url = f"https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country=ALL&q={domain}&sort_data[direction]=desc&sort_data[mode]=relevancy_monthly_grouped&search_type=keyword_unordered&media_type=all"
            driver.get(url)
            time.sleep(5)  # Initial load wait

            # Scroll to load more content
            self.scroll_page(driver)

            # Wait for ads container
            ads_container = self.wait_for_element(driver, 'div[role="main"]')
            if not ads_container:
                print(f"No ads container found for {domain}")
                return

            # Find all ad elements
            ad_elements = driver.find_elements(By.CSS_SELECTOR, 'div[role="article"]')
            print(f"Found {len(ad_elements)} ads for {domain}")

            # Extract data from each ad
            for ad_element in ad_elements:
                ad_data = self.extract_ad_data(ad_element)
                ad_data['domain'] = domain
                self.results.append(ad_data)
                print(f"Extracted data for ad from {domain}")

        except Exception as e:
            print(f"Error scraping {domain}: {str(e)}")
        finally:
            driver.quit()

    def save_results(self):
        """Save results to JSON file"""
        try:
            with open('results.json', 'w', encoding='utf-8') as f:
                json.dump(self.results, f, ensure_ascii=False, indent=4)
            print(f"Results saved to results.json - Total ads scraped: {len(self.results)}")
        except Exception as e:
            print(f"Error saving results: {str(e)}")

    def run(self, domains_file):
        """Run the scraper for all domains"""
        try:
            # Read domains from CSV
            df = pd.read_csv(domains_file)
            domains = df['shop_domain'].tolist()

            # Scrape each domain
            for domain in domains:
                self.scrape_domain(domain)
                time.sleep(5)  # Delay between domains

            # Save all results
            self.save_results()

        except Exception as e:
            print(f"Error in main execution: {str(e)}")

if __name__ == "__main__":
    scraper = FacebookAdsScraper()
    scraper.run('shop_domain.csv')