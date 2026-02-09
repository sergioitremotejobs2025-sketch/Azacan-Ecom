import os
import django
import sys

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecom.settings')
django.setup()

from store.models import Product, Category
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Configuration
BATCH_SIZE = 20  # Number of products to process in this run
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
            print("No categories found at all. Converting generic setup...")
            default_cat = Category.objects.create(name="Books", description="All books")
    
    print(f"Looking for products in category: '{default_cat.name}'")
    
    # Filter products that need categorization
    # We take a slice to avoid processing 9000 items in one go during testing
    products_to_process = Product.objects.filter(category=default_cat)[:BATCH_SIZE]
    
    if not products_to_process:
        print("No products found to categorize (or all are already categorized).")
        return

    print(f"Processing batch of {len(products_to_process)} products...")

    prompt = ChatPromptTemplate.from_template(
        """You are a helpful librarian.
        Classify the following book into exactly ONE of these categories:
        {category_list}

        Book Title: {title}
        Book Description: {description}

        Return ONLY the category name from the list above. Do not add any punctuation or extra text."""
    )
    
    chain = prompt | llm | StrOutputParser()
    
    success_count = 0
    
    for product in products_to_process:
        try:
            print(f"Categorizing: {product.name[:50]}...")
            
            # Prepare context
            cat_list_str = ", ".join(CATEGORIES)
            description = product.description or "No description available"
            
            # Update output directly in loop
            response = chain.invoke({
                "category_list": cat_list_str,
                "title": product.name,
                "description": description[:500] # Truncate long descriptions
            })
            
            category_name = response.strip()
            
            # Simple validation: Check if response vaguely matches a known category
            # If the LLM returns "Science Fiction", it matches exactly.
            # If it returns "It is Fiction", we might have issues. 
            # With temperature 0 and strict prompt, it usually behaves.
            
            # Handle potential hallucinations or slightly off text
            matched_category = None
            for cat in CATEGORIES:
                if cat.lower() in category_name.lower():
                    matched_category = cat
                    break
            
            if not matched_category:
                # Fallback if LLM invented a category or failed strict match
                print(f"  -> LLM suggested '{category_name}', defaulting to 'Non-Fiction' (Unsure)")
                matched_category = "Non-Fiction" # Safe fallback
            
            # Get or Create the Category in DB
            category_obj, created = Category.objects.get_or_create(
                name=matched_category,
                defaults={'description': f'Books in the {matched_category} genre'}
            )
            
            # Assign to product
            product.category = category_obj
            product.save()
            
            print(f"  -> Assigned to: {matched_category}")
            success_count += 1
            
        except Exception as e:
            print(f"  -> Failed to categorize {product.id}: {e}")

    print(f"\nBatch complete! Successfully categorized {success_count}/{len(products_to_process)} products.")

if __name__ == "__main__":
    auto_categorize()
