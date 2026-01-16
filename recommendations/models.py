from django.db import models
from pgvector.django import VectorField
from django.contrib.auth.models import User

class Book(models.Model):
    stock = models.IntegerField(default=0, blank=True, null=True)
    reference = models.CharField(max_length=255, blank=True, null=True )
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255, blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    infantil = models.CharField(max_length=255, blank=True, null=True)
    category = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    iva = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    image = models.ImageField(upload_to='books', blank=True, null=True)
    subjects = models.CharField(max_length=255, blank=True, null=True)  # Comma-separated
    embedding = VectorField(dimensions=384, null=True, blank=True)  # For SentenceTransformer 'all-MiniLM-L6-v2' (384 dims)

    created_at = models.DateTimeField(auto_now_add=True)  # When added
    updated_at = models.DateTimeField(auto_now=True)      # Last modified

    class Meta:
        ordering = ['-created_at']  # Newest first
        indexes = [
            models.Index(fields=['title']), 
            models.Index(fields=['author']),
            models.Index(fields=['category']),
        ]

    def __str__(self):
        return f"{self.title} by {self.author or 'Unknown'} (ID: {self.id})"

class Purchase(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    purchase_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Purchase - {str(self.id)}'