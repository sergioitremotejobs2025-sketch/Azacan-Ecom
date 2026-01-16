from django.db import models
import datetime
from django.contrib.auth.models import User
from django.db.models.signals import post_save

# Create your models here.


# Create a customer Profile
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    date_modified = models.DateTimeField(auto_now=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    address1 = models.CharField(max_length=255, blank=True, null=True)
    address2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    zip_code = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    old_cart = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f'{self.user.first_name} {self.user.last_name}'

    class Meta:
        verbose_name = "Profile"
        verbose_name_plural = "Profiles"
#Create a user Profile by default when users signs up
def create_profile(sender, instance, created, **kwargs):
    if created:
        user_profile = Profile.objects.create(user=instance)
        user_profile.save()
#Automate the profile creation
post_save.connect(create_profile, sender=User)

"""
We are going to need a category model, a product model and an order model.
"""
class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
class Customer(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    phone = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(max_length=100)
    # Increased length to accommodate hashed passwords (128 chars for Django's default hasher)
    password = models.CharField(max_length=128, help_text="Use set_password() to hash passwords")

    def set_password(self, raw_password):
        """
        Hash and set the password for this customer.
        
        Args:
            raw_password (str): The plaintext password to hash
        """
        from django.contrib.auth.hashers import make_password
        self.password = make_password(raw_password)
    
    def check_password(self, raw_password):
        """
        Check if the provided password matches the stored hashed password.
        
        Args:
            raw_password (str): The plaintext password to check
            
        Returns:
            bool: True if password matches, False otherwise
        """
        from django.contrib.auth.hashers import check_password
        return check_password(raw_password, self.password)

    def __str__(self):
        return f'{self.first_name} {self.last_name}'

class Product(models.Model):
    name = models.CharField(max_length=255, db_index=True)  # Index for search queries
    price = models.DecimalField(default=0, decimal_places=2, max_digits=10)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, default=1)  # ForeignKey automatically indexed
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='uploads/product/', blank=True, null=True)
    is_sale = models.BooleanField(default=False, db_index=True)  # Index for filtering sale items
    sale_price = models.DecimalField(default=0, decimal_places=2, max_digits=10)
    dimensions = models.JSONField(blank=True, null=True, help_text="{'height': ..., 'width': ..., 'thickness': ...}")
    isbn = models.CharField(max_length=20, blank=True, null=True, db_index=True, help_text="International Standard Book Number (if applicable)", verbose_name="ISBN")  # Index for ISBN lookups
    
    # New fields for Azacan import
    reference = models.CharField(max_length=100, blank=True, null=True, db_index=True, verbose_name="Referencia")  # Index for reference lookups
    publisher = models.CharField(max_length=255, blank=True, null=True, verbose_name="Editorial")
    year = models.CharField(max_length=50, blank=True, null=True, verbose_name="Año")
    edition_place = models.CharField(max_length=255, blank=True, null=True, verbose_name="Lugar de edición")
    pages = models.CharField(max_length=50, blank=True, null=True, verbose_name="Páginas")
    measures = models.CharField(max_length=100, blank=True, null=True, verbose_name="Medidas")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def print_dimensions(self):
        dims = self.dimensions or {}
        print(f"Dimensions: {dims.get('height')} x {dims.get('width')} x {dims.get('thickness')}")

    def __str__(self):
        return self.name

class Order(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    address = models.CharField(max_length=255, default='', blank=True)
    phone = models.CharField(max_length=15, default='', blank=True)
    date_ordered = models.DateField(default=datetime.datetime.today)
    status = models.BooleanField(default=False) # True for completed/shipped, False for pending

    def __str__(self):
        return f'Order #{self.id} by {self.customer.first_name} {self.customer.last_name}'

