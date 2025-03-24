from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import json
import time

class SearchScraper:
    def __init__(self):
        self.options = webdriver.ChromeOptions()
        self.options.add_argument('--headless')
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')
        self.options.add_argument('--lang=en-US')
        self.options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        self.driver = webdriver.Chrome(options=self.options)
        self.wait = WebDriverWait(self.driver, 10)

    def google_search(self, query):
        try:
            # Go directly to search results to avoid cookie popup
            self.driver.get(f'https://www.google.com/search?q={query}')
            time.sleep(3)  # Wait for dynamic content

            results = {
                "searchParameters": {
                    "q": query,
                    "gl": "us",
                    "hl": "en",
                    "autocorrect": True,
                    "page": 1,
                    "type": "search"
                }
            }

            # Extract knowledge graph
            try:
                kg_div = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-md]")))
                
                results["knowledgeGraph"] = {
                    "title": self.safe_extract(By.CSS_SELECTOR, "h2[data-attrid='title']"),
                    "type": self.safe_extract(By.CSS_SELECTOR, "div[data-attrid='subtitle']"),
                    "website": self.safe_extract(By.CSS_SELECTOR, "a[data-attrid*='visit']", attribute="href"),
                    "imageUrl": self.safe_extract(By.CSS_SELECTOR, "g-img.tm6bl2 img", attribute="src"),
                    "description": self.safe_extract(By.CSS_SELECTOR, "div[data-attrid='description']"),
                    "attributes": {}
                }

                # Extract attributes
                attrs = self.driver.find_elements(By.CSS_SELECTOR, "div[data-attrid^='/']")
                for attr in attrs:
                    try:
                        key = attr.find_element(By.CSS_SELECTOR, "span.w8qArf").text
                        value = attr.find_element(By.CSS_SELECTOR, "span.LrzXr").text
                        if key and value:
                            results["knowledgeGraph"]["attributes"][key] = value
                    except:
                        continue

            except TimeoutException:
                results["knowledgeGraph"] = {}

            # Extract organic results
            organic_results = []
            results_div = self.driver.find_elements(By.CSS_SELECTOR, "div.g")
            
            for position, result in enumerate(results_div, 1):
                try:
                    title = result.find_element(By.CSS_SELECTOR, "h3").text
                    link = result.find_element(By.CSS_SELECTOR, "a").get_attribute("href")
                    snippet = result.find_element(By.CSS_SELECTOR, "div.VwiC3b").text
                    
                    organic_result = {
                        "title": title,
                        "link": link,
                        "snippet": snippet,
                        "position": position
                    }
                    organic_results.append(organic_result)
                except:
                    continue

            results["organic"] = organic_results
            return results

        except Exception as e:
            print(f"Error: {str(e)}")
            return {"error": str(e)}

    def safe_extract(self, by, selector, attribute=None):
        try:
            element = self.driver.find_element(by, selector)
            return element.get_attribute(attribute) if attribute else element.text
        except:
            return ""

    def close(self):
        self.driver.quit()

def main():
    scraper = SearchScraper()
    try:
        results = scraper.google_search("apple inc")
        with open('search2.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
        print("Results saved to search_results.json")
    finally:
        scraper.close()

if __name__ == "__main__":
    main()