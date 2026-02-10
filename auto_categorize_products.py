import os
import django
import sys
import time

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecom.settings')
django.setup()

from store.models import Product, Category
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Configuration
DEFAULT_CATEGORY_NAME = "Books" # The catch-all category we want to move items FROM

# Predefined categories to guide the LLM
CATEGORIES = [
    "Fiction",
    "Non-Fiction",
    "Mystery & Thriller",
    "Science Fiction & Fantasy",
    "Romance",
    "History",
    "Biography & Memoir",
    "Business & Economics",
    "Self-Help",
    "Science & Nature",
    "Children's Books",
    "Poetry",
    "Art & Photography",
    "Travel",
    "Religion & Spirituality",
    "Cooking & Food",
    "Health & Wellness",
    "Computers & Technology",
    "Politics & Social Sciences"
]

def auto_categorize():
    print("Initializing AI Categorizer...")
    
    # Initialize LLM
    try:
        llm = ChatOllama(
            model="llama3.1:8b", 
            temperature=0.0, # Deterministic output
            base_url=os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        )
    except Exception as e:
        print(f"Error initializing LLM: {e}")
        return

    # Get the default category to filter products
    try:
        default_cat = Category.objects.get(name=DEFAULT_CATEGORY_NAME)
    except Category.DoesNotExist:
        print(f"Default category '{DEFAULT_CATEGORY_NAME}' not found.")
        # Fallback: Get all products or category 1
        default_cat = Category.objects.first()
        if not default_cat:
            print("No categories found at all. Creating default 'Books'...")
            default_cat = Category.objects.create(name="Books", description="All books")
            # If we just created it, likely all products need to be assigned to it first? 
            # Assuming sync script ran previously.
    
    # Statistics
    total_products = Product.objects.count()
    # Filter only products that are still in the default category
    products_to_process_qs = Product.objects.filter(category=default_cat)
    uncategorized_count = products_to_process_qs.count()
    categorized_count = total_products - uncategorized_count
    
    print("-" * 50)
    print(f"Total Products: {total_products}")
    print(f"Already Categorized: {categorized_count} (Skipping)")
    print(f"Remaining to Process: {uncategorized_count} (In '{default_cat.name}')")
    print("-" * 50)
    
    if uncategorized_count == 0:
        print("All products have been categorized! Exiting.")
        return

    prompt = ChatPromptTemplate.from_template(
        """You are a helpful librarian.
        Classify the following book into exactly ONE of these categories:
        {category_list}

        Book Title: {title}
        Book Description: {description}

        Return ONLY the category name from the list above. Do not add any punctuation or extra text."""
    )
    
    chain = prompt | llm | StrOutputParser()
    
    cat_list_str = ", ".join(CATEGORIES)
    
    # Using iterator to handle large queryset memory efficiently
    # and to ensure we process the current state
    count = 0
    success_count = 0
    
    start_time = time.time()
    
    for product in products_to_process_qs.iterator():
        count += 1
        try:
            print(f"[{count}/{uncategorized_count}] Categorizing: {product.name[:40]}...", end=" ", flush=True)
            
            # Double check inside loop in case of race conditions or restarts (redundant but safe)
            if product.category.name != DEFAULT_CATEGORY_NAME:
                print("Skipped (Already done)")
                continue

            description = product.description or "No description available"
            
            # Invoke LLM
            response = chain.invoke({
                "category_list": cat_list_str,
                "title": product.name,
                "description": description[:500] 
            })
            
            category_name = response.strip()
            
            # Validate
            matched_category = None
            for cat in CATEGORIES:
                if cat.lower() in category_name.lower():
                    matched_category = cat
                    break
            
            if not matched_category:
                matched_category = "Non-Fiction" # Fallback
                print(f"[Fallback: {category_name} -> {matched_category}]", end=" ")
            
            # Get or Create Category
            category_obj, _ = Category.objects.get_or_create(
                name=matched_category,
                defaults={'description': f'Books in the {matched_category} genre'}
            )
            
            # Update Product
            product.category = category_obj
            product.save()
            
            success_count += 1
            print(f"-> {matched_category}")
            
        except Exception as e:
            print(f"\nError processing {product.id}: {e}")

    elapsed = time.time() - start_time
    print("-" * 50)
    print(f"Job Complete!")
    print(f"Processed: {success_count}/{uncategorized_count}")
    print(f"Time Taken: {elapsed:.2f} seconds")

if __name__ == "__main__":
    auto_categorize()
