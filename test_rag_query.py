import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecom.settings')
django.setup()

from recommendations.rag import get_recommendations_by_query

def test_query_recommendations():
    query = "I'm looking for a book about magic and dragons"
    print(f"Testing recommendations for query: '{query}'")
    try:
        recommendations = get_recommendations_by_query(query, top_k=3)
        print("\nGenerated Recommendations:")
        print(recommendations)
    except Exception as e:
        print(f"\nError: {e}")

if __name__ == "__main__":
    test_query_recommendations()
