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
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import logging
import sys
import urllib.parse


class FacebookAdsScraper:
    def __init__(self):
        # Credentials
        self.email = ""
        self.password = "922"
        
        # Setup directories
        self.base_dir = os.path.join(os.getcwd(), 'facebook_ads_data')
        self.ads_dir = os.path.join(self.base_dir, 'ads_info')
        self.text_dir = os.path.join(self.base_dir, 'ads_text')
        
        for directory in [self.base_dir, self.ads_dir, self.text_dir]:
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
        options.add_argument('--headless')
        # Add these new options for better login handling
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-features=IsolateOrigins,site-per-process')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        return options



    def initialize_driver(self):
        try:
            logging.info("Initializing Chrome driver...")
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=self.options)
            # Add these commands for better automation detection bypass
            driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'
            })
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            return driver
        except Exception as e:
            logging.error(f"Failed to initialize Chrome driver: {str(e)}")
            return None



    def wait_for_element(self, driver, by, value, timeout=15):
        try:
            element = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except Exception as e:
            logging.debug(f"Wait for element failed: {str(e)}")
            return None



    def login(self, driver):
        try:
            logging.info("Starting login process...")
            # First, clear any existing cookies
            driver.delete_all_cookies()
            
            # Go to Facebook login page
            driver.get("https://www.facebook.com")
            time.sleep(3)

            # Handle cookie consent if present
            try:
                cookie_buttons = driver.find_elements(By.XPATH, 
                    "//button[contains(text(), 'Allow') or contains(text(), 'Accept') or contains(text(), 'OK')]")
                if cookie_buttons:
                    cookie_buttons[0].click()
                    time.sleep(2)
            except:
                logging.info("No cookie consent needed")

            # Enter email
            email_field = self.wait_for_element(driver, By.ID, "email")
            if not email_field:
                email_field = self.wait_for_element(driver, By.NAME, "email")
            if email_field:
                email_field.clear()
                email_field.send_keys(self.email)
                time.sleep(1)

            # Enter password
            password_field = self.wait_for_element(driver, By.ID, "pass")
            if not password_field:
                password_field = self.wait_for_element(driver, By.NAME, "pass")
            if password_field:
                password_field.clear()
                password_field.send_keys(self.password)
                time.sleep(1)

            # Click login button
            try:
                login_button = driver.find_element(By.NAME, "login")
                login_button.click()
            except:
                password_field.send_keys(Keys.RETURN)

            # Wait for login to complete
            time.sleep(5)

            # Verify login success by checking multiple indicators
            if self.verify_login(driver):
                logging.info("Login successful!")
                return True
            else:
                logging.error("Login verification failed")
                return False

        except Exception as e:
            logging.error(f"Login failed: {str(e)}")
            return False




    def verify_login(self, driver):
        """Verify login success using multiple methods"""
        try:
            # Wait a bit longer for the page to load completely
            time.sleep(5)
            
            # Check multiple indicators of successful login
            indicators = [
                # Check URL is not login page
                lambda: "login" not in driver.current_url.lower(),
                # Check for common elements present after login
                lambda: len(driver.find_elements(By.XPATH, "//div[@role='navigation']")) > 0,
                lambda: len(driver.find_elements(By.XPATH, "//div[@aria-label='Facebook']")) > 0
            ]
            
            return any(indicator() for indicator in indicators)
            
        except Exception as e:
            logging.error(f"Login verification error: {str(e)}")
            return False




    def navigate_to_ad_library(self, driver, search_term):
        try:
            logging.info("Navigating to Ad Library...")
            
            # Use the direct search URL with encoded search term
            encoded_search = urllib.parse.quote(search_term)
            search_url = f"https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country=ALL&view_all_page_id=all&sort_data[direction]=desc&sort_data[mode]=relevancy_monthly_grouped&search_type=keyword_unordered&media_type=all&q={encoded_search}"
            
            driver.get(search_url)
            time.sleep(5)

            # Check if we need to login again
            if self.check_and_handle_login(driver):
                time.sleep(3)

            # Wait for page load
            logging.info("Waiting for page to load completely...")
            self.wait_for_page_load(driver)

            # Verify we're on the correct page
            if not self.verify_ad_library_page(driver):
                logging.error("Failed to verify Ad Library page")
                return False

            return True

        except Exception as e:
            logging.error(f"Error navigating to Ad Library: {str(e)}")
            return False
        


    def verify_ad_library_page(self, driver):
        """Verify we're on the Ad Library page"""
        try:
            # Wait for any of these indicators
            indicators = [
                (By.XPATH, "//div[contains(text(), 'Ad Library')]"),
                (By.XPATH, "//div[contains(@aria-label, 'Ad Library')]"),
                (By.CSS_SELECTOR, '[data-testid="ad_library_page"]'),
                (By.CSS_SELECTOR, '[role="main"]')
            ]
            
            for by, selector in indicators:
                try:
                    element = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((by, selector))
                    )
                    if element:
                        return True
                except:
                    continue
                    
            return False
        except:
            return False
        



    def wait_for_page_load(self, driver):
        """Wait for page to load completely"""
        try:
            # Wait for page load complete
            WebDriverWait(driver, 30).until(
                lambda driver: driver.execute_script('return document.readyState') == 'complete'
            )
            
            # Additional wait for dynamic content
            time.sleep(5)
            
            # Scroll a bit to trigger content load
            driver.execute_script("window.scrollBy(0, 300);")
            time.sleep(2)
        except Exception as e:
            logging.warning(f"Page load wait warning: {str(e)}")




    def extract_ad_data(self, ad_container):
        """Enhanced ad data extraction with comprehensive selectors"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                ad_data = {
                    'scrape_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'ad_text': '',
                    'metadata': '',
                    'platform': '',
                    'start_date': '',
                    'id': '',
                    'company_name': '',
                    'image_url': '' 
                }
                
                driver = ad_container.parent
                driver.execute_script("arguments[0].scrollIntoView(true);", ad_container)
                time.sleep(1)
                
                # Ad Text Extraction
                text_selectors = [
                    '[data-testid="ad_text"]',
                    '[data-testid="ad_primary_text"]',
                    'div[role="article"] div[dir="auto"]',
                    '.x1cy8zhl div[dir="auto"]',
                    '.x1iorvi4 div[dir="auto"]',
                    '._7jyr',
                    '.xjkvuk6 div[dir="auto"]',
                    '.x1lliihq.xjkvuk6.x1cy8zhl'  # Added for more coverage
                ]
                for selector in text_selectors:
                    try:
                        elements = ad_container.find_elements(By.CSS_SELECTOR, selector)
                        texts = set()  # Prevent duplication
                        for elem in elements:
                            text = elem.text.strip()
                            if text and len(text) > 10 and text not in texts:
                                texts.add(text)
                        ad_data['ad_text'] = ' '.join(texts)
                        if ad_data['ad_text']:
                            break
                    except:
                        continue

                # Company Name
                company_selectors = [
                    'a[role="link"] span[dir="auto"]',
                    'h1[dir="auto"]',
                    '[data-testid="ad_page_name"]',
                    '.x1heor9g',
                    '._8jh2',
                    '.x1i10h78 span'  # Added for more accuracy
                ]
                for selector in company_selectors:
                    try:
                        element = ad_container.find_element(By.CSS_SELECTOR, selector)
                        if element and element.text:
                            ad_data['company_name'] = element.text.strip()
                            break
                    except:
                        continue

                # Image/Video URL
                media_selectors = [
                    'img[data-testid="ad_image"]',
                    'video[data-testid="ad_video"]',
                    'img[role="img"]',
                    '.x1ey2m1c img',
                    '.x1iorvi4 img',
                    '.x1ll5gia.x19kjcj4.xh8yej3',
                    'video.x1lliihq'  # Added for video support
                ]
                for selector in media_selectors:
                    try:
                        element = ad_container.find_element(By.CSS_SELECTOR, selector)
                        if element:
                            url = element.get_attribute('src')
                            if url:
                                ad_data['image_url'] = url
                                break
                    except:
                        continue

                # Platforms
                platform_selectors = [
                    '[data-testid="ad_platforms"]',
                    '[aria-label*="Platform"]',
                    'div[role="row"] span',
                    '.x1xmf6yo span',
                    '.x1lliihq span:contains("Platforms")'  # Added for explicit platform text
                ]
                platforms = set()
                for selector in platform_selectors:
                    try:
                        elements = ad_container.find_elements(By.CSS_SELECTOR, selector)
                        for elem in elements:
                            text = elem.text.lower()
                            if 'facebook' in text:
                                platforms.add('Facebook')
                            if 'instagram' in text:
                                platforms.add('Instagram')
                            if 'messenger' in text:
                                platforms.add('Messenger')
                            if 'whatsapp' in text:
                                platforms.add('WhatsApp')
                        if platforms:
                            ad_data['platform'] = ', '.join(platforms)
                            break
                    except:
                        continue

                # Start Date
                date_selectors = [
                    '[data-testid="ad_date"]',
                    'span:contains("Started running on")',
                    '.x1xmf6yo span:contains("Started")',
                    'span:contains("running on")',
                    '.x1lliihq span:contains("Started")'  # Added for more coverage
                ]
                for selector in date_selectors:
                    try:
                        element = ad_container.find_element(By.CSS_SELECTOR, selector)
                        if element and element.text:
                            date_text = element.text.strip()
                            if 'Started running on' in date_text:
                                ad_data['start_date'] = date_text.split('Started running on')[-1].strip()
                            else:
                                ad_data['start_date'] = date_text
                            break
                    except:
                        continue

                # Ad ID
                id_selectors = [
                    '[data-testid="ad_id"]',
                    'span:contains("ID:")',
                    'div:contains("ID:")',
                    '.xt0e3qv:contains("ID:")',
                    '.x8t9es0.xw23nyj.xo1l8bm span:contains("ID:")',
                    '.x1cy8zhl.x78zum5 span:contains("ID:")'  # Added for better ID capture
                ]
                for selector in id_selectors:
                    try:
                        element = ad_container.find_element(By.CSS_SELECTOR, selector)
                        if element and element.text:
                            text = element.text.strip()
                            if 'ID:' in text:
                                ad_data['id'] = text.split('ID:')[-1].strip()
                            elif text.isdigit():  # If it's just a number
                                ad_data['id'] = text
                            break
                    except:
                        continue

                # Metadata
                metadata_selectors = [
                    '[data-testid="ad_metadata"]',
                    '.x1vh85ih',
                    '.x8bgqxi.x1n2onr6',
                    '.x1lliihq.x1iorvi4',  # Added for more metadata
                    'div[role="row"]:not(:has(span:contains("Started")))'  # Exclude date info
                ]
                metadata_parts = []
                for selector in metadata_selectors:
                    try:
                        elements = ad_container.find_elements(By.CSS_SELECTOR, selector)
                        for elem in elements:
                            text = elem.text.strip()
                            if text and text not in ad_data['ad_text'] and 'Started running' not in text:
                                metadata_parts.append(text)
                        if metadata_parts:
                            ad_data['metadata'] = ' | '.join(metadata_parts)
                            break
                    except:
                        continue

                # Return if we have substantial data
                if ad_data['ad_text'] or ad_data['id'] or ad_data['start_date']:
                    return ad_data
                
                if attempt < max_retries - 1:
                    time.sleep(2)
                    
            except Exception as e:
                logging.error(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2)
        
        return None
    
    def check_and_handle_login(self, driver):
        """Check if we're redirected to login and handle it"""
        try:
            if "login" in driver.current_url.lower():
                logging.info("Detected login redirect, handling login...")
                return self.login(driver)
            return False
        except Exception as e:
            logging.error(f"Error checking login status: {str(e)}")
            return False

    def wait_for_search_results(self, driver):
        """Wait for search results to load"""
        try:
            # Wait for either ads to appear or no results message
            WebDriverWait(driver, 15).until(
                lambda x: len(x.find_elements(By.CSS_SELECTOR, '[data-testid="ad_library_preview"]')) > 0 or
                         len(x.find_elements(By.XPATH, "//*[contains(text(), 'No Ads Found')]")) > 0
            )
            time.sleep(3)  # Additional wait for content to load completely
        except:
            logging.warning("Timeout waiting for search results")


    def scrape_ads(self, search_term):
        driver = None
        try:
            driver = self.initialize_driver()
            if not driver:
                return 0

            if not self.login(driver):
                raise Exception("Failed to login to Facebook")

            if not self.navigate_to_ad_library(driver, search_term):
                raise Exception("Failed to navigate to Ad Library")

            time.sleep(5)
            ads_data = []
            seen_texts = set()  # For deduplication
            
            scroll_attempts = 0
            max_scroll_attempts = 15
            last_height = driver.execute_script("return document.body.scrollHeight")

            while len(ads_data) < 10 and scroll_attempts < max_scroll_attempts:
                ad_container_selectors = [
                    '.x1dr75xp.xh8yej3.x16md763',
                    '[data-testid="ad_container"]',
                    '[data-testid="ad_library_preview"]',
                    '._7jyg',
                    '.x1cy8zhl',
                    '.x1iorvi4'
                ]
                
                for selector in ad_container_selectors:
                    containers = driver.find_elements(By.CSS_SELECTOR, selector)
                    for container in containers[len(ads_data):]:
                        try:
                            driver.execute_script("arguments[0].scrollIntoView(true);", container)
                            time.sleep(1)
                            
                            ad_data = self.extract_ad_data(container)
                            if ad_data and ad_data['ad_text'] and ad_data['ad_text'] not in seen_texts:
                                seen_texts.add(ad_data['ad_text'])
                                ads_data.append(ad_data)
                                logging.info(f"Found ad {len(ads_data)}: ID {ad_data['id']}")
                                
                                if len(ads_data) >= 5:
                                    break
                        except Exception as e:
                            logging.debug(f"Error processing container: {str(e)}")
                            continue
                    
                    if len(ads_data) >= 5:
                        break
                
                if len(ads_data) < 5:
                    driver.execute_script("window.scrollBy(0, 500);")
                    time.sleep(2)
                    new_height = driver.execute_script("return document.body.scrollHeight")
                    if new_height == last_height:
                        scroll_attempts += 1
                    else:
                        last_height = new_height
                        scroll_attempts = 0

            if ads_data:
                self.save_data(ads_data, [ad['ad_text'] for ad in ads_data], search_term)
                return len(ads_data)
            else:
                logging.error("No unique ads found")
                return 0

        except Exception as e:
            logging.error(f"Error during scraping: {str(e)}")
            return 0
        finally:
            if driver:
                driver.quit()




    def save_data(self, ads_data, all_ad_text, search_term):
        """
        Save scraped ads data and text to files
        
        Parameters:
            ads_data (list): List of dictionaries containing ad information
            all_ad_text (list): List of ad text content
            search_term (str): Search term used to find the ads
        """
        try:
            # Create timestamp for unique filenames
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Save ads info as JSON
            ads_filename = os.path.join(
                self.ads_dir, 
                f'{search_term}_ads_{timestamp}.json'
            )
            with open(ads_filename, 'w', encoding='utf-8') as f:
                json.dump(ads_data, f, indent=4, ensure_ascii=False)
            
            # Save ad text as plain text
            text_filename = os.path.join(
                self.text_dir,
                f'{search_term}_text_{timestamp}.txt'
            )
            with open(text_filename, 'w', encoding='utf-8') as f:
                for i, text in enumerate(all_ad_text, 1):
                    f.write(f'Ad {i}:\n{text}\n\n')
            
            logging.info(f"Saved {len(ads_data)} ads to {ads_filename}")
            logging.info(f"Saved ad text to {text_filename}")
            
        except Exception as e:
            logging.error(f"Error saving data: {str(e)}")
            raise

def main():
    try:
        scraper = FacebookAdsScraper()
        
        search_term = input("\nEnter search term (e.g., walmart): ").strip()
        
        if not search_term:
            print("Please enter a valid search term")
            return
        
        print(f"\nStarting scrape for '{search_term}'...")
        print("(This may take a few moments...)")
        
        num_ads = scraper.scrape_ads(search_term)
        
        if num_ads > 0:
            print(f"\nSuccessfully scraped {num_ads} ads!")
            print(f"Check the following directories for results:")
            print(f"- Ads info: {scraper.ads_dir}")
            print(f"- Ads text: {scraper.text_dir}")
        else:
            print("\nNo ads were scraped. Please check:")
            print("1. Your Facebook credentials are correct")
            print("2. The search term exists in the Ad Library")
            print("3. Check the log file (fb_scraper.log) for detailed errors")
            
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
        print("Please check the log file (fb_scraper.log) for detailed errors")

if __name__ == "__main__":
    main()
