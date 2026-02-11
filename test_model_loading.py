import os
import django
import time

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecom.settings')
django.setup()

from sentence_transformers import SentenceTransformer

def test_model_loading():
    print("Loading SentenceTransformer model 'all-MiniLM-L6-v2'...")
    start_time = time.time()
    model = SentenceTransformer('all-MiniLM-L6-v2')
    duration = time.time() - start_time
    print(f"Model loaded in {duration:.2f} seconds")

if __name__ == "__main__":
    test_model_loading()
