from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import chromedriver_autoinstaller
import json
import os
import sys
import time
import traceback

def setup_chrome_driver():
    try:
        # Auto-install the correct chromedriver version
        chromedriver_autoinstaller.install()
        
        # Set up Chrome options
        chrome_options = Options()
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--log-level=3')  # Suppress logging
        chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        # Initialize the driver without explicit service
        driver = webdriver.Chrome(options=chrome_options)
        return driver
    except Exception as e:
        print(f"\nError setting up Chrome driver: {str(e)}")
        print("\nDetailed error information:")
        print(traceback.format_exc())
        return None

def scrape_knowledge_graph(query):
    driver = None
    try:
        # Setup driver
        driver = setup_chrome_driver()
        if not driver:
            return {"error": "Failed to initialize Chrome driver"}
        
        # Navigate to Google
        driver.get("https://www.google.com")
        time.sleep(2)
        
        # Find and interact with search box
        search_box = driver.find_element(By.NAME, "q")
        search_box.clear()
        search_box.send_keys(query)
        search_box.send_keys(Keys.RETURN)
        time.sleep(3)
        
        # Initialize result
        result = {
            "searchParameters": {
                "q": query,
                "gl": "us",
                "hl": "en",
                "autocorrect": True,
                "page": 1,
                "type": "search"
            }
        }
        
        # Try to find knowledge graph
        try:
            wait = WebDriverWait(driver, 10)
            knowledge_panel = wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "div.kp-wholepage")))
            
            # Extract basic information
            result["knowledgeGraph"] = {
                "title": safe_extract(driver, "h2.qrShPb"),
                "type": safe_extract(driver, "div.wwUB2c"),
                "website": safe_extract_attribute(driver, "a.Q7PwXb", "href"),
                "description": safe_extract(driver, "div.LGOjhe"),
                "attributes": {}
            }
            
            # Extract attributes
            attributes = {}
            rows = driver.find_elements(By.CSS_SELECTOR, "div.rVusze")
            for row in rows:
                try:
                    label = row.find_element(By.CSS_SELECTOR, "span.w8qArf").text.strip()
                    value = row.find_element(By.CSS_SELECTOR, "span.LrzXr").text.strip()
                    if label and value:
                        attributes[label] = value
                except:
                    continue
            
            result["knowledgeGraph"]["attributes"] = attributes
            
        except Exception as e:
            result["error"] = f"No knowledge graph found for query: {query}"
        
        return result
        
    except Exception as e:
        return {"error": f"Scraping failed: {str(e)}"}
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

def safe_extract(driver, css_selector):
    try:
        element = driver.find_element(By.CSS_SELECTOR, css_selector)
        return element.text.strip()
    except:
        return None

def safe_extract_attribute(driver, css_selector, attribute):
    try:
        element = driver.find_element(By.CSS_SELECTOR, css_selector)
        return element.get_attribute(attribute)
    except:
        return None

def main():
    # Ensure output directory exists
    output_dir = "search_results"
    os.makedirs(output_dir, exist_ok=True)
    
    print("\nGoogle Knowledge Graph Scraper")
    print("-----------------------------")
    print("Initializing...")
    
    # Check Python version
    print(f"Python Version: {sys.version}")
    
    while True:
        try:
            # Get query
            query = input("\nEnter your search query (or 'quit' to exit): ").strip()
            
            if query.lower() == 'quit':
                break
            
            if not query:
                print("Please enter a valid query.")
                continue
            
            # Execute search
            print("\nSearching...")
            result = scrape_knowledge_graph(query)
            
            # Save results
            filename = os.path.join(output_dir, 
                                  f"{query.replace(' ', '_').lower()}_info.json")
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=4, ensure_ascii=False)
            
            # Display results
            print("\nResults:")
            print(json.dumps(result, indent=4, ensure_ascii=False))
            print(f"\nResults saved to {filename}")
            
        except Exception as e:
            print(f"\nAn error occurred: {str(e)}")
            print("\nDetailed error information:")
            print(traceback.format_exc())

if __name__ == "__main__":
    main()