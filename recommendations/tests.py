from django.test import TestCase
from django.contrib.auth.models import User
from recommendations.models import Book, Purchase
from recommendations.rag import get_recommendations, get_sentence_transformer_model
from unittest.mock import patch, MagicMock
import numpy as np


class BookModelTestCase(TestCase):
    """Test cases for Book model"""
    
    def test_book_creation(self):
        """Test creating a book"""
        book = Book.objects.create(
            title='Test Book',
            author='Test Author',
            description='A test book description',
            subjects='Fiction, Adventure'
        )
        
        self.assertEqual(book.title, 'Test Book')
        self.assertEqual(book.author, 'Test Author')
        self.assertIsNone(book.embedding)
    
    def test_book_with_embedding(self):
        """Test book with embedding"""
        embedding = np.random.rand(384).tolist()
        book = Book.objects.create(
            title='Book with Embedding',
            author='Author Name',
            description='Description',
            embedding=embedding
        )
        
        self.assertIsNotNone(book.embedding)
        self.assertEqual(len(book.embedding), 384)
    
    def test_book_string_representation(self):
        """Test book __str__ method"""
        book = Book.objects.create(
            title='String Test',
            author='Author',
            description='Desc'
        )
        
        # Should return 'Book - {id}'
        self.assertTrue(str(book).startswith('Book - '))


class PurchaseModelTestCase(TestCase):
    """Test cases for Purchase model"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass'
        )
        self.book = Book.objects.create(
            title='Purchased Book',
            author='Author',
            description='Description'
        )
    
    def test_purchase_creation(self):
        """Test creating a purchase"""
        purchase = Purchase.objects.create(
            user=self.user,
            book=self.book
        )
        
        self.assertEqual(purchase.user, self.user)
        self.assertEqual(purchase.book, self.book)
        self.assertIsNotNone(purchase.purchase_date)
    
    def test_purchase_string_representation(self):
        """Test purchase __str__ method"""
        purchase = Purchase.objects.create(
            user=self.user,
            book=self.book
        )
        
        # Should return 'Purchase - {id}'
        self.assertTrue(str(purchase).startswith('Purchase - '))


class RAGRecommendationTestCase(TestCase):
    """Test cases for RAG recommendation system"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='raguser',
            email='rag@example.com',
            password='testpass'
        )
        
        # Create books with embeddings
        self.book1 = Book.objects.create(
            title='Science Fiction Book',
            author='Sci-Fi Author',
            description='A great science fiction novel',
            subjects='Science Fiction',
            embedding=np.random.rand(384).tolist()
        )
        self.book2 = Book.objects.create(
            title='Fantasy Book',
            author='Fantasy Author',
            description='An epic fantasy adventure',
            subjects='Fantasy',
            embedding=np.random.rand(384).tolist()
        )
        self.book3 = Book.objects.create(
            title='Mystery Book',
            author='Mystery Author',
            description='A thrilling mystery',
            subjects='Mystery',
            embedding=np.random.rand(384).tolist()
        )
    
    def test_no_purchases(self):
        """Test recommendations for user with no purchases"""
        result = get_recommendations(self.user.id, top_k=3)
        
        self.assertIsInstance(result, str)
        self.assertIn('No purchases yet', result)
    
    def test_invalid_user(self):
        """Test recommendations for invalid user ID"""
        result = get_recommendations(99999, top_k=3)
        
        self.assertIsInstance(result, str)
        self.assertIn('Invalid user', result)
    
    def test_recommendations_with_purchases(self):
        """Test recommendations for user with purchase history"""
        # Create purchase
        Purchase.objects.create(user=self.user, book=self.book1)
        
        # Mock the LLM to avoid actual API calls
        with patch('recommendations.rag.ChatOllama') as mock_llm:
            mock_chain = MagicMock()
            mock_chain.invoke.return_value = "Recommended books: Fantasy Book, Mystery Book"
            mock_llm.return_value = mock_chain
            
            result = get_recommendations(self.user.id, top_k=2)
            
            self.assertIsInstance(result, str)
            # Should not be an error message
            self.assertNotIn('No purchases', result)
            self.assertNotIn('Invalid user', result)
    
    def test_recommendations_caching(self):
        """Test that recommendations are cached"""
        Purchase.objects.create(user=self.user, book=self.book1)
        
        with patch('recommendations.rag.ChatOllama') as mock_llm:
            mock_chain = MagicMock()
            mock_chain.invoke.return_value = "Cached recommendations"
            mock_llm.return_value = mock_chain
            
            # First call - should hit LLM
            result1 = get_recommendations(self.user.id, top_k=2)
            call_count_1 = mock_chain.invoke.call_count
            
            # Second call - should use cache
            result2 = get_recommendations(self.user.id, top_k=2)
            call_count_2 = mock_chain.invoke.call_count
            
            # Results should be the same
            self.assertEqual(result1, result2)
            # Second call should not invoke LLM again
            self.assertEqual(call_count_1, call_count_2)
    
    def test_no_embeddings_available(self):
        """Test when books have no embeddings"""
        # Create book without embedding
        book_no_embedding = Book.objects.create(
            title='No Embedding Book',
            author='Author',
            description='Description',
            embedding=None
        )
        Purchase.objects.create(user=self.user, book=book_no_embedding)
        
        result = get_recommendations(self.user.id, top_k=3)
        
        self.assertIsInstance(result, str)
        self.assertIn('No embeddings available', result)
    
    def test_llm_failure_fallback(self):
        """Test fallback when LLM fails"""
        Purchase.objects.create(user=self.user, book=self.book1)
        
        # Mock LLM to raise an exception
        with patch('recommendations.rag.ChatOllama') as mock_llm:
            mock_llm.side_effect = Exception("LLM connection failed")
            
            result = get_recommendations(self.user.id, top_k=2)
            
            # Should return fallback message with book list
            self.assertIsInstance(result, str)
            self.assertIn('Based on your reading history', result)
    
    def test_model_caching(self):
        """Test that SentenceTransformer model is cached"""
        # Call the function twice
        model1 = get_sentence_transformer_model()
        model2 = get_sentence_transformer_model()
        
        # Should return the same instance
        self.assertIs(model1, model2)


