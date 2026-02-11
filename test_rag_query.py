import os
import django
import json
import time

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecom.settings')
django.setup()

from recommendations.rag import get_sentence_transformer_model, get_recommendations_by_query
from recommendations.models import Book
from pgvector.django import CosineDistance

def test_query_recommendations_detailed():
    query = "I'm looking for a book about magic and dragons"
    print(f"Testing recommendations for query: '{query}'")
    
    total_start = time.time()
    
    # 1. Model Loading
    print("\n1. Loading SentenceTransformer model...")
    s1 = time.time()
    model = get_sentence_transformer_model()
    print(f"   Done in {time.time() - s1:.2f}s")
    
    # 2. Embedding
    print("\n2. Generating query embedding...")
    s2 = time.time()
    query_embedding = model.encode(query).tolist()
    print(f"   Done in {time.time() - s2:.2f}s")
    
    # 3. Vector Search
    print("\n3. Performing vector search in DB...")
    s3 = time.time()
    similar_books = (
        Book.objects.annotate(distance=CosineDistance('embedding', query_embedding))
        .filter(embedding__isnull=False)
        .order_by('distance')[:3]
    )
    count = len(similar_books)
    print(f"   Found {count} books in {time.time() - s3:.2f}s")
    
    # 4. Ollama Call
    print("\n4. Calling LLM (DeepSeek-Coder)...")
    s4 = time.time()
    recommendations = get_recommendations_by_query(query, top_k=3)
    print(f"   LLM call finished in {time.time() - s4:.2f}s")
    
    print(f"\nTotal Time: {time.time() - total_start:.2f}s")
    print("\nResults:")
    print(json.dumps(recommendations, indent=2))

if __name__ == "__main__":
    test_query_recommendations_detailed()
