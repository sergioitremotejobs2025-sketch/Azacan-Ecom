from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from ..models import Book
from .serializers import BookSerializer
from ..rag import get_recommendations, get_recommendations_by_book_title, get_recommendations_by_query

class BookViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows books to be viewed, created, updated or deleted.
    """
    queryset = Book.objects.all().order_by('-id')
    serializer_class = BookSerializer

    from rest_framework.filters import SearchFilter, OrderingFilter
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['title', 'reference', 'author', 'category']
    ordering_fields = ['price', 'title', 'id']

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def recommend_by_user(request):
    """
    Get recommendations based on user purchase history.
    """
    user_id = request.data.get('user_id') or request.query_params.get('user_id')
    if not user_id:
        return Response({"error": "user_id is required"}, status=status.HTTP_400_BAD_REQUEST)
    
    top_k = int(request.data.get('top_k', 3))
    recommendations = get_recommendations(user_id, top_k=top_k)
    return Response({"recommendations": recommendations})

@api_view(['POST'])
@permission_classes([AllowAny])
def recommend_by_title(request):
    """
    Get recommendations based on a specific book title.
    """
    title = request.data.get('title')
    if not title:
        return Response({"error": "title is required"}, status=status.HTTP_400_BAD_REQUEST)
    
    top_k = int(request.data.get('top_k', 5))
    recommendations = get_recommendations_by_book_title(title, top_k=top_k)
    return Response({"recommendations": recommendations})

@api_view(['POST'])
@permission_classes([AllowAny])
def recommend_by_query(request):
    """
    Get recommendations based on a natural language query.
    """
    query = request.data.get('query')
    if not query:
        return Response({"error": "query is required"}, status=status.HTTP_400_BAD_REQUEST)
    
    top_k = int(request.data.get('top_k', 5))
    recommendations = get_recommendations_by_query(query, top_k=top_k)
    return Response({"recommendations": recommendations})