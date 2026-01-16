from django.urls import path
from .views import recommend_books

urlpatterns = [
    path('recommend/', recommend_books, name='recommend'),
]