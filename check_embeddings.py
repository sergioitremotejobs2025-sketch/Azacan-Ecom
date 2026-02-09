import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecom.settings')
django.setup()

from recommendations.models import Book

count = Book.objects.count()
embedded_count = Book.objects.filter(embedding__isnull=False).count()

print(f"Total books: {count}")
print(f"Books with embeddings: {embedded_count}")

if embedded_count == 0:
    print("WARNING: No embeddings found. Semantic search will not return results.")
