import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
from selenium.webdriver.common.action_chains import ActionChains



def setup_driver():
    """Sets up the Selenium WebDriver."""
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Run in headless mode
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)
    return driver

def debug_screenshot(driver, filename):
    """Takes a screenshot for debugging purposes."""
    driver.save_screenshot(filename)
    print(f"Saved screenshot: {filename}")


def extract_google_related_searches(driver):
    """Extract related searches from Google search results page."""
    related_searches = []
    try:
        # Wait for related searches to load
        time.sleep(2)
        
        # Get page source after JavaScript execution
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        # Look for related searches in multiple possible locations
        related_search_divs = soup.select("div.BNeawe.s3v9rd.AP7Wnd")  # Main related searches
        if not related_search_divs:
            related_search_divs = soup.select("div.brs_col")  # Alternative location
        if not related_search_divs:
            related_search_divs = soup.select("div[jsname='Cpkphb']")  # Another alternative
            
        for div in related_search_divs:
            links = div.select("a")
            for link in links:
                title = link.text.strip()
                href = link.get('href', '')
                if href.startswith('/search?'):
                    full_link = f"https://www.google.com{href}"
                elif href.startswith('http'):
                    full_link = href
                else:
                    continue
                    
                if title and not any(r['title'] == title for r in related_searches):
                    related_searches.append({
                        "title": title,
                        "link": full_link
                    })
                    
        # Also check for "People also search for" section
        people_also_search = soup.select("div.g-blk")
        for item in people_also_search:
            title = item.text.strip()
            if title and not any(r['title'] == title for r in related_searches):
                related_searches.append({
                    "title": title,
                    "link": f"https://www.google.com/search?q={title.replace(' ', '+')}"
                })
                
    except Exception as e:
        print(f"Error extracting Google related searches: {e}")
        debug_screenshot(driver, "google_related_error.png")
        
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


def google_search_with_related_and_sub_sitelinks(driver, query):
    """Search Google and extract results with sitelinks, sub-sitelinks, and related searches."""
    driver.get("https://www.google.com")
    search_box = driver.find_element(By.NAME, "q")
    search_box.send_keys(query)
    search_box.send_keys(Keys.RETURN)
    time.sleep(2)

    # Get the initial results
    soup = BeautifulSoup(driver.page_source, "html.parser")
    results = []

    # Parse organic results
    for idx, result in enumerate(soup.select(".tF2Cxc"), start=1):
        title = result.select_one(".DKV0Md").text
        link = result.select_one(".yuRUbf a")["href"]
        snippet = result.select_one(".VwiC3b").text if result.select_one(".VwiC3b") else ""

        # Parse sitelinks
        sitelinks = []
        for sitelink in result.select(".HiHjCd a"):
            sitelink_title = sitelink.text.strip()
            sitelink_link = sitelink["href"]

            # Extract sub-sitelinks
            sub_sitelinks = extract_sub_sitelinks(driver, sitelink_link)

            sitelinks.append({
                "title": sitelink_title,
                "link": sitelink_link,
                "sub_sitelinks": sub_sitelinks
            })

        results.append({
            "title": title,
            "link": link,
            "snippet": snippet,
            "sitelinks": sitelinks,
            "position": idx,
        })

    # Extract related searches
    related_searches = extract_google_related_searches(driver)

    return results, related_searches


def extract_youtube_related_searches(driver, query):
    """Extract related searches and suggestions from YouTube."""
    suggestions = []
    try:
        # Navigate to YouTube search
        if not driver.current_url.startswith('https://www.youtube.com'):
            driver.get('https://www.youtube.com')
            time.sleep(2)
            
        # Find and click search box
        search_box = driver.find_element(By.NAME, "search_query")
        search_box.clear()
        search_box.send_keys(query)
        time.sleep(2)  # Wait for suggestions to load
        
        # Get autocomplete suggestions
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        # Try multiple possible selectors for suggestions
        suggestion_elements = soup.select("ytd-video-suggestion-renderer")
        if not suggestion_elements:
            suggestion_elements = soup.select("yt-suggestion-item")
        if not suggestion_elements:
            suggestion_elements = soup.select("[role='option']")
            
        for element in suggestion_elements:
            title = element.text.strip()
            if title and not any(s['title'] == title for s in suggestions):
                suggestions.append({
                    "title": title,
                    "type": "autocomplete"
                })
                
        # Now get related searches from search results page
        search_box.send_keys(Keys.RETURN)
        time.sleep(3)
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        # Look for related searches in search results page
        related_sections = soup.select("ytd-horizontal-card-list-renderer")
        for section in related_sections:
            items = section.select("ytd-search-refinement-card-renderer")
            for item in items:
                title = item.text.strip()
                if title and not any(s['title'] == title for s in suggestions):
                    suggestions.append({
                        "title": title,
                        "type": "related"
                    })
                    
    except Exception as e:
        print(f"Error extracting YouTube related searches: {e}")
        debug_screenshot(driver, "youtube_related_error.png")
        
    return suggestions


def youtube_search(driver, query):
    """Searches YouTube and extracts data."""
    driver.get("https://www.youtube.com")
    search_box = driver.find_element(By.NAME, "search_query")
    search_box.send_keys(query)
    search_box.send_keys(Keys.RETURN)
    time.sleep(2)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    results = []
    for idx, result in enumerate(soup.select("ytd-video-renderer"), start=1):
        title_tag = result.select_one("#video-title")
        title = title_tag["title"] if title_tag else "No title"
        link = f"https://www.youtube.com{title_tag['href']}" if title_tag else "No link"
        results.append({
            "title": title,
            "link": link,
            "position": idx,
        })

    # Extract related searches
    related_searches = extract_youtube_related_searches(driver, query)

    return results, related_searches


def bing_search(driver, query):
    """Searches Bing and extracts data."""
    driver.get("https://www.bing.com")
    search_box = driver.find_element(By.NAME, "q")
    search_box.send_keys(query)
    search_box.send_keys(Keys.RETURN)
    time.sleep(2)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    results = []
    for idx, result in enumerate(soup.select(".b_algo"), start=1):
        title = result.select_one("h2").text
        link = result.select_one("h2 a")["href"]
        snippet = result.select_one(".b_caption p")
        snippet_text = snippet.text if snippet else ""
        results.append({
            "title": title,
            "link": link,
            "snippet": snippet_text,
            "position": idx,
        })
    return results


def main():
    query = "apple inc"
    driver = setup_driver()

    try:
        # Perform searches
        google_results, google_related = google_search_with_related_and_sub_sitelinks(driver, query)
        bing_results = bing_search(driver, query)
        youtube_results, youtube_related = youtube_search(driver, query)

        # Construct final output
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
            "googleRelatedSearches": google_related,
            "bingResults": bing_results,
            "youtubeResults": youtube_results,
            "youtubeRelatedSearches": youtube_related,
        }

        # Save to JSON file
        with open("main.json", "w") as f:
            json.dump(output, f, indent=4)

        print("Search results saved to 'search_results.json'")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
