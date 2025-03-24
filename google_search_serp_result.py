import json
import time
import logging
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)




@dataclass
class SearchParameters:
    query: str
    language: str = "en"
    country: str = "us"
    autocorrect: bool = True
    page: int = 1
    search_type: str = "search"



@dataclass
class Sitelink:
    title: str
    link: str
    sub_sitelinks: List[Dict[str, str]]



@dataclass
class SearchResult:
    position: int
    title: str
    link: str
    snippet: str
    sitelinks: List[Sitelink]



class GoogleSearchScraper:
    def __init__(self, headless: bool = True):
        """Initialize the scraper with configurable headless mode."""
        self.driver = self._setup_driver(headless)
        self.wait = WebDriverWait(self.driver, 10)



    def _setup_driver(self, headless: bool) -> webdriver.Chrome:
        """Configure and return ChromeDriver with optimal settings."""
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        return webdriver.Chrome(options=options)
    



    def extract_sub_sitelinks(self, sitelink_url: str) -> List[Dict[str, str]]:
        """Extract sub-sitelinks from a given URL with improved error handling."""
        sub_sitelinks = []
        original_url = self.driver.current_url

        try:
            self.driver.get(sitelink_url)
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            links = soup.select("a[href]")
            
            for link in links:
                title = link.text.strip()
                url = link["href"]
                if title and url.startswith("http"):
                    sub_sitelinks.append({"title": title, "link": url})
                    
        except TimeoutException:
            logger.warning(f"Timeout while extracting sub-sitelinks from {sitelink_url}")
        except Exception as e:
            logger.error(f"Error extracting sub-sitelinks from {sitelink_url}: {str(e)}")
        finally:
            self.driver.get(original_url)
            time.sleep(1)  # Brief pause to ensure page load

        return sub_sitelinks



    def extract_related_searches(self) -> List[Dict[str, str]]:
        """Extract related searches with improved selector handling."""
        related_searches = []
        selectors = [
            "div.brs_col p a",
            "div.exp-c a.k8XOCe",
            "div[jsname='Cpkphb'] a",
            "div.s75CSd a",
            "div.PNyWAd a"
        ]

        try:
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))
            soup = BeautifulSoup(self.driver.page_source, "html.parser")

            # Extract related searches from various selectors
            for selector in selectors:
                for element in soup.select(selector):
                    query = element.text.strip()
                    if query and not any(r.get('query') == query for r in related_searches):
                        related_searches.append({"query": query})

            # Extract "People also search for" suggestions
            self._extract_people_also_search(soup, related_searches)
            
            # Extract search box suggestions
            self._extract_search_suggestions(related_searches)

        except Exception as e:
            logger.error(f"Error extracting related searches: {str(e)}")

        return related_searches
    



    def _extract_people_also_search(self, soup: BeautifulSoup, related_searches: List[Dict[str, str]]):
        """Extract 'People also search for' suggestions."""
        for item in soup.select("div.g-blk"):
            title = item.text.strip()
            if title and not any(r.get('title') == title for r in related_searches):
                related_searches.append({
                    "title": title,
                    "link": f"https://www.google.com/search?q={title.replace(' ', '+')}"
                })

                

    def _extract_search_suggestions(self, related_searches: List[Dict[str, str]]):
        """Extract search box suggestions."""
        try:
            search_box = self.driver.find_element(By.NAME, "q")
            search_box.clear()
            ActionChains(self.driver).move_to_element(search_box).click().perform()
            
            suggestions = self.wait.until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "ul[role='listbox'] li"))
            )
            
            for suggestion in suggestions:
                query = suggestion.text.strip()
                if query and not any(r.get('query') == query for r in related_searches):
                    related_searches.append({"query": query})
                    
        except (TimeoutException, NoSuchElementException) as e:
            logger.warning(f"Could not extract search suggestions: {str(e)}")

    def search(self, parameters: SearchParameters) -> Dict:
        """Perform Google search and return structured results."""
        try:
            self.driver.get("https://www.google.com")
            search_box = self.driver.find_element(By.NAME, "q")
            search_box.send_keys(parameters.query + Keys.RETURN)
            
            results = self._extract_search_results()
            related_searches = self.extract_related_searches()

            return {
                "searchParameters": asdict(parameters),
                "googleResults": results,
                "relatedSearches": related_searches
            }

        except Exception as e:
            logger.error(f"Error during search: {str(e)}")
            raise

    def _extract_search_results(self) -> List[Dict]:
        """Extract search results with sitelinks."""
        results = []
        soup = BeautifulSoup(self.driver.page_source, "html.parser")

        for idx, result in enumerate(soup.select(".g"), start=1):
            try:
                search_result = self._parse_search_result(result, idx)
                if search_result:
                    results.append(asdict(search_result))
            except Exception as e:
                logger.error(f"Error extracting result {idx}: {str(e)}")

        return results

    def _parse_search_result(self, result: BeautifulSoup, position: int) -> Optional[SearchResult]:
        """Parse individual search result."""
        title_elem = result.select_one("h3")
        link_elem = result.select_one("a")
        snippet_elem = result.select_one("div.VwiC3b")

        if not (title_elem and link_elem):
            return None

        sitelinks = []
        for sitelink in result.select(".HiHjCd a"):
            sub_sitelinks = self.extract_sub_sitelinks(sitelink["href"])
            sitelinks.append(Sitelink(
                title=sitelink.text.strip(),
                link=sitelink["href"],
                sub_sitelinks=sub_sitelinks
            ))

        return SearchResult(
            position=position,
            title=title_elem.text.strip(),
            link=link_elem["href"],
            snippet=snippet_elem.text.strip() if snippet_elem else "",
            sitelinks=sitelinks
        )

    def save_results(self, results: Dict, filename: str):
        """Save search results to a JSON file."""
        try:
            with open(filename, "w", encoding='utf-8') as f:
                json.dump(results, f, indent=4, ensure_ascii=False)
            logger.info(f"Results saved to {filename}")
        except Exception as e:
            logger.error(f"Error saving results to {filename}: {str(e)}")

    def __enter__(self):
        """Enable context manager pattern."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Ensure proper cleanup of resources."""
        self.driver.quit()

def main():
    """Main execution function."""
    search_params = SearchParameters(query="Selenium in python")
    
    with GoogleSearchScraper(headless=True) as scraper:
        try:
            results = scraper.search(search_params)
            scraper.save_results(results, "google_search_results.json")
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")

if __name__ == "__main__":
    main()