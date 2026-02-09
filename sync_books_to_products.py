import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecom.settings')
django.setup()

from store.models import Product, Category
from recommendations.models import Book
import random

def sync_books_to_products():
    print("Syncing Books to Products...")
    
    # Create a default category if none exists
    category, created = Category.objects.get_or_create(name="Books", defaults={"description": "All Books"})
    if created:
        print(f"Created default category: {category}")
    else:
        print(f"Using existing category: {category}")

    books = Book.objects.all()
    count = 0
    
    # Use bulk_create for efficiency, but need to check existing first to avoid dupes or handle them
    # For simplicity in this script, let's iterate and create if not exists
    
    existing_products = set(Product.objects.values_list('name', flat=True))
    
    products_to_create = []
    
    print(f"Found {books.count()} books. creating products for them...")
    
    for book in books:
        if book.title not in existing_products:
            # Generate a random price between 10 and 50 if missing
            price = book.price if book.price else random.uniform(10.0, 50.0)
            
            product = Product(
                name=book.title,
                price=price,
                category=category,
                description=book.description or f"Book by {book.author}",
                image=book.image, # Assuming image field is compatible or just path
                is_sale=False,
                sale_price=0,
                reference=book.reference,
                # publisher=book.publisher, # Book model doesn't have publisher field in updated view? let's skip for now
                # year=book.year, 
            )
            products_to_create.append(product)
            count += 1
            
            # Batch create every 1000
            if len(products_to_create) >= 1000:
                Product.objects.bulk_create(products_to_create)
                print(f"Created batch of {len(products_to_create)} products.")
                products_to_create = []

    if products_to_create:
        Product.objects.bulk_create(products_to_create)
        print(f"Created final batch of {len(products_to_create)} products.")

    print(f"Sync complete. Added {count} new products.")

if __name__ == "__main__":
    sync_books_to_products()
