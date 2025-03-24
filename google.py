import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def setup_driver():
    """Sets up the Selenium WebDriver."""
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(options=options)
    return driver




def debug_screenshot(driver, filename):
    """Takes a screenshot for debugging purposes."""
    driver.save_screenshot(filename)
    print(f"Saved screenshot: {filename}")

def extract_google_related_searches(driver):
    """Extract related searches from Google."""
    related_searches = []
    try:
        # Wait for related searches to load
        time.sleep(3)
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        # Try different selectors for related searches
        selectors = [
            "div.brs_col p a",  # Bottom related searches
            "div.exp-c a.k8XOCe",  # Side related searches
            "div[jsname='Cpkphb'] a",  # Alternative location
            "div.s75CSd a",  # Another possible location
            "div.PNyWAd a" # Yet another location
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            for element in elements:
                query = element.text.strip()
                if query and not any(r['query'] == query for r in related_searches):
                    related_searches.append({"query": query})
        
        # Also check "People also ask" questions
        # people_also_ask = soup.select("div.related-question-pair")
        # for item in people_also_ask:
        #     query = item.text.strip()
        #     if query and not any(r['query'] == query for r in related_searches):
        #         related_searches.append({"query": query})
        people_also_search = soup.select("div.g-blk")
        for item in people_also_search:
            title = item.text.strip()
            if title and not any(r['title'] == title for r in related_searches):
                related_searches.append({
                    "title": title,
                    "link": f"https://www.google.com/search?q={title.replace(' ', '+')}"
                })
        # Try to get suggestions from search box
        try:
            search_box = driver.find_element(By.NAME, "q")
            search_box.clear()
            ActionChains(driver).move_to_element(search_box).click().perform()
            time.sleep(1)
            suggestions = driver.find_elements(By.CSS_SELECTOR, "ul[role='listbox'] li")
            for suggestion in suggestions:
                query = suggestion.text.strip()
                if query and not any(r['query'] == query for r in related_searches):
                    related_searches.append({"query": query})
        except Exception as e:
            print(f"Error getting search suggestions: {e}")
            
    except Exception as e:
        print(f"Error extracting Google related searches: {e}")
        
    return related_searches
    

def extract_sub_sitelinks(driver, sitelink_url):
    """Extract sub-sitelinks from a given sitelink URL."""
    sub_sitelinks = []
    try:
        driver.get(sitelink_url)
        time.sleep(2)  # Allow the page to load
        soup = BeautifulSoup(driver.page_source, "html.parser")

        # Extract links from the page
        for link in soup.select("a[href]"):  # Select all anchor tags with href
            title = link.text.strip()
            url = link["href"]
            if title and url.startswith("http"):  # Only include valid links
                sub_sitelinks.append({"title": title, "link": url})
    except Exception as e:
        print(f"Error extracting sub-sitelinks from {sitelink_url}: {e}")
    return sub_sitelinks


# def extract_youtube_related_searches(driver, query):
#     """Extract search suggestions from YouTube search bar."""
#     suggestions = []
#     try:
#         # Make sure we're on YouTube
#         if not driver.current_url.startswith('https://www.youtube.com'):
#             driver.get('https://www.youtube.com')
#             time.sleep(2)

#         # Find and interact with search box
#         search_box = driver.find_element(By.NAME, "search_query")
#         search_box.clear()
#         search_box.send_keys(query)
        
#         # Wait for suggestions to load
#         time.sleep(2)  
        
#         # Get the suggestions panel
#         try:
#             suggestions_panel = WebDriverWait(driver, 10).until(
#                 EC.presence_of_element_located((By.CSS_SELECTOR, "ytd-suggestion-panel-renderer"))
#             )
            
#             # Get all suggestion items
#             suggestion_elements = suggestions_panel.find_elements(By.CSS_SELECTOR, "ytd-searchbox-suggestion-renderer")
            
#             for element in suggestion_elements:
#                 try:
#                     # Get the suggestion text
#                     suggestion_text = element.get_attribute('innerHTML')
#                     soup = BeautifulSoup(suggestion_text, 'html.parser')
                    
#                     # Extract the text from the suggestion
#                     suggestion = soup.text.strip()
                    
#                     if suggestion and suggestion != query:  # Avoid duplicates and original query
#                         suggestions.append({
#                             "query": suggestion
#                         })
#                 except Exception as e:
#                     print(f"Error extracting individual suggestion: {e}")
#                     continue
                    
#         except Exception as e:
#             print(f"Error finding suggestions panel: {e}")
#             # Try alternative method with direct HTML parsing
#             soup = BeautifulSoup(driver.page_source, 'html.parser')
#             suggestion_elements = soup.select("ytd-searchbox-suggestion-renderer")
            
#             for element in suggestion_elements:
#                 suggestion = element.text.strip()
#                 if suggestion and suggestion != query:
#                     suggestions.append({
#                         "query": suggestion
#                     })
    
#     except Exception as e:
#         print(f"Error in YouTube related search extraction: {e}")
#         # Take a debug screenshot
#         debug_screenshot(driver, "youtube_suggestions_error.png")
    
#     return suggestions


def debug_screenshot(driver, filename):
    """Takes a screenshot for debugging purposes."""
    driver.save_screenshot(filename)
    print(f"Saved screenshot: {filename}")


def google_search(driver, query):
    """Perform Google search and extract results with related searches."""
    driver.get("https://www.google.com")
    search_box = driver.find_element(By.NAME, "q")
    search_box.send_keys(query)
    search_box.send_keys(Keys.RETURN)
    time.sleep(2)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    results = []

    # Extract organic results
    for idx, result in enumerate(soup.select(".g"), start=1):
        try:
            title_elem = result.select_one("h3")
            link_elem = result.select_one("a")
            snippet_elem = result.select_one("div.VwiC3b")
            
            if title_elem and link_elem:
                title = title_elem.text.strip()
                link = link_elem["href"]
                snippet = snippet_elem.text.strip() if snippet_elem else ""
                
                results.append({
                    "position": idx,
                    "title": title,
                    "link": link,
                    "snippet": snippet
                })
        except Exception as e:
            print(f"Error extracting result {idx}: {e}")
            continue

    # Get related searches
    related_searches = extract_google_related_searches(driver)
    
    return results, related_searches

# def youtube_search(driver, query):
#     """Searches YouTube and extracts data with related searches."""
#     driver.get("https://www.youtube.com")
#     time.sleep(2)  # Wait for page to load
    
#     # First get the search suggestions
#     related_searches = extract_youtube_related_searches(driver, query)
    
#     # Then perform the actual search
#     search_box = driver.find_element(By.NAME, "search_query")
#     search_box.clear()  # Clear any existing text
#     search_box.send_keys(query)
#     search_box.send_keys(Keys.RETURN)
#     time.sleep(2)

#     soup = BeautifulSoup(driver.page_source, "html.parser")
#     results = []
#     for idx, result in enumerate(soup.select("ytd-video-renderer"), start=1):
#         title_tag = result.select_one("#video-title")
#         title = title_tag["title"] if title_tag else "No title"
#         link = f"https://www.youtube.com{title_tag['href']}" if title_tag else "No link"
#         results.append({
#             "title": title,
#             "link": link,
#             "position": idx,
#         })

#     return results, related_searches

def main():
    query = "Selenium in python"
    driver = setup_driver()

    try:
        # Perform searches
        google_results, google_related = google_search(driver, query)
        # youtube_results, youtube_related = youtube_search(driver, query)

        # Construct output
        output = {
            "searchParameters": {
                "q": query,
                "gl": "us",
                "hl": "en",
                "autocorrect": True,
                "page": 1,
                "type": "search"
            },
            "googleResults": google_results,
            "relatedSearches": google_related,  # Main related searches
            # "youtubeResults": youtube_results,
            # "youtubeRelatedSearches": youtube_related
        }

        # Save to JSON file
        with open("google.json", "w", encoding='utf-8') as f:
            json.dump(output, f, indent=4, ensure_ascii=False)

        print("Search results saved to 'search_results.json'")

    finally:
        driver.quit()

if __name__ == "__main__":
    main()














