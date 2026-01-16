from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BookViewSet, recommend_by_user, recommend_by_title, recommend_by_query

router = DefaultRouter()
router.register(r'books', BookViewSet, basename='book')

urlpatterns = [
    path('', include(router.urls)),
    path('recommend/user/', recommend_by_user, name='recommend_by_user'),
    path('recommend/title/', recommend_by_title, name='recommend_by_title'),
    path('recommend/query/', recommend_by_query, name='recommend_by_query'),
]