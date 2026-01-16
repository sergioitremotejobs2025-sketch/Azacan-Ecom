"""
Utility module for fetching book information from Google Books API.
"""
import requests

GOOGLE_BOOKS_API_URL = "https://www.googleapis.com/books/v1/volumes"


def fetch_dimensions_by_isbn(isbn: str) -> dict | None:
    """
    Query Google Books API by ISBN and return dimensions dict.
    Returns {'height': ..., 'width': ..., 'thickness': ...} or None.
    
    Note: Dimensions are only available when fetching individual volume by ID,
    so we first search by ISBN, then fetch the volume directly.
    """
    # Step 1: Search by ISBN to get the volume ID
    params = {"q": f"isbn:{isbn}"}
    try:
        response = requests.get(GOOGLE_BOOKS_API_URL, params=params, timeout=10)
        response.raise_for_status()
    except requests.RequestException:
        return None

    data = response.json()
    items = data.get("items", [])
    if not items:
        return None

    volume_id = items[0].get("id")
    if not volume_id:
        return None

    # Step 2: Fetch the volume directly by ID to get full details including dimensions
    try:
        vol_response = requests.get(f"{GOOGLE_BOOKS_API_URL}/{volume_id}", timeout=10)
        vol_response.raise_for_status()
    except requests.RequestException:
        return None

    vol_data = vol_response.json()
    volume_info = vol_data.get("volumeInfo", {})
    dimensions = volume_info.get("dimensions")
    
    if dimensions:
        return {
            "height": dimensions.get("height"),
            "width": dimensions.get("width"),
            "thickness": dimensions.get("thickness"),
        }
    return None


def fetch_image_by_isbn(isbn: str) -> bytes | None:
    """
    Query Google Books API by ISBN and return book cover image bytes.
    Returns image bytes or None if not found.
    """
    # Step 1: Search by ISBN to get the volume ID
    params = {"q": f"isbn:{isbn}"}
    try:
        response = requests.get(GOOGLE_BOOKS_API_URL, params=params, timeout=10)
        response.raise_for_status()
    except requests.RequestException:
        return None

    data = response.json()
    items = data.get("items", [])
    if not items:
        return None

    volume_id = items[0].get("id")
    if not volume_id:
        return None

    # Step 2: Fetch the volume directly by ID to get imageLinks
    try:
        vol_response = requests.get(f"{GOOGLE_BOOKS_API_URL}/{volume_id}", timeout=10)
        vol_response.raise_for_status()
    except requests.RequestException:
        return None

    vol_data = vol_response.json()
    volume_info = vol_data.get("volumeInfo", {})
    image_links = volume_info.get("imageLinks", {})
    
    # Try to get the largest available image
    image_url = (
        image_links.get("extraLarge")
        or image_links.get("large")
        or image_links.get("medium")
        or image_links.get("small")
        or image_links.get("thumbnail")
        or image_links.get("smallThumbnail")
    )
    
    if not image_url:
        return None

    try:
        img_response = requests.get(image_url, timeout=15)
        img_response.raise_for_status()
        return img_response.content
    except requests.RequestException:
        return None


def fetch_image_from_azacan(isbn: str) -> bytes | None:
    """
    Scrape book cover image from libros.azacan.org by ISBN.
    Returns image bytes or None if not found.
    """
    search_url = f"https://libros.azacan.org/es/libreria?modo=avanzado&titulo=&autor=&editorial=&isbn={isbn}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(search_url, headers=headers, timeout=15)
        response.raise_for_status()
    except requests.RequestException:
        return None

    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Look for the image in search results
        # The browser subagent identified '.product-image-link img'
        img_tag = soup.select_one(".product-image-link img")
        
        if not img_tag or not img_tag.get("src"):
            return None
            
        image_url = img_tag["src"]
        
        # If it's a relative URL, make it absolute
        if image_url.startswith("/"):
            image_url = f"https://libros.azacan.org{image_url}"
            
        # Download the image
        img_response = requests.get(image_url, headers=headers, timeout=15)
        img_response.raise_for_status()
        return img_response.content
        
    except Exception:
        return None


def fetch_image_by_reference_from_azacan(reference: str) -> bytes | None:
    """
    Scrape book cover image from libros.azacan.org by Reference.
    Returns image bytes or None if not found.
    """
    search_url = f"https://libros.azacan.org/es/libreria?search={reference}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(search_url, headers=headers, timeout=15)
        response.raise_for_status()
    except requests.RequestException:
        return None

    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Look for the image in search results
        img_tag = soup.select_one(".product-image-link img")
        
        if not img_tag or not img_tag.get("src"):
            return None
            
        image_url = img_tag["src"]
        
        if image_url.startswith("/"):
            image_url = f"https://libros.azacan.org{image_url}"
            
        img_response = requests.get(image_url, headers=headers, timeout=15)
        img_response.raise_for_status()
        return img_response.content
        
    except Exception:
        return None


