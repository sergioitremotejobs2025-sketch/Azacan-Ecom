import requests
import time

def test_search(query):
    url = f"http://localhost:8000/search/?search={query}"
    try:
        response = requests.get(url) 
        if response.status_code == 200:
            print(f"Search for '{query}' returned status 200 OK.")
            if "No se encontraron productos" in response.text:
                print("No products found (as expected maybe?) or maybe search failed to find matches.")
            else:
                print("Products found! Check the output HTML for results.")
                # print snippet to confirm
                print(response.text[:500])
        else:
            print(f"Search failed with status: {response.status_code}")
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    print("Testing semantic search (GET query)...")
    time.sleep(2)
    test_search("history")
    test_search("novel")
