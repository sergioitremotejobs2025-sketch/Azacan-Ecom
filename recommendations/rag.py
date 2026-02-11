import os
import re
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from langchain_core.output_parsers import StrOutputParser
from pgvector.django import CosineDistance
from recommendations.models import Book, Purchase
from sentence_transformers import SentenceTransformer
from django.core.cache import cache
from django.contrib.auth.models import User
import numpy as np
import logging

logger = logging.getLogger(__name__)

# Singleton pattern for model caching
_model_cache = None

def get_sentence_transformer_model():
    """
    Get or create a cached SentenceTransformer model.
    Uses module-level singleton pattern to avoid reloading on every request.
    """
    global _model_cache
    if _model_cache is None:
        logger.info("Loading SentenceTransformer model 'all-MiniLM-L6-v2'...")
        _model_cache = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("Model loaded successfully")
    return _model_cache


def get_recommendations(user_id, top_k=3):
    """
    Generate book recommendations for a user based on their purchase history using RAG.
    
    Args:
        user_id (int): The ID of the user to generate recommendations for
        top_k (int): Number of similar books to retrieve (default: 5)
    
    Returns:
        str: LLM-generated recommendations or error message
    
    Raises:
        None: All exceptions are caught and returned as user-friendly messages
    """
    # Check cache first
    cache_key = f"recommendations_v5_{user_id}_{top_k}"
    cached_result = cache.get(cache_key)
    if cached_result:
        logger.info(f"Returning cached recommendations for user {user_id}")
        return cached_result
    
    try:
        # Import Product model to map Book -> Product via reference
        from store.models import Product
        
        # Validate user exists
        if not User.objects.filter(id=user_id).exists():
            return "Invalid user ID."
        
        # Get past purchases
        past_books = Purchase.objects.filter(user_id=user_id).values_list('book_id', flat=True)
        
        if not past_books:
            return "No purchases yet. Browse our catalog!"
        
        # Get embeddings for past purchases
        past_embeddings = Book.objects.filter(id__in=past_books).values_list('embedding', flat=True)
        
        # Filter out None embeddings
        valid_embeddings = [emb for emb in past_embeddings if emb is not None]
        
        if not valid_embeddings:
            return "No embeddings available for your past purchases. Please check back later as we process your books."
        
        # Calculate average embedding
        average_embedding = np.mean(valid_embeddings, axis=0)
        
        # Retrieve larger pool of similar books for diversity (e.g. top 20)
        candidate_books = list(Book.objects.exclude(id__in=past_books).annotate(
            distance=CosineDistance('embedding', average_embedding)
        ).order_by('distance')[:20])
        
        if not candidate_books:
            return "No similar books found. Try browsing our catalog for new discoveries!"
            
        import random
        # Randomly sample top_k from the candidates to provide variety
        sample_size = min(len(candidate_books), top_k)
        similar_books = random.sample(candidate_books, sample_size)
        
        # Sort them back by distance
        similar_books.sort(key=lambda x: x.distance)
        
        # Build a reference -> Product ID lookup for the selected books
        book_references = [b.reference for b in similar_books if b.reference]
        product_map = {}
        if book_references:
            products = Product.objects.filter(reference__in=book_references).values_list('reference', 'id')
            product_map = {ref: pid for ref, pid in products}
        
        # Format retrieved books for context
        context = "\n".join([
            f"Title: {b.title}, Author: {b.author}, Description: {b.description}" 
            for b in similar_books
        ])
        
        # LLM generation
        try:
            llm = ChatOllama(model="DeepSeek-Coder:latest", temperature=0.7, base_url=os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434'))
            prompt = ChatPromptTemplate.from_template(
            """You are a helpful book expert.
            
                Here are {count} books recommended for a user:
                {context}

                Write a short, engaging 1-sentence reason for recommending EACH book.
                
                Return the reasons as a list valid JSON strings.
                Example format: ["Reason for book 1", "Reason for book 2", "Reason for book 3"]
                
                Strictly return ONLY the JSON list. No other text.
            """
            )
            chain = prompt | llm | StrOutputParser()
            response_text = chain.invoke({"context": context, "count": len(similar_books)})
            
            import json
            try:
                # Strip think blocks and markdown code tags
                clean_json = re.sub(r'<think>.*?</think>', '', response_text, flags=re.DOTALL)
                clean_json = clean_json.replace("```json", "").replace("```", "").strip()
                reasons = json.loads(clean_json)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse LLM JSON response: {response_text}")
                reasons = [f"Recommended because it's similar to your taste." for _ in similar_books]

            if len(reasons) < len(similar_books):
                 reasons.extend([f"A great choice based on your history." for _ in range(len(similar_books) - len(reasons))])
            
            # Construct structured result with Product ID for cart integration
            structured_recommendations = []
            for i, book in enumerate(similar_books):
                product_id = product_map.get(book.reference)
                if product_id:  # Only include if we can map to a Product
                    structured_recommendations.append({
                        'book': book,
                        'product_id': product_id,
                        'reason': reasons[i]
                    })

            cache.set(cache_key, structured_recommendations, 3600)
            return structured_recommendations
            
        except Exception as llm_error:
            logger.error(f"LLM generation failed for user {user_id}: {llm_error}")
            fallback = []
            for b in similar_books:
                product_id = product_map.get(b.reference)
                if product_id:
                    fallback.append({'book': b, 'product_id': product_id, 'reason': "Recommended based on your history."})
            return fallback
    
    except Exception as e:
        logger.error(f"Error generating recommendations for user {user_id}: {e}")
        return [] # Return empty list on error


def get_recommendations_by_book_title(book_title: str, top_k: int = 5) -> str:
    """
    Generate book recommendations based on a given book title using vector similarity (RAG-style).

    Args:
        book_title (str): The title of the book to find similar books for
        top_k (int): Number of similar books to retrieve (default: 5)

    Returns:
        str: LLM-generated recommendations in HTML format or fallback message
    """
    cache_key = f"recommendations_title_{book_title.lower()}_{top_k}"
    cached_result = cache.get(cache_key)
    if cached_result:
        logger.info(f"Cache hit for recommendations: {book_title}")
        return cached_result

    try:
        # Step 1: Find the reference book by title
        try:
            reference_book = Book.objects.get(title__iexact=book_title)
        except Book.DoesNotExist:
            return f"Sorry, we couldn't find a book titled '{book_title}' in our catalog."
        except Book.MultipleObjectsReturned:
            # Use the first match if multiple
            reference_book = Book.objects.filter(title__iexact=book_title).first()

        if reference_book.embedding is None:
            return f"We don't have embedding data for '{book_title}' yet. Please try another book."

        reference_embedding = reference_book.embedding

        # Step 2: Retrieve top_k similar books (excluding the reference book itself)
        similar_books = (
            Book.objects.exclude(id=reference_book.id)
            .annotate(distance=CosineDistance('embedding', reference_embedding))
            .filter(embedding__isnull=False)  # Ensure valid embeddings
            .order_by('distance')[:top_k]
        )

        if not similar_books:
            return "No similar books found at this time. Try browsing our catalog!"

        # Step 3: Format context for LLM
        context_lines = []
        for b in similar_books:
            author = b.author or "Unknown Author"
            description = b.description or "No description available."
            context_lines.append(f"Title: {b.title}\nAuthor: {author}\nDescription: {description}\n")

        context = "\n".join(context_lines)

        # Step 4: Generate recommendations using LLM
        try:
            llm = ChatOllama(model="DeepSeek-Coder:latest", temperature=0.7, base_url=os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434'))
            prompt = ChatPromptTemplate.from_template(
                """You are a knowledgeable bookstore assistant. 
                    A customer enjoyed the book titled "{book_title}".

                    Here are some similar books from our catalog:

                    {context}

                    Recommend 3-5 books from the list above that this customer might enjoy next.
                    Explain briefly why each one is a good recommendation based on similarity to the original book.

                    Format your response as an HTML unordered list (<ul><li>...</li></ul>) with bold titles.
                    Do not recommend books outside this list."""
            )

            chain = prompt | llm | StrOutputParser()
            recommendation = chain.invoke({
                "book_title": book_title,
                "context": context
            })

            # Cache successful result for 1 hour
            cache.set(cache_key, recommendation, timeout=3600)
            return recommendation

        except Exception as llm_error:
            logger.error(f"LLM generation failed for book '{book_title}': {llm_error}")
            # Fallback: simple formatted list
            fallback = "<ul>"
            for b in similar_books:
                author = b.author or "Unknown Author"
                fallback += f"<li><strong>{b.title}</strong> by {author}</li>"
            fallback += "</ul>"
            return f"<p>You might also enjoy:</p>{fallback}"

    except Exception as e:
        logger.error(f"Unexpected error in recommendations for '{book_title}': {str(e)}")
        return "We're having trouble generating recommendations right now. Please try again later or browse our catalog."


def get_similar_books(query: str, top_k: int = 5):
    """
    Retrieve top_k similar books from the database using vector similarity.
    """
    model = get_sentence_transformer_model()
    query_embedding = model.encode(query).tolist()

    return (
        Book.objects.annotate(distance=CosineDistance('embedding', query_embedding))
        .filter(embedding__isnull=False)
        .order_by('distance')[:top_k]
    )

def get_recommendation_prompt():
    return ChatPromptTemplate.from_template(
        """Below is a list of books retrieved from a database for the query: "{query}"
           CONTEXT:
           {context}

           TASK: Professional Bookstore AI. provide a JSON list of short matching reasons (1 sentence each).
           FORMAT: ["Reason 1", "Reason 2", ...]
           RULES:
           - Return ONLY valid JSON.
           - No introductory or concluding text.
           - No explanations of why you can't access real-time data (you are already provided the data).
        """
    )

def get_recommendations_by_query_stream(query: str, top_k: int = 5):
    """
    Generate book recommendations based on a natural language query using vector similarity (RAG-style).
    Yields chunks of the LLM response for streaming.
    """
    try:
        similar_books = get_similar_books(query, top_k)
        logger.info(f"Stream: Found {similar_books.count()} similar books for query: {query}")
        if not similar_books:
            yield "[]"
            return

        context = "\n".join([f"Title: {b.title}, Author: {b.author}, Description: {b.description}" for b in similar_books])
        
        llm = ChatOllama(model="deepseek-r1:1.5b", temperature=0.1, base_url=os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434'))
        prompt = get_recommendation_prompt()
        chain = prompt | llm | StrOutputParser()
        
        in_think = False
        buffer = ""
        
        for chunk in chain.stream({"query": query, "context": context}):
            buffer += chunk
            
            # Simple state machine to skip <think> blocks
            if not in_think:
                if "<think>" in buffer:
                    # Found start of think block
                    parts = buffer.split("<think>", 1)
                    if parts[0]:
                        yield parts[0]
                    buffer = "" # Rest will be handled after </think>
                    in_think = True
                else:
                    # No think block yet, stream what we have
                    yield buffer
                    buffer = ""
            
            if in_think:
                if "</think>" in buffer:
                    # Found end of think block
                    parts = buffer.split("</think>", 1)
                    buffer = parts[1] # Keep what's after </think>
                    in_think = False
                    # Don't yield yet, let the next iteration handle it (or yield if it's the end)
        
        if buffer and not in_think:
             yield buffer

    except Exception as e:
        logger.error(f"Streaming failed: {e}")
        yield f"Error: {str(e)}"

def get_recommendations_by_query(query: str, top_k: int = 5):
    """
    Generate book recommendations based on a natural language query using vector similarity (RAG-style).
    """
    cache_key = f"recommendations_query_v3_{hash(query)}_{top_k}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result

    try:
        similar_books = get_similar_books(query, top_k)
        logger.info(f"Found {similar_books.count()} similar books for query: {query}")
        if not similar_books:
            return []

        context = "\n".join([f"Title: {b.title}, Author: {b.author}, Description: {b.description}" for b in similar_books])
        
        llm = ChatOllama(model="deepseek-r1:1.5b", temperature=0.1, base_url=os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434'))
        prompt = get_recommendation_prompt()
        chain = prompt | llm | StrOutputParser()
        
        response_text = chain.invoke({"query": query, "context": context})

        import json
        try:
            # Strip think blocks and markdown code tags
            clean_json = re.sub(r'<think>.*?</think>', '', response_text, flags=re.DOTALL)
            clean_json = clean_json.replace("```json", "").replace("```", "").strip()
            reasons = json.loads(clean_json)
        except (json.JSONDecodeError, ValueError):
            logger.warning(f"Failed to parse LLM JSON: {response_text}")
            reasons = ["Highly relevant matching based on your query." for _ in similar_books]

        if len(reasons) < len(similar_books):
            reasons.extend(["A great match for your interests." for _ in range(len(similar_books) - len(reasons))])

        structured_recommendations = []
        for i, book in enumerate(similar_books):
            structured_recommendations.append({
                'title': book.title,
                'author': book.author,
                'description': book.description,
                'reference': book.reference,
                'reason': reasons[i] if i < len(reasons) else "A great choice."
            })

        cache.set(cache_key, structured_recommendations, timeout=3600)
        return structured_recommendations

    except Exception as e:
        logger.error(f"Unexpected error in query recommendations: {str(e)}")
        return []
        
def search_books(query: str, top_k: int = 5):
    """
    Search for books using vector similarity.
    Returns: QuerySet of Book objects
    """
    try:
        model = get_sentence_transformer_model()
        query_embedding = model.encode(query).tolist()
        
        similar_books = (
            Book.objects.annotate(distance=CosineDistance('embedding', query_embedding))
            .filter(embedding__isnull=False)
            .order_by('distance')[:top_k]
        )
        return similar_books
    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        return Book.objects.none()