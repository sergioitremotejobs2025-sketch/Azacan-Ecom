from django.urls import path
from .views import recommend_books, cart_recommendations

urlpatterns = [
    path('recommend/', recommend_books, name='recommend'),
    path('cart_recommendations/', cart_recommendations, name='cart_recommendations'),
]