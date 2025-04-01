import logging
from django.conf import settings
import openai

logger = logging.getLogger(__name__)

def prepare_conversation_for_ai(user_message, conversation_history=None):
    """
    Przygotowuje konwersację w formacie dla OpenAI API.
    
    Args:
        user_message: Wiadomość od użytkownika.
        conversation_history: Historia konwersacji.
        
    Returns:
        list: Lista wiadomości gotowa do wysłania do OpenAI API.
    """
    messages = conversation_history.copy() if conversation_history else []
    
    # Dodaj wiadomość użytkownika
    messages.append({"role": "user", "content": user_message})
    
    return messages

def get_ai_response(messages, openai_client):
    """
    Wysyła zapytanie do API OpenAI i zwraca odpowiedź.
    
    Args:
        messages: Przygotowana lista wiadomości.
        openai_client: Zainicjalizowany klient OpenAI.
        
    Returns:
        dict: Słownik z odpowiedzią od AI.
    """
    try:
        # Zapytaj model AI
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7
        )
        
        # Zapisz pierwsze 200 znaków odpowiedzi do logów
        response_content = response.choices[0].message.content
        print(f"[DEBUG] Zawartość odpowiedzi (pierwsze 200 znaków): {response_content[:200]}...")
        
        # Zwróć odpowiedź
        return {
            "response": response_content
        }
    except Exception as e:
        logger.error(f"Błąd podczas komunikacji z AI: {e}")
        print(f"[DEBUG ERROR] Błąd podczas komunikacji z AI: {str(e)}")
        return {
            "response": f"Przepraszam, wystąpił błąd podczas komunikacji z AI: {str(e)}"
        } 