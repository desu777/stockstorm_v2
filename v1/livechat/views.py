from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import ChatMessage
from django.utils import timezone
from django.db.models import Q

# Create your views here.

@login_required
def get_chat_messages(request):
    """
    Pobiera wszystkie wiadomości czatu bez ograniczeń czasowych.
    Zwraca w formacie JSON dla użycia z AJAX.
    """
    # Pobierz wszystkie wiadomości bez filtrowania czasem
    messages = ChatMessage.objects.all().order_by('timestamp')
    
    data = []
    for message in messages:
        # Sprawdź, czy użytkownik ma zdjęcie profilowe
        profile_picture_url = None
        if hasattr(message.user, 'profile') and message.user.profile.profile_picture:
            profile_picture_url = message.user.profile.profile_picture.url
        
        data.append({
            'id': message.id,
            'username': message.user.username,
            'user_id': message.user.id,
            'message': message.message,
            'timestamp': message.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'is_self': message.user.id == request.user.id,
            'profile_picture': profile_picture_url
        })
    
    return JsonResponse({'messages': data})
