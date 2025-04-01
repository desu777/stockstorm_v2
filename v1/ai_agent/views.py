from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from .models import Conversation, Message

# Bezpieczny import funkcji
try:
    from .services import chat_with_ai
    has_services = True
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
    logger.error("Nie można zaimportować modułu services. Czat AI będzie niedostępny.")
    has_services = False
    
    # Pusta funkcja zastępcza
    def chat_with_ai(message, history=None, user_id=None, microservice_token=None):
        return {"response": "Przepraszam, funkcjonalność czatu AI jest tymczasowo niedostępna.", "chart_image": None}

try:
    from home.utils import get_token
    has_get_token = True
except ImportError:
    has_get_token = False

import json
import logging
from django.utils import timezone
import traceback

logger = logging.getLogger(__name__)

def generate_title(message_text, max_length=60):
    """
    Generuje tytuł konwersacji na podstawie pierwszej wiadomości użytkownika.
    """
    try:
        # Prosty algorytm - użyj pierwszych słów wiadomości (maksymalnie 60 znaków)
        title = message_text[:max_length].strip()
        if len(message_text) > max_length:
            title += "..."
        
        # Jeśli tytuł jest zbyt krótki, użyj domyślnego
        if len(title) < 3:
            return "Nowa konwersacja"
            
        return title
    except Exception as e:
        logger.error(f"Błąd podczas generowania tytułu: {e}")
        return "Nowa konwersacja"

@login_required
def ai_agent_chat(request):
    # Zawsze tworzymy nową konwersację zamiast pobierać aktywną
    conversation = Conversation.objects.create(user=request.user, title="Nowa rozmowa")
    
    # Dodajemy wiadomość powitalną od bota
    welcome_message = Message.objects.create(
        conversation=conversation,
        role="assistant",
        content="Witaj w CryptoBot AI! Jestem Twoim osobistym asystentem do spraw tradingu kryptowalut. W czym mogę Ci dzisiaj pomóc?"
    )
    
    # Zwracamy pusty context - stare wiadomości nie są już potrzebne
    context = {
        'conversation': conversation,
        'now': timezone.now()
    }
    
    return render(request, 'ai_agent/chat.html', context)

