import os
import django
import time

print("Starting Django setup...")
start_time = time.time()
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecom.settings')
django.setup()
print(f"Django setup finished in {time.time() - start_time:.2f} seconds")