def _scrape_azacan_detail_page(detail_url: str) -> dict | None:
    """
    Helper function to scrape details from an Azacán detail page.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        from bs4 import BeautifulSoup
        response = requests.get(detail_url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        details = {}

        # 1. Scrape Title
        title_tag = soup.select_one("h1.product-detail-title")
        if title_tag:
            details['name'] = title_tag.get_text().strip()

        # 2. Scrape Image URL
        # The main image is typically in a link with class 'product-detail-image-link'
        img_tag = soup.select_one(".product-detail-image-container img")
        if img_tag and img_tag.get("src"):
            image_url = img_tag["src"]
            if image_url.startswith("/"):
                image_url = f"https://libros.azacan.org{image_url}"
            details['image_url'] = image_url

        # 3. Scrape Description
        desc_div = soup.select_one("#tab_descripcion")
        if desc_div:
            desc_p = desc_div.find_all("p")
            description = []
            for p in desc_p:
                if "h3" not in p.get("class", []):
                    description.append(p.get_text().strip())
            details['description'] = "\n\n".join(description) if description else desc_div.get_text().strip()

        # 3. Scrape Table Data
        table = soup.select_one(".product-detail-info-table")
        if table:
            rows = table.find_all("tr")
            for row in rows:
                cols = row.find_all("td")
                if len(cols) >= 2:
                    label = cols[0].get_text().strip().lower()
                    value = cols[1].get_text().strip()
                    
                    if "referencia:" in label:
                        details['reference'] = value
                    elif "isbn:" in label:
                        details['isbn'] = value
                    elif "editorial:" in label:
                        details['publisher'] = value
                    elif "año:" in label:
                        details['year'] = value
                    elif "lugar de edición:" in label:
                        details['edition_place'] = value
                    elif "páginas:" in label:
                        details['pages'] = value
                    elif "medidas:" in label:
                        details['measures'] = value
        
        return details
    except Exception:
        return None


def fetch_all_details_from_azacan(isbn: str) -> dict | None:
    """
    Search by ISBN on Azacán and scrape all details from the detail page.
    """
    search_url = f"https://libros.azacan.org/es/libreria?modo=avanzado&titulo=&autor=&editorial=&isbn={isbn}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(search_url, headers=headers, timeout=15)
        response.raise_for_status()
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.content, "html.parser")

        detail_link = soup.select_one("a.product-list-title")
        if not detail_link or not detail_link.get("href"):
            return None

        detail_url = detail_link["href"]
        if detail_url.startswith("/"):
            detail_url = f"https://libros.azacan.org{detail_url}"

        return _scrape_azacan_detail_page(detail_url)
    except Exception:
        return None


def fetch_all_details_by_reference_from_azacan(reference: str) -> dict | None:
    """
    Search by Reference on Azacán and scrape all details from the detail page.
    """
    search_url = f"https://libros.azacan.org/es/libreria?search={reference}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(search_url, headers=headers, timeout=15)
        response.raise_for_status()
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.content, "html.parser")

        # In a general search, we might get multiple results or direct link if it's unique
        # Usually it shows the list view even for one result if search is used
        detail_link = soup.select_one("a.product-list-title")
        if not detail_link or not detail_link.get("href"):
            return None

        detail_url = detail_link["href"]
        if detail_url.startswith("/"):
            detail_url = f"https://libros.azacan.org{detail_url}"

        return _scrape_azacan_detail_page(detail_url)
    except Exception:
        return None
def get_book_description(query, max_results=1):
    """
    Fetch the book description from Google Books API.
    
    Parameters:
        query (str): Can be an ISBN (e.g., '9780141439518') or a search term 
                     (e.g., 'intitle:Dune inauthor:Herbert')
        max_results (int): Number of results to consider (default: 1)
    
    Returns:
        str or None: The book description if found, otherwise None
    """
    base_url = "https://www.googleapis.com/books/v1/volumes"
    
    # Build the query parameter
    if query.replace('-', '').isdigit() and len(query.replace('-', '')) in (10, 13):
        params = {"q": f"isbn:{query}"}
    else:
        params = {"q": query}
    
    params["maxResults"] = max_results
    
    try:
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()  # Raise error for bad status codes
        data = response.json()
        
        if data.get("totalItems", 0) == 0:
            print("No books found for the given query.")
            return None
        
        # Get the first (best) match
        book = data["items"][0]["volumeInfo"]
        description = book.get("description")
        
        if description:
            # Clean up HTML tags if present (some descriptions include <b>, <i>, etc.)
            try:
                from bs4 import BeautifulSoup
                clean_description = BeautifulSoup(description, "html.parser").get_text()
                return clean_description.strip()
            except ImportError:
                # If BeautifulSoup not installed, return raw description
                return description.strip()
        
        else:
            print(f"No description available for '{book.get('title', 'Unknown title')}'.")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from Google Books API: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None
    """
    Example usage
if __name__ == "__main__":
    # By ISBN
    desc = get_book_description("9780441172719")  # Dune
    if desc:
        print("Description:")
        print(desc)
    
    print("\n" + "="*50 + "\n")
    
    # By title/author
    desc = get_book_description("intitle:1984 inauthor:Orwell")
    if desc:
        print("Description:")
        print(desc)
    """