@login_required
def send_message(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        message_content = data.get('message')
        conversation_id = data.get('conversation_id')
        
        try:
            conversation = Conversation.objects.get(id=conversation_id, user=request.user)
            
            # Zapisz wiadomość użytkownika
            user_message = Message.objects.create(
                conversation=conversation,
                role='user',
                content=message_content
            )
            
            # Pobierz historię konwersacji
            message_history = []
            previous_messages = Message.objects.filter(conversation=conversation).order_by('created_at')
            
            # Transformuj wiadomości do formatu wymaganego przez OpenAI API
            for msg in previous_messages:
                if msg.id != user_message.id:  # Pomijamy aktualną wiadomość, bo dodamy ją osobno
                    message_history.append({
                        "role": msg.role,
                        "content": msg.content
                    })
            
            # Uzyskaj odpowiedź od AI - funkcja zwraca słownik a nie krotkę
            ai_response = chat_with_ai(
                user_message=message_content,
                conversation_history=message_history,
                user_id=request.user.id
            )
            
            # Pobieramy dane ze słownika
            response_content = ai_response.get('response', 'Przepraszam, wystąpił problem z odpowiedzią.')
            chart_image = ai_response.get('chart_image')
            conversation_title = ai_response.get('title')
            
            # Jeśli uzyskano tytuł konwersacji, zaktualizuj go
            if conversation_title and (conversation.title == "Nowa rozmowa" or not conversation.title):
                conversation.title = conversation_title
                conversation.save()
            
            # Zapisz odpowiedź AI
            ai_message = Message.objects.create(
                conversation=conversation,
                role='assistant',
                content=response_content,
                chart_image=chart_image
            )
            
            # Zaktualizuj znacznik czasu konwersacji
            conversation.updated_at = timezone.now()
            conversation.save()
            
            return JsonResponse({
                'status': 'success',
                'message': {
                    'content': response_content,
                    'created_at': ai_message.created_at.strftime('%H:%M')
                },
                'chart_image': chart_image,
                'conversation': {
                    'id': conversation.id,
                    'title': conversation.title
                }
            })
            
        except Conversation.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Conversation not found'
            }, status=404)
        except Exception as e:
            print(f"Error: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    }, status=400)

def process_chart_data(data):
    """
    Przetwarza dane wykresu, rozpoznając czy to zwykły obraz czy dane dla Chart.js
    
    Args:
        data: Dane wykresu (słownik lub string z base64)
        
    Returns:
        Dict z typem wykresu i danymi
    """
    import json
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Sprawdzamy czy otrzymaliśmy słownik z danymi dla Chart.js
        if isinstance(data, dict) and 'datasets' in data:
            logger.debug("Wykryto dane Chart.js - konwertowanie do JSON")
            # Zwracamy jako JSON do wykorzystania przez frontend
            return {
                'status': 'success',
                'chart_type': 'chartjs',
                'chart_data': json.dumps(data)
            }
            
        # Sprawdzamy czy to jest string z base64 obrazu
        elif isinstance(data, str) and (data.startswith('data:image') or ';base64,' in data):
            logger.debug("Wykryto base64 obrazu")
            return {
                'status': 'success',
                'chart_type': 'image',
                'chart_image': data
            }
            
        # Sprawdzamy czy to jest base64 bez prefiksu
        elif isinstance(data, str) and len(data) > 100:
            logger.debug("Wykryto prawdopodobnie base64 obrazu bez prefiksu")
            return {
                'status': 'success',
                'chart_type': 'image',
                'chart_image': f"data:image/jpeg;base64,{data}"
            }
            
        # Jeśli otrzymaliśmy None lub pusty string
        elif data is None or data == "":
            logger.warning("Otrzymano puste dane wykresu")
            return {
                'status': 'error',
                'message': 'Brak danych wykresu'
            }
            
        # W innych przypadkach zwracamy błąd
        else:
            logger.warning(f"Nieznany format danych wykresu: {type(data)}")
            return {
                'status': 'error',
                'message': 'Nierozpoznany format danych wykresu'
            }
            
    except Exception as e:
        logger.error(f"Błąd podczas przetwarzania danych wykresu: {str(e)}")
        return {
            'status': 'error',
            'message': f'Błąd: {str(e)}'
        }

@login_required
def bot_chart_view(request, bot_id):
    """Widok generujący i wyświetlający wykres dla pojedynczego bota"""
    try:
        # Uzyskaj token mikrousługi
        microservice_token = get_microservice_token()
        
        # Wywołaj funkcję generowania wykresu dla bota
        response = call_generate_bot_chart(
            user_id=request.user.id,
            microservice_token=microservice_token,
            bot_id=bot_id,
            use_chartjs=True  # Używamy Chart.js domyślnie
        )
        
        # Sprawdź typ wykresu i wyodrębnij odpowiednie dane
        chart_data = {}
        if response.get("chart_is_html") and response.get("chart_html"):
            # To są dane Chart.js
            chart_data = process_chart_data(response["chart_html"])
        elif response.get("chart_image") and response.get("chart_image_base64"):
            # To jest base64 obrazu
            chart_data = process_chart_data(response["chart_image_base64"])
        else:
            # Brak danych wykresu
            chart_data = {
                'status': 'error',
                'message': 'Nie udało się wygenerować wykresu'
            }
        
        # Dodaj informacje o bocie
        if response.get("bot_info"):
            chart_data["bot_info"] = response["bot_info"]
        
        if response.get("detailed_info"):
            chart_data["detailed_analysis"] = response["detailed_info"]
            
        return JsonResponse(chart_data)
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@login_required
def portfolio_chart_view(request):
    """Widok generujący i wyświetlający wykres zysków dla całego portfolio"""
    try:
        # Uzyskaj token mikrousługi
        microservice_token = get_microservice_token()
        
        # Pobierz parametry z zapytania
        strategy_filter = request.GET.get('strategy')
        period_days = int(request.GET.get('period', 365))
        
        # Wywołaj funkcję generowania wykresu portfolio
        response = call_generate_chart(
            user_id=request.user.id,
            microservice_token=microservice_token,
            strategy_filter=strategy_filter,
            period_days=period_days,
            use_chartjs=True  # Używamy Chart.js domyślnie
        )
        
        # Sprawdź typ wykresu i wyodrębnij odpowiednie dane
        chart_data = {}
        if response.get("chart_is_html") and response.get("chart_html"):
            # To są dane Chart.js
            chart_data = process_chart_data(response["chart_html"])
        elif response.get("chart_image") and response.get("chart_image_base64"):
            # To jest base64 obrazu
            chart_data = process_chart_data(response["chart_image_base64"])
        else:
            # Brak danych wykresu
            chart_data = {
                'status': 'error',
                'message': 'Nie udało się wygenerować wykresu'
            }
        
        # Dodaj informacje o portfolio
        if response.get("portfolio_analysis"):
            chart_data["portfolio_analysis"] = response["portfolio_analysis"]
            
        return JsonResponse(chart_data)
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

def get_microservice_token():
    """Pobiera token dostępu do mikrousługi"""
    try:
        from .services import get_microservice_token as get_token
        return get_token()
    except ImportError:
        logger.error("Nie można zaimportować funkcji get_microservice_token z modułu services")
        return None
