import os
import json
from datetime import datetime
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import logging
import sys
import urllib.parse


class FacebookAdsScraper:
    def __init__(self):
        # Credentials
        self.email = "gatthewarshubham145@gmail.com"
        self.password = "Shubham@2004"
        
        # Setup directories
        self.base_dir = os.path.join(os.getcwd(), 'facebook_ads_data')
        self.images_dir = os.path.join(self.base_dir, 'images')
        
        for directory in [self.base_dir, self.images_dir]:
            os.makedirs(directory, exist_ok=True)
        
        self.setup_logging()
        self.options = self.configure_chrome_options()

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('fb_scraper.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )

    def configure_chrome_options(self):
        options = webdriver.ChromeOptions()
        options.add_argument('--start-maximized')
        options.add_argument('--disable-notifications')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-sandbox')
        options.add_argument('--headless')  # Optional for running without UI
        return options

    def initialize_driver(self):
        try:
            logging.info("Initializing Chrome driver...")
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=self.options)
            return driver
        except Exception as e:
            logging.error(f"Failed to initialize Chrome driver: {str(e)}")
            return None

    def login(self, driver):
        try:
            logging.info("Logging into Facebook...")
            driver.get("https://www.facebook.com")
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.ID, "email"))
            ).send_keys(self.email)
            driver.find_element(By.ID, "pass").send_keys(self.password)
            driver.find_element(By.NAME, "login").click()
            time.sleep(5)
            return True
        except Exception as e:
            logging.error(f"Login failed: {str(e)}")
            return False

    def navigate_to_ad_library(self, driver, search_term):
        try:
            logging.info("Navigating to Facebook Ad Library...")
            search_url = f"https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country=ALL&q={urllib.parse.quote(search_term)}"
            driver.get(search_url)
            time.sleep(5)
            return True
        except Exception as e:
            logging.error(f"Failed to navigate to Ad Library: {str(e)}")
            return False

    def extract_image_urls(self, driver):
        try:
            logging.info("Extracting image URLs...")
            image_elements = driver.find_elements(By.TAG_NAME, 'img')
            image_urls = [img.get_attribute('src') for img in image_elements if img.get_attribute('src')]

            if image_urls:
                logging.info(f"Found {len(image_urls)} image URLs.")
                # Save image URLs to a JSON file
                output_file = os.path.join(self.images_dir, 'images_url.json')
                with open(output_file, 'w') as json_file:
                    json.dump({'images': image_urls}, json_file, indent=4)
                logging.info(f"Image URLs saved to {output_file}")
            else:
                logging.warning("No image URLs found.")

        except Exception as e:
            logging.error(f"Error extracting image URLs: {str(e)}")

    def scrape_ads(self, search_term):
        driver = self.initialize_driver()
        if not driver:
            return
        
        try:
            if not self.login(driver):
                raise Exception("Login failed.")

            if not self.navigate_to_ad_library(driver, search_term):
                raise Exception("Navigation to Ad Library failed.")

            self.extract_image_urls(driver)

        except Exception as e:
            logging.error(f"Error during scraping: {str(e)}")
        finally:
            driver.quit()

def main():
    try:
        scraper = FacebookAdsScraper()
        search_term = input("\nEnter search term (e.g., Walmart): ").strip()
        if not search_term:
            print("Please enter a valid search term.")
            return

        logging.info(f"Starting scrape for '{search_term}'...")
        scraper.scrape_ads(search_term)
    except Exception as e:
        logging.error(f"Error in main function: {str(e)}")

if __name__ == "__main__":
    main()
