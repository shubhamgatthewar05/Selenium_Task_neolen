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
        self.options.add_argument('--headless')  # Run in headless mode
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')
        self.driver = webdriver.Chrome(options=self.options)
        self.wait = WebDriverWait(self.driver, 10)


    
    def google_search(self, query):

        try: 

            self.driver.get('https://www.google.com')
            
            # Accept cookies if prompted ...
            try:
                cookie_button = self.wait.until(
                    EC.presence_of_element_located((By.XPATH, "//button[contains(., 'Accept all')]"))
                )
                cookie_button.click()
            except TimeoutException:
                pass

            
            search_box = self.wait.until(

                EC.presence_of_element_located((By.NAME, "q"))
            )

            search_box.send_keys(query)
            search_box.send_keys(Keys.RETURN)


            time.sleep(5)

            results = {
            "searchParameters": {
                "q": query,
                "gl": "us",
                "hl": "en",
                "autocorrect": True,
                "page": 1,
                "type": "search"
            },
            "organic": []
            }

            try:
                kg_div = self.driver.find_element(By.ID, "kp-wp-tab-overview")

                #  Extract main knowledge graph info
                title = kg_div.find_element(By.TAG_NAME, "h2").text

                # Try to get type/category
                try:
                    type_element = kg_div.find_element(By.CLASS_NAME, "wwUB2c")
                    entity_type = type_element.text
                except NoSuchElementException:
                    entity_type = ""


                # Try to get image
                try:
                    img_element = kg_div.find_element(By.CLASS_NAME, "kc-vh")
                    image_url = img_element.get_attribute("src")
                except NoSuchElementException:
                    image_url = ""


                # Try to get description and source
                try:
                    desc_element = kg_div.find_element(By.CLASS_NAME, "kno-rdesc")
                    description = desc_element.find_element(By.TAG_NAME, "span").text
                    desc_source = desc_element.find_element(By.TAG_NAME, "a").text
                    desc_link = desc_element.find_element(By.TAG_NAME, "a").get_attribute("href")
                except NoSuchElementException:
                    description = ""
                    desc_source = ""
                    desc_link = ""

                results["knowledgeGraph"] = {
                        "title": title,
                        "type": entity_type,
                        "imageUrl": image_url,
                        "description": description,
                        "descriptionSource": desc_source,
                        "descriptionLink": desc_link,
                        "attributes": {}
                }
                # Extract website if present
                try:
                    website_element = kg_div.find_element(By.CSS_SELECTOR, "a[data-attrid='kc:/common/topic:official website']")
                    results["knowledgeGraph"]["website"] = website_element.get_attribute("href")
                except NoSuchElementException:
                    pass


                attributes = kg_div.find_elements(By.CLASS_NAME, "rVusze")
                for attr in attributes:
                    try:
                        key = attr.find_element(By.CLASS_NAME, "w8qArf").text
                        value = attr.find_element(By.CLASS_NAME, "LrzXr").text
                        results["knowledgeGraph"]["attributes"][key] = value
                    except NoSuchElementException:
                        continue

            except NoSuchElementException:
                pass



        #Extract the orginc result with sitelinks  

            organic_results = self.driver.find_elements(By.CLASS_NAME, "g")

            for position, result in enumerate(organic_results, 1):
                try:
                    title_element = result.find_element(By.TAG_NAME, "h3")
                    link_element = result.find_element(By.TAG_NAME, "a")
                    snippet_element = result.find_element(By.CLASS_NAME, "VwiC3b")
                    
                    organic_result = {
                        "title": title_element.text,
                        "link": link_element.get_attribute("href"),
                        "snippet": snippet_element.text,
                        "position": position
                    }

                    try:
                        sitelinks_table = result.find_element(By.CLASS_NAME, "PAYrJc")
                        sitelink_elements = sitelinks_table.find_elements(By.TAG_NAME, "a")
                        
                        if sitelink_elements:
                            organic_result["sitelinks"] = []
                            for sitelink in sitelink_elements:
                                organic_result["sitelinks"].append({
                                    "title": sitelink.text,
                                    "link": sitelink.get_attribute("href")
                                })
                    except NoSuchElementException:
                        pass

                    results["organic"].append(organic_result)
                except NoSuchElementException:
                    continue

            return results
        
        except Exception as e:
            return {"error": str(e)}


                    

    # def google_search(self, query):
    #     try:
    #         self.driver.get('https://www.google.com')
            
    #         # Accept cookies if prompted ...
    #         try:
    #             cookie_button = self.wait.until(
    #                 EC.presence_of_element_located((By.XPATH, "//button[contains(., 'Accept all')]"))
    #             )
    #             cookie_button.click()
    #         except TimeoutException:
    #             pass

    #         # Perform search
    #         # search_box = self.wait.until(
    #         #     EC.presence_of_element_located((By.NAME, "q"))
    #         # )
    #         search_box = self.wait.until(
    #             EC.presence_of_element_located((By.NAME, "q"))
    #         )
    #         search_box.send_keys(query)
    #         search_box.send_keys(Keys.RETURN)

    #         # Wait for results
    #         time.sleep(5)

    #         results = {
    #             "searchParameters": {
    #                 "q": query,
    #                 "gl": "us",
    #                 "hl": "en",
    #                 "autocorrect": True,
    #                 "page": 1,
    #                 "type": "search"
    #             },
    #             "organic": []
    #         }
    #         # knowledge_graph =  {}
            


    #         # Extract knowledge graph if present
    #         try:
    #             kg_div = self.driver.find_element(By.ID, "kp-wp-tab-overview")
    #             results["knowledgeGraph"] = {
    #                 "title": kg_div.find_element(By.TAG_NAME, "h2").text,
    #                 "description": kg_div.find_element(By.CLASS_NAME, "kno-rdesc").text,
    #                 "attributes": {}
    #             }
    #             # Extract attributes
    #             attributes = kg_div.find_elements(By.CLASS_NAME, "rVusze")
    #             for attr in attributes:
    #                 try:
    #                     key = attr.find_element(By.CLASS_NAME, "w8qArf").text
    #                     value = attr.find_element(By.CLASS_NAME, "LrzXr").text
    #                     results["knowledgeGraph"]["attributes"][key] = value
    #                 except NoSuchElementException:
    #                     continue
    #         except NoSuchElementException:
    #             pass

    #         # Extract organic results
    #         organic_results = self.driver.find_elements(By.CLASS_NAME, "g")
    #         for position, result in enumerate(organic_results, 1):
    #             try:
    #                 title_element = result.find_element(By.TAG_NAME, "h3")
    #                 link_element = result.find_element(By.TAG_NAME, "a")
    #                 snippet_element = result.find_element(By.CLASS_NAME, "VwiC3b")
                    
    #                 organic_result = {
    #                     "title": title_element.text,
    #                     "link": link_element.get_attribute("href"),
    #                     "snippet": snippet_element.text,
    #                     "position": position
    #                 }
    #                 results["organic"].append(organic_result)
    #             except NoSuchElementException:
    #                 continue

    #         return results

    #     except Exception as e:
    #         return {"error": str(e)}

    def youtube_search(self, query):
        try:
            self.driver.get('https://www.youtube.com')
            
            # Accept cookies if prompted
            try:
                cookie_button = self.wait.until(
                    EC.presence_of_element_located((By.XPATH, "//button[contains(., 'Accept all')]"))
                )
                cookie_button.click()
            except TimeoutException:
                pass

            # Perform search
            search_box = self.wait.until(
                EC.presence_of_element_located((By.NAME, "search_query"))
            )
            search_box.send_keys(query)
            search_box.send_keys(Keys.RETURN)

            # Wait for results
            time.sleep(2)

            results = {
                "searchParameters": {
                    "q": query,
                    "platform": "youtube",
                    "page": 1
                },
                "videos": []
            }

            # Extract video results
            video_elements = self.driver.find_elements(By.TAG_NAME, "ytd-video-renderer")
            for position, video in enumerate(video_elements, 1):
                try:
                    title_element = video.find_element(By.ID, "video-title")
                    channel_element = video.find_element(By.CLASS_NAME, "ytd-channel-name")
                    
                    video_data = {
                        "title": title_element.text,
                        "link": title_element.get_attribute("href"),
                        "channel": channel_element.text,
                        "position": position
                    }
                    results["videos"].append(video_data)
                except NoSuchElementException:
                    continue

            return results

        except Exception as e:
            return {"error": str(e)}

    def bing_search(self, query):
        try:
            self.driver.get('https://www.bing.com')
            
            # Perform search
            search_box = self.wait.until(
                EC.presence_of_element_located((By.NAME, "q"))
            )
            search_box.send_keys(query)
            search_box.send_keys(Keys.RETURN)

            # Wait for results
            time.sleep(2)

            results = {
                "searchParameters": {
                    "q": query,
                    "engine": "bing",
                    "page": 1
                },
                "organic": []
            }

            # Extract organic results
            organic_results = self.driver.find_elements(By.CLASS_NAME, "b_algo")
            for position, result in enumerate(organic_results, 1):
                try:
                    title_element = result.find_element(By.TAG_NAME, "h2")
                    link_element = title_element.find_element(By.TAG_NAME, "a")
                    snippet_element = result.find_element(By.CLASS_NAME, "b_caption")
                    
                    organic_result = {
                        "title": title_element.text,
                        "link": link_element.get_attribute("href"),
                        "snippet": snippet_element.text,
                        "position": position
                    }
                    results["organic"].append(organic_result)
                except NoSuchElementException:
                    continue

            return results

        except Exception as e:
            return {"error": str(e)}

    def close(self):
        self.driver.quit()

# Example usage
def main():
    scraper = SearchScraper()
    query = "apple inc"
    
    try:
        # Perform searches
        google_results = scraper.google_search(query)
        youtube_results = scraper.youtube_search(query)
        bing_results = scraper.bing_search(query)
        
        # Combine results
        all_results = {
            "google": google_results,
            "youtube": youtube_results,
            "bing": bing_results
        }
        
        # Save results to file
        with open('app.json', 'w', encoding='utf-8') as f:
            json.dump(all_results, f, ensure_ascii=False, indent=4)
            
        print("Search results have been saved to search_results.json")
        
    finally:
        scraper.close()

if __name__ == "__main__":
    main()