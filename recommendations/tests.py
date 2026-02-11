from django.test import TestCase
from django.contrib.auth.models import User
from recommendations.models import Book, Purchase
from store.models import Product, Category
from recommendations.rag import get_recommendations, get_sentence_transformer_model
from unittest.mock import patch, MagicMock
import numpy as np
import pydantic

# Create a mock that passes Pydantic validation
class MockableMagicMock(MagicMock):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v, info=None):
        return v

# Patch MagicMock to include Pydantic validation if needed, or just use our subclass
# For simplicity in this test file, we'll use our subclass or just patch the validation 
# behavior if we can, but modifying the test setup is safer.


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
        
        # Should return descriptive string
        self.assertIn('String Test', str(book))
        self.assertIn('Author', str(book))


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
        
        # Create category
        self.category = Category.objects.create(name='Test Category', description='Test')
        
        # Create books with embeddings and matching products
        self.book1 = Book.objects.create(
            title='Science Fiction Book',
            author='Sci-Fi Author',
            description='A great science fiction novel',
            subjects='Science Fiction',
            reference='REF1',
            embedding=np.random.rand(384).tolist()
        )
        Product.objects.create(name=self.book1.title, reference='REF1', category=self.category, price=10.0)
        
        self.book2 = Book.objects.create(
            title='Fantasy Book',
            author='Fantasy Author',
            description='An epic fantasy adventure',
            subjects='Fantasy',
            reference='REF2',
            embedding=np.random.rand(384).tolist()
        )
        Product.objects.create(name=self.book2.title, reference='REF2', category=self.category, price=12.0)
        
        self.book3 = Book.objects.create(
            title='Mystery Book',
            author='Mystery Author',
            description='A thrilling mystery',
            subjects='Mystery',
            reference='REF3',
            embedding=np.random.rand(384).tolist()
        )
        Product.objects.create(name=self.book3.title, reference='REF3', category=self.category, price=15.0)
    
    def test_no_purchases(self):
        """Test recommendations for user with no purchases"""
        result = get_recommendations(self.user.id, top_k=3)
        
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)
    
    def test_invalid_user(self):
        """Test recommendations for invalid user ID"""
        result = get_recommendations(99999, top_k=3)
        
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)
    
    def test_recommendations_with_purchases(self):
        """Test recommendations for user with purchase history"""
        # Create purchase
        Purchase.objects.create(user=self.user, book=self.book1)
        
        with patch('recommendations.rag.ChatOllama') as mock_llm_cls:
            mock_llm_instance = MockableMagicMock()
            mock_llm_cls.return_value = mock_llm_instance
            
            with patch('recommendations.rag.ChatPromptTemplate') as mock_prompt_cls:
                mock_prompt = MagicMock()
                mock_prompt_cls.from_template.return_value = mock_prompt
                
                mock_intermediate = MagicMock()
                mock_prompt.__or__.return_value = mock_intermediate
                
                mock_chain = MagicMock()
                mock_intermediate.__or__.return_value = mock_chain
                
                # DeepSeek-style response with think block and JSON list
                mock_chain.invoke.return_value = '<think>Parsing...</think>["Reason 1", "Reason 2"]'
                
                result = get_recommendations(self.user.id, top_k=2)
                
                self.assertIsInstance(result, list)
                self.assertTrue(len(result) > 0)
                self.assertIn('book', result[0])
                self.assertIn('product_id', result[0])
                self.assertIn('reason', result[0])
    
    def test_recommendations_caching(self):
        """Test that recommendations are cached"""
        Purchase.objects.create(user=self.user, book=self.book1)
        
        with patch('recommendations.rag.ChatOllama') as mock_llm_cls, \
             patch('recommendations.rag.ChatPromptTemplate') as mock_prompt_cls:
            
            # Setup mock chain
            mock_prompt = MagicMock()
            mock_prompt_cls.from_template.return_value = mock_prompt
            
            mock_intermediate = MagicMock()
            mock_prompt.__or__.return_value = mock_intermediate
            
            mock_chain = MagicMock()
            mock_intermediate.__or__.return_value = mock_chain
            
            mock_chain.invoke.return_value = '["Reason A", "Reason B"]'
            
            # First call - should hit LLM (which is our mock chain)
            result1 = get_recommendations(self.user.id, top_k=2)
            call_count_1 = mock_chain.invoke.call_count
            
            # Second call - should use cache
            result2 = get_recommendations(self.user.id, top_k=2)
            call_count_2 = mock_chain.invoke.call_count
            
            # Results should be the same
            self.assertEqual(len(result1), len(result2))
            # Second call should not invoke LLM again
            self.assertEqual(call_count_1, call_count_2)
    
    def test_no_embeddings_available(self):
        """Test when books have no embeddings"""
        # Create book without embedding
        book_no_embedding = Book.objects.create(
            title='No Embedding Book',
            author='Author',
            description='Description',
            reference='REF_NONE',
            embedding=None
        )
        Purchase.objects.create(user=self.user, book=book_no_embedding)
        
        result = get_recommendations(self.user.id, top_k=3)
        
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)
    
    def test_llm_failure_fallback(self):
        """Test fallback when LLM fails"""
        Purchase.objects.create(user=self.user, book=self.book1)
        
        # Mock LLM to raise an exception
        with patch('recommendations.rag.ChatOllama') as mock_llm:
            mock_llm.side_effect = Exception("LLM connection failed")
            
            result = get_recommendations(self.user.id, top_k=2)
            
            # Should return fallback as a list
            self.assertIsInstance(result, list)
            self.assertTrue(len(result) > 0)
            self.assertEqual(result[0]['reason'], "Recommended based on your history.")
    
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
        self.category = Category.objects.create(name='Edge Category', description='Test')
    
    def test_empty_top_k(self):
        """Test with top_k=0"""
        book = Book.objects.create(
            title='Test',
            author='Author',
            description='Desc',
            reference='REF_EMPTY',
            embedding=np.random.rand(384).tolist()
        )
        Product.objects.create(name=book.title, reference=book.reference, category=self.category, price=10.0)
        Purchase.objects.create(user=self.user, book=book)
        
        # Should handle gracefully
        result = get_recommendations(self.user.id, top_k=0)
        self.assertIsInstance(result, list)
    
    def test_large_top_k(self):
        """Test with very large top_k"""
        book = Book.objects.create(
            title='Test',
            author='Author',
            description='Desc',
            reference='REF_LARGE',
            embedding=np.random.rand(384).tolist()
        )
        Product.objects.create(name=book.title, reference=book.reference, category=self.category, price=10.0)
        Purchase.objects.create(user=self.user, book=book)
        
        # Should handle gracefully even if top_k > available books
        result = get_recommendations(self.user.id, top_k=1000)
        self.assertIsInstance(result, list)
    
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
        
        with patch('recommendations.rag.ChatOllama') as mock_llm_cls, \
             patch('recommendations.rag.ChatPromptTemplate') as mock_prompt_cls:
            
            # Setup mock chain
            mock_prompt = MagicMock()
            mock_prompt_cls.from_template.return_value = mock_prompt
            
            mock_intermediate = MagicMock()
            mock_prompt.__or__.return_value = mock_intermediate
            
            mock_chain = MagicMock()
            mock_intermediate.__or__.return_value = mock_chain
            
            mock_chain.invoke.return_value = '["Reason ABC"]'
            
            result = get_recommendations(self.user.id, top_k=3)
            
            # Should handle duplicate purchases
            self.assertIsInstance(result, list)
