from django.test import TestCase, Client
from django.contrib.auth.models import User
from store.models import Product, Category, Customer, Profile
from cart.cart import Cart
from decimal import Decimal


class CartTestCase(TestCase):
    """Test cases for shopping cart functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.category = Category.objects.create(
            name='Test Category',
            description='Test Description'
        )
        self.product1 = Product.objects.create(
            name='Test Product 1',
            price=Decimal('10.00'),
            category=self.category,
            description='Test product 1 description'
        )
        self.product2 = Product.objects.create(
            name='Test Product 2',
            price=Decimal('20.00'),
            category=self.category,
            description='Test product 2 description',
            is_sale=True,
            sale_price=Decimal('15.00')
        )
    
    def test_cart_initialization(self):
        """Test cart initializes correctly"""
        request = self.client.get('/').wsgi_request
        cart = Cart(request)
        self.assertIsNotNone(cart)
        self.assertEqual(len(cart), 0)
    
    def test_add_product_to_cart(self):
        """Test adding a product to cart"""
        request = self.client.get('/').wsgi_request
        cart = Cart(request)
        
        cart.add(product=self.product1, quantity=2)
        self.assertEqual(len(cart), 1)
        
        # Verify product is in cart
        product_ids = cart.cart.keys()
        self.assertIn(str(self.product1.id), product_ids)
        self.assertEqual(cart.cart[str(self.product1.id)]['quantity'], 2)
    
    def test_add_multiple_products(self):
        """Test adding multiple different products"""
        request = self.client.get('/').wsgi_request
        cart = Cart(request)
        
        cart.add(product=self.product1, quantity=1)
        cart.add(product=self.product2, quantity=3)
        
        self.assertEqual(len(cart), 2)
        self.assertEqual(cart.cart[str(self.product1.id)]['quantity'], 1)
        self.assertEqual(cart.cart[str(self.product2.id)]['quantity'], 3)
    
    def test_update_cart_quantity(self):
        """Test updating product quantity in cart"""
        request = self.client.get('/').wsgi_request
        cart = Cart(request)
        
        cart.add(product=self.product1, quantity=2)
        cart.update(product=self.product1, quantity=5)
        
        self.assertEqual(cart.cart[str(self.product1.id)]['quantity'], 5)
    
    def test_remove_product_from_cart(self):
        """Test removing a product from cart"""
        request = self.client.get('/').wsgi_request
        cart = Cart(request)
        
        cart.add(product=self.product1, quantity=2)
        self.assertEqual(len(cart), 1)
        
        cart.remove(product=self.product1)
        self.assertEqual(len(cart), 0)
        self.assertNotIn(str(self.product1.id), cart.cart.keys())
    
    def test_cart_total_calculation(self):
        """Test cart total price calculation"""
        request = self.client.get('/').wsgi_request
        cart = Cart(request)
        
        # Add regular price product
        cart.add(product=self.product1, quantity=2)
        # Add sale price product
        cart.add(product=self.product2, quantity=1)
        
        total = cart.car_total()
        # (10.00 * 2) + (15.00 * 1) = 35.00
        expected_total = Decimal('35.00')
        self.assertEqual(total, expected_total)
    
    def test_cart_total_with_sale_price(self):
        """Test that sale prices are used correctly in total"""
        request = self.client.get('/').wsgi_request
        cart = Cart(request)
        
        cart.add(product=self.product2, quantity=2)
        total = cart.car_total()
        
        # Should use sale_price (15.00) not regular price (20.00)
        expected_total = Decimal('30.00')
        self.assertEqual(total, expected_total)
    
    def test_cart_persistence_in_session(self):
        """Test cart persists in session"""
        # First request - add to cart
        session = self.client.session
        session['session_key'] = {}
        session.save()
        
        request1 = self.client.get('/').wsgi_request
        cart1 = Cart(request1)
        cart1.add(product=self.product1, quantity=3)
        
        # Second request - verify cart persists
        request2 = self.client.get('/').wsgi_request
        cart2 = Cart(request2)
        
        self.assertEqual(len(cart2), 1)
        self.assertIn(str(self.product1.id), cart2.cart.keys())
    
    def test_cart_clear(self):
        """Test clearing the cart"""
        request = self.client.get('/').wsgi_request
        cart = Cart(request)
        
        cart.add(product=self.product1, quantity=2)
        cart.add(product=self.product2, quantity=1)
        self.assertEqual(len(cart), 2)
        
        cart.clear()
        # After clearing, cart should be empty
        request2 = self.client.get('/').wsgi_request
        cart2 = Cart(request2)
        self.assertEqual(len(cart2), 0)
    
    def test_get_products(self):
        """Test getting products from cart"""
        request = self.client.get('/').wsgi_request
        cart = Cart(request)
        
        cart.add(product=self.product1, quantity=1)
        cart.add(product=self.product2, quantity=1)
        
        products = cart.get_prods()
        self.assertEqual(products.count(), 2)
        self.assertIn(self.product1, products)
        self.assertIn(self.product2, products)
    
    def test_cart_iteration(self):
        """Test iterating over cart items"""
        request = self.client.get('/').wsgi_request
        cart = Cart(request)
        
        cart.add(product=self.product1, quantity=2)
        cart.add(product=self.product2, quantity=1)
        
        items = list(cart)
        self.assertEqual(len(items), 2)
        
        # Verify each item has required fields
        for item in items:
            self.assertIn('product', item)
            self.assertIn('quantity', item)
            self.assertIn('price', item)
            self.assertIn('total_price', item)


class ProductModelTestCase(TestCase):
    """Test cases for Product model"""
    
    def setUp(self):
        """Set up test data"""
        self.category = Category.objects.create(
            name='Books',
            description='Book category'
        )
    
    def test_product_creation(self):
        """Test creating a product"""
        product = Product.objects.create(
            name='Test Book',
            price=Decimal('25.99'),
            category=self.category,
            description='A test book',
            isbn='9780441172719'
        )
        
        self.assertEqual(product.name, 'Test Book')
        self.assertEqual(product.price, Decimal('25.99'))
        self.assertEqual(product.isbn, '9780441172719')
        self.assertFalse(product.is_sale)
    
    def test_product_sale_price(self):
        """Test product with sale price"""
        product = Product.objects.create(
            name='Sale Book',
            price=Decimal('30.00'),
            category=self.category,
            is_sale=True,
            sale_price=Decimal('20.00')
        )
        
        self.assertTrue(product.is_sale)
        self.assertEqual(product.sale_price, Decimal('20.00'))
    
    def test_product_dimensions(self):
        """Test product with dimensions JSON field"""
        product = Product.objects.create(
            name='Book with Dimensions',
            price=Decimal('15.00'),
            category=self.category,
            dimensions={'height': '9 inches', 'width': '6 inches', 'thickness': '1 inch'}
        )
        
        self.assertIsNotNone(product.dimensions)
        self.assertEqual(product.dimensions['height'], '9 inches')
    
    def test_product_string_representation(self):
        """Test product __str__ method"""
        product = Product.objects.create(
            name='String Test Book',
            price=Decimal('10.00'),
            category=self.category
        )
        
        self.assertEqual(str(product), 'String Test Book')


class CustomerModelTestCase(TestCase):
    """Test cases for Customer model with password hashing"""
    
    def test_customer_creation(self):
        """Test creating a customer"""
        customer = Customer.objects.create(
            first_name='John',
            last_name='Doe',
            email='john@example.com',
            phone='1234567890'
        )
        
        self.assertEqual(customer.first_name, 'John')
        self.assertEqual(customer.email, 'john@example.com')
    
    def test_password_hashing(self):
        """Test password is hashed correctly"""
        customer = Customer.objects.create(
            first_name='Jane',
            last_name='Smith',
            email='jane@example.com'
        )
        
        customer.set_password('secure_password123')
        customer.save()
        
        # Password should be hashed, not plaintext
        self.assertNotEqual(customer.password, 'secure_password123')
        self.assertTrue(customer.password.startswith('pbkdf2_sha256$'))
    
    def test_password_verification(self):
        """Test password verification works correctly"""
        customer = Customer.objects.create(
            first_name='Bob',
            last_name='Johnson',
            email='bob@example.com'
        )
        
        customer.set_password('mypassword')
        customer.save()
        
        # Correct password should verify
        self.assertTrue(customer.check_password('mypassword'))
        
        # Incorrect password should not verify
        self.assertFalse(customer.check_password('wrongpassword'))
    
    def test_customer_string_representation(self):
        """Test customer __str__ method"""
        customer = Customer.objects.create(
            first_name='Alice',
            last_name='Williams',
            email='alice@example.com'
        )
        
        self.assertEqual(str(customer), 'Alice Williams')


class ProfileModelTestCase(TestCase):
    """Test cases for Profile model"""
    
    def test_profile_auto_creation(self):
        """Test profile is automatically created when user is created"""
        user = User.objects.create_user(
            username='profiletest',
            email='profile@example.com',
            password='testpass'
        )
        
        # Profile should be automatically created
        self.assertTrue(Profile.objects.filter(user=user).exists())
        profile = Profile.objects.get(user=user)
        self.assertEqual(profile.user, user)
    
    def test_profile_fields(self):
        """Test profile fields can be updated"""
        user = User.objects.create_user(
            username='fieldtest',
            email='field@example.com',
            password='testpass'
        )
        
        profile = Profile.objects.get(user=user)
        profile.phone = '555-1234'
        profile.address1 = '123 Main St'
        profile.city = 'Test City'
        profile.save()
        
        # Reload from database
        profile.refresh_from_db()
        self.assertEqual(profile.phone, '555-1234')
        self.assertEqual(profile.address1, '123 Main St')
        self.assertEqual(profile.city, 'Test City')
