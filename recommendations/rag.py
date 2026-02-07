import os
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
    cache_key = f"recommendations_{user_id}_{top_k}"
    cached_result = cache.get(cache_key)
    if cached_result:
        logger.info(f"Returning cached recommendations for user {user_id}")
        return cached_result
    
    try:
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
        
        # Retrieve similar books (exclude past purchases)
        similar_books = Book.objects.exclude(id__in=past_books).annotate(
            distance=CosineDistance('embedding', average_embedding)
        ).order_by('distance')[:top_k]
        #return similar_books
        
        if not similar_books:
            return "No similar books found. Try browsing our catalog for new discoveries!"
        
        # Format retrieved books for context
        context = "\n".join([
            f"Title: {b.title}, Author: {b.author}, Description: {b.description}" 
            for b in similar_books
        ])
        #context = "Title: test, Author: test, Description: test"
        #return context
        # LLM generation
        try:
            llm = ChatOllama(model="llama3.1:8b", base_url=os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434'))
            prompt = ChatPromptTemplate.from_template(
            """You are an expert at formatting book recommendations in clean HTML.

                Here is a list of books to recommend:

                {context}

                Return ONLY a valid HTML snippet containing an unordered list of recommendations.
                Use this exact structure:
                - Start directly with <ul>
                - Each book as <li><strong>Title</strong> by Author - short 1-sentence reason -- Add an detailed explanation of why each book is recommended.</li>
                - End with </ul>

                Do NOT include any text outside the HTML.
                Do NOT use markdown, code blocks, or backticks.
                Do NOT add headings, paragraphs, or explanations.
                Do NOT wrap in ```html tags.

                Begin your response directly with <ul>"""
            )
            chain = prompt | llm | StrOutputParser()
            recommendation = chain.invoke({"context": context})
            
            # Cache the result for 1 hour
            cache.set(cache_key, recommendation, 3600)
            
            return recommendation
            
        except Exception as llm_error:
            logger.error(f"LLM generation failed for user {user_id}: {llm_error}")
            # Fallback: return simple list if LLM fails
            fallback = "Based on your reading history, you might enjoy:\n\n"
            fallback += "\n".join([f"- {b.title} by {b.author}" for b in similar_books])
            return fallback
    
    except Exception as e:
        logger.error(f"Error generating recommendations for user {user_id}: {e}")
        return "We're having trouble generating recommendations right now. Please try again later."

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
            llm = ChatOllama(model="llama3.1:8b", temperature=0.7, base_url=os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434'))
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


def get_recommendations_by_query(query: str, top_k: int = 5) -> str:
    """
    Generate book recommendations based on a natural language query using vector similarity (RAG-style).

    Args:
        query (str): The search query or explanation of the topic
        top_k (int): Number of similar books to retrieve (default: 5)

    Returns:
        str: LLM-generated recommendations in HTML format or fallback message
    """
    cache_key = f"recommendations_query_{hash(query)}_{top_k}"
    cached_result = cache.get(cache_key)
    if cached_result:
        logger.info(f"Cache hit for query recommendations: {query[:50]}...")
        return cached_result

    try:
        # Step 1: Generate embedding for the query
        model = get_sentence_transformer_model()
        query_embedding = model.encode(query).tolist()

        # Step 2: Retrieve top_k similar books
        similar_books = (
            Book.objects.annotate(distance=CosineDistance('embedding', query_embedding))
            .filter(embedding__isnull=False)  # Ensure valid embeddings
            .order_by('distance')[:top_k]
        )

        if not similar_books:
            return "No similar books found for your query. Try searching for something else!"

        # Step 3: Format context for LLM
        context_lines = []
        for b in similar_books:
            author = b.author or "Unknown Author"
            description = b.description or "No description available."
            context_lines.append(f"Title: {b.title}\nAuthor: {author}\nDescription: {description}\n")

        context = "\n".join(context_lines)

        # Step 4: Generate recommendations using LLM
        try:
            llm = ChatOllama(model="llama3.1:8b", temperature=0.7, base_url=os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434'))
            prompt = ChatPromptTemplate.from_template(
                """You are a helpful bookstore assistant. 
                    A customer is looking for books based on the following request: "{query}".

                    Here are some books from our catalog that might match their interests:

                    {context}

                    Recommend 3-5 books from the list above that best match the customer's request.
                    For each book, provide a detailed explanation of why it fits the specific query provided.

                    Format your response as an HTML unordered list (<ul><li>...</li></ul>).
                    Each list item should follow this structure: <li><strong>Title</strong> by Author - Reason for recommendation</li>.
                    Do not include any text outside the HTML tags."""
            )

            chain = prompt | llm | StrOutputParser()
            recommendation = chain.invoke({
                "query": query,
                "context": context
            })

            # Cache successful result for 1 hour
            cache.set(cache_key, recommendation, timeout=3600)
            return recommendation

        except Exception as llm_error:
            logger.error(f"LLM generation failed for query '{query[:50]}...': {llm_error}")
            # Fallback: simple formatted list
            fallback = "<ul>"
            for b in similar_books:
                author = b.author or "Unknown Author"
                fallback += f"<li><strong>{b.title}</strong> by {author}</li>"
            fallback += "</ul>"
            return f"<p>Based on your search, you might enjoy:</p>{fallback}"

    except Exception as e:
        logger.error(f"Unexpected error in query recommendations for '{query[:50]}...': {str(e)}")
        return "We're having trouble generating recommendations for your query right now. Please try again later."