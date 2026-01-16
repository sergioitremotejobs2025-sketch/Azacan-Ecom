from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .rag import get_recommendations

@login_required
def recommend_books(request):
    recommendation = get_recommendations(request.user.id)
    return render(request, 'recommendations/recommend.html', {'recommendation': recommendation})