import requests
from bs4 import BeautifulSoup
import os

def test_azacan_scraper(isbn):
    search_url = f"https://libros.azacan.org/es/libreria?modo=avanzado&titulo=&autor=&editorial=&isbn={isbn}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    print(f"Searching: {search_url}")
    try:
        response = requests.get(search_url, headers=headers, timeout=15)
        response.raise_for_status()
        print(f"Search response status: {response.status_code}")
    except Exception as e:
        print(f"Error during search request: {e}")
        return

    soup = BeautifulSoup(response.content, "html.parser")
    
    # Debug: Print first 500 chars of HTML
    print("HTML Preview:")
    print(response.text[:500])
    
    # Try different selectors
    selectors = [".product-image-link img", ".product-image", "a[href*='libro'] img", "img[src*='uploads/libros']"]
    for selector in selectors:
        img_tag = soup.select_one(selector)
        print(f"Selector '{selector}': {'Found' if img_tag else 'Not Found'}")
        if img_tag:
            src = img_tag.get("src")
            print(f"  src: {src}")
            if src:
                # Absolute URL check
                if src.startswith("/"):
                    src = f"https://libros.azacan.org{src}"
                print(f"  Absolute src: {src}")
                
                # Try downloading
                try:
                    img_res = requests.get(src, headers=headers, timeout=10)
                    print(f"  Download status: {img_res.status_code}")
                except Exception as e:
                    print(f"  Download error: {e}")

if __name__ == "__main__":
    test_azacan_scraper("8460989747")
