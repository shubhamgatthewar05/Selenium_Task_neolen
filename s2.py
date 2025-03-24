import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def search_google(query):
    driver.get("https://www.google.com")
    search_box = driver.find_element(By.NAME, "q")
    search_box.send_keys(query)
    search_box.send_keys(Keys.RETURN)

    # Wait for the results to load
    wait = WebDriverWait(driver, 10)
    results_container = wait.until(EC.presence_of_element_located((By.ID, "search")))

    results = []
    organic_results = results_container.find_elements(By.CSS_SELECTOR, "div.tF2Cxc")
    for position, result in enumerate(organic_results[:10], start=1):
        try:
            title = result.find_element(By.TAG_NAME, "h3").text
            link = result.find_element(By.TAG_NAME, "a").get_attribute("href")
            snippet_element = result.find_elements(By.CSS_SELECTOR, "div.VwiC3b, div.yourNewClass")
            snippet = snippet_element[0].text if snippet_element else "No snippet available"
            results.append({
                "title": title,
                "link": link,
                "snippet": snippet,
                "position": position
            })
        except Exception as e:
            print(f"Error processing result {position}: {e}")
            continue

    # Extract the knowledge graph (if available)
    knowledge_graph = {}
    try:
        kg_title = driver.find_element(By.CSS_SELECTOR, "div > div > h2").text
        kg_description = driver.find_element(By.CSS_SELECTOR, "div").text
        kg_image = driver.find_element(By.CSS_SELECTOR, "img").get_attribute("src")
        kg_website = driver.find_element(By.CSS_SELECTOR, "div").get_attribute("href")
        attributes_elements = driver.find_elements(By.CSS_SELECTOR, "div.kno-fv")

        attributes = {}
        for attr in attributes_elements:
            key = attr.find_element(By.TAG_NAME, "span").text
            value = attr.find_element(By.TAG_NAME, "div").text
            attributes[key] = value

        knowledge_graph = {
            "title": kg_title,
            "description": kg_description,
            "imageUrl": kg_image,
            "website": kg_website,
            "attributes": attributes
        }
    except Exception as e:
        print(f"Knowledge Graph not found: {e}")

    return {"organicResults": results, "knowledgeGraph": knowledge_graph}

def search_youtube(query):
    driver.get("https://www.youtube.com")
    search_box = driver.find_element(By.NAME, "search_query")
    search_box.send_keys(query)
    search_box.send_keys(Keys.RETURN)
    time.sleep(2)

    results = []
    video_results = driver.find_elements(By.CSS_SELECTOR, "ytd-video-renderer")
    for position, video in enumerate(video_results[:10], start=1):
        title = video.find_element(By.CSS_SELECTOR, "a#video-title").text
        link = video.find_element(By.CSS_SELECTOR, "a#video-title").get_attribute("href")
        snippet = video.find_element(By.CSS_SELECTOR, "yt-formatted-string#description-text").text if video.find_elements(By.CSS_SELECTOR, "yt-formatted-string#description-text") else ""
        results.append({"title": title, "link": link, "snippet": snippet, "position": position})

    return results

def search_bing(query):
    driver.get("https://www.bing.com")
    search_box = driver.find_element(By.NAME, "q")
    search_box.send_keys(query)
    search_box.send_keys(Keys.RETURN)
    time.sleep(2)

    results = []
    organic_results = driver.find_elements(By.CSS_SELECTOR, "li.b_algo")
    for position, result in enumerate(organic_results[:10], start=1):
        title = result.find_element(By.TAG_NAME, "h2").text
        link = result.find_element(By.TAG_NAME, "a").get_attribute("href")
        snippet = result.find_element(By.CSS_SELECTOR, "p").text if result.find_elements(By.CSS_SELECTOR, "p") else ""
        results.append({"title": title, "link": link, "snippet": snippet, "position": position})

    return results

if __name__ == "__main__":
    query = "apple inc"
    driver = webdriver.Chrome()

    try:
        google_results = search_google(query)
        youtube_results = search_youtube(query)
        bing_results = search_bing(query)

        final_output = {
            "searchParameters": {
                "q": query,
                "gl": "us",
                "hl": "en",
                "autocorrect": True,
                "page": 1,
                "type": "search"
            },
            "google": google_results,
            "youtube": youtube_results,
            "bing": bing_results
        }

        with open("s23.json", "w") as f:
            json.dump(final_output, f, indent=4)

    finally:
        driver.quit()
