from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .rag import get_recommendations
from django.http import HttpResponse

@login_required
def recommend_books(request):
    """
    Deprecated view? This seems to use 'recommend.html' which might not exist or work.
    """
    recommendation = get_recommendations(request.user.id)
    return render(request, 'recommendations/recommend.html', {'recommendation': recommendation})

@login_required
def cart_recommendations(request):
    """
    Returns HTML partial for recommendations. Used for async loading on checkout page.
    """
    try:
        recommendations = get_recommendations(request.user.id)
        if not recommendations or isinstance(recommendations, str):
            # If string is returned (error or simple list fallback), it might not work well with the partial loop.
            # But get_recommendations logic was updated to return list of dicts.
            # If empty, return empty response (template handles empty lists gracefully)
            pass
        
        return render(request, 'recommendations/cart_recommendations_partial.html', {'recommendations': recommendations})
    except Exception as e:
        print(f"Error in cart_recommendations: {e}")
        return HttpResponse("")