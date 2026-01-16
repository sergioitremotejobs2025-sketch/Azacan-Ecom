import requests
import json
import sys

BASE_URL = "http://127.0.0.1:8000/api"

def test_endpoint(name, path, method="POST", data=None):
    url = f"{BASE_URL}{path}"
    print(f"\n--- Testing {name} ---")
    print(f"URL: {url}")
    print(f"Method: {method}")
    if data:
        print(f"Data: {json.dumps(data)}")
    
    try:
        if method == "POST":
            response = requests.post(url, json=data)
        else:
            response = requests.get(url, params=data)
        
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            # Truncate recommendations for display
            recs = result.get('recommendations', '')
            print(f"Response (truncated): {recs[:200]}...")
        else:
            print(f"Error Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the server. Make sure 'python manage.py runserver' is running on port 8000.")
        sys.exit(1)

def run_tests():
    # 1. Test Query Recommendation
    test_endpoint(
        "Recommendation by Query", 
        "/recommend/query/", 
        data={"query": "I want a book about history of mathematics", "top_k": 2}
    )

    # 2. Test Title Recommendation
    # Note: Using a book title that likely exists in the db based on previous tests
    test_endpoint(
        "Recommendation by Title", 
        "/recommend/title/", 
        data={"title": "EL DRAGON DE SU MAJESTAD", "top_k": 2}
    )

    # 3. Test User Recommendation
    # Note: user_id=1 is a common default, but may vary
    test_endpoint(
        "Recommendation by User", 
        "/recommend/user/", 
        method="GET",
        data={"user_id": 1, "top_k": 2}
    )

if __name__ == "__main__":
    run_tests()
