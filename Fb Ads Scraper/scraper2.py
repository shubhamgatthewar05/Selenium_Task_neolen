from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import pandas as pd
import time
import os
from datetime import datetime

class FacebookAdsLibraryScraper:
    def __init__(self, headless=False):  # Changed default to False for better debugging
        """Initialize the scraper with browser options."""
        self.options = webdriver.ChromeOptions()
        if headless:
            self.options.add_argument('--headless=new')  # Updated headless mode
        
        # Add arguments to handle WebGL errors
        self.options.add_argument('--disable-gpu')
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')
        self.options.add_argument('--disable-software-rasterizer')
        self.options.add_experimental_option('excludeSwitches', ['enable-logging'])  # Suppress console logs
        
        # Files setup
        self.output_file = 'fb_ads_data.csv'
        self.log_file = 'scraping_log.txt'
        
    def setup_driver(self):
        """Set up and return a new webdriver instance."""
        return webdriver.Chrome(options=self.options)
    
    def scrape_ads_data(self, domain):
        """Scrape ads data for a specific domain."""
        driver = self.setup_driver()
        data = {'domain': domain, 'ads_count': 0, 'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        
        try:
            # Construct the URL with updated parameters
            url = f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=ALL&view_all_page_id=null&search_type=keyword_unordered&q={domain}"
            
            print(f"\nAccessing {url}")
            driver.get(url)
            
            # Wait longer for initial load
            time.sleep(10)
            
            # Try multiple selectors for the results count
            selectors = [
                "//div[contains(@class, 'x1yztbdb')]//span[contains(text(), 'results')]",
                "//div[contains(@class, 'x1yztbdb')]//span[contains(text(), 'result')]",
                "//span[contains(text(), 'Showing')]",
                "//div[contains(@class, 'x1av1boa')]//span[contains(text(), 'results')]"
            ]
            
            results_text = None
            for selector in selectors:
                try:
                    element = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                    results_text = element.text
                    break
                except:
                    continue
            
            if results_text:
                print(f"Found results text: {results_text}")
                # Extract number from text like "Showing 1,234 results" or "1,234 results"
                import re
                numbers = re.findall(r'\d+(?:,\d+)?', results_text)
                if numbers:
                    data['ads_count'] = int(numbers[0].replace(',', ''))
            else:
                print(f"No results found for {domain}")
                
        except Exception as e:
            print(f"Error scraping {domain}: {str(e)}")
            self.log_error(f"Error scraping {domain}: {str(e)}")
            
        finally:
            print(f"Scraped {data['ads_count']} ads for {domain}")
            driver.quit()
            
        return data
    
    def export_to_csv(self, data):
        """Export scraped data to CSV."""
        try:
            df = pd.DataFrame([data])
            if not os.path.exists(self.output_file):
                df.to_csv(self.output_file, index=False)
            else:
                df.to_csv(self.output_file, mode='a', header=False, index=False)
        except Exception as e:
            self.log_error(f"Error exporting data: {str(e)}")

    def log_error(self, error_message):
        """Log errors to file."""
        try:
            with open(self.log_file, 'a') as file:
                file.write(f"{datetime.now()}: {error_message}\n")
        except Exception as e:
            print(f"Error writing to log file: {str(e)}")

    def run(self, domains, delay_between_requests=15):  # Increased delay
        """Main method to run the scraper."""
        print(f"Starting to scrape {len(domains)} domains")
        
        for domain in domains:
            print(f"\nScraping ads for {domain}...")
            data = self.scrape_ads_data(domain)
            self.export_to_csv(data)
            time.sleep(delay_between_requests)  # Longer delay between requests
            
        print("\nScraping completed!")

# Usage example
if __name__ == "__main__":
    # Test with a smaller set of domains first
    test_domains = [
        "nike.com",
        "newbalance.com"
    ]
    
    # Initialize and run the scraper
    scraper = FacebookAdsLibraryScraper(headless=False)  # Set to False to see the browser
    scraper.run(test_domains, delay_between_requests=15)