class RAGEdgeCasesTestCase(TestCase):
    """Test edge cases in RAG system"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='edgeuser',
            email='edge@example.com',
            password='testpass'
        )
    
    def test_empty_top_k(self):
        """Test with top_k=0"""
        book = Book.objects.create(
            title='Test',
            author='Author',
            description='Desc',
            embedding=np.random.rand(384).tolist()
        )
        Purchase.objects.create(user=self.user, book=book)
        
        # Should handle gracefully
        result = get_recommendations(self.user.id, top_k=0)
        self.assertIsInstance(result, str)
    
    def test_large_top_k(self):
        """Test with very large top_k"""
        book = Book.objects.create(
            title='Test',
            author='Author',
            description='Desc',
            embedding=np.random.rand(384).tolist()
        )
        Purchase.objects.create(user=self.user, book=book)
        
        # Should handle gracefully even if top_k > available books
        result = get_recommendations(self.user.id, top_k=1000)
        self.assertIsInstance(result, str)
    
    def test_multiple_purchases_same_book(self):
        """Test user purchasing same book multiple times"""
        book = Book.objects.create(
            title='Popular Book',
            author='Author',
            description='Desc',
            embedding=np.random.rand(384).tolist()
        )
        
        # Create multiple purchases of same book
        Purchase.objects.create(user=self.user, book=book)
        Purchase.objects.create(user=self.user, book=book)
        
        with patch('recommendations.rag.ChatOllama') as mock_llm:
            mock_chain = MagicMock()
            mock_chain.invoke.return_value = "Recommendations"
            mock_llm.return_value = mock_chain
            
            result = get_recommendations(self.user.id, top_k=3)
            
            # Should handle duplicate purchases
            self.assertIsInstance(result, str)
