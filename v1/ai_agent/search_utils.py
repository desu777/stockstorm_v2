import os
import json
import numpy as np
import logging
from django.conf import settings
import openai

logger = logging.getLogger(__name__)

def get_embedding(text, client=None, model="text-embedding-3-small"):
    """
    Generuje embedding dla podanego tekstu za pomocą modelu OpenAI.
    
    Args:
        text: Tekst, dla którego ma zostać wygenerowany embedding
        client: Klient OpenAI (opcjonalny - jeśli nie podany, zostanie utworzony nowy)
        model: Model OpenAI do generowania embeddingów
        
    Returns:
        Lista z wartościami embeddingu
    """
    if not text or text.strip() == "":
        logger.warning("Próba wygenerowania embeddingu dla pustego tekstu")
        return None
        
    own_client = False
    if client is None:
        # Dodaj obsługę API key i użyj zmiennej środowiskowej
        api_key = settings.OPENAI_API_KEY
        own_client = True
        client = openai.OpenAI(api_key=api_key)
        
    try:
        # Ogranicz długość tekstu, aby zmieścić się w limitach modelu
        text = text[:8191]
        
        # Generuj embedding
        response = client.embeddings.create(
            model=model,
            input=text
        )
        
        # Zwróć wartości embeddingu
        return response.data[0].embedding
        
    except Exception as e:
        logger.error(f"Błąd podczas generowania embeddingu: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None
    finally:
        # Zamknij klienta, jeśli go utworzyliśmy
        if own_client:
            pass  # OpenAI klienty nie wymagają zamknięcia
            
def search_knowledge_base(query_text, top_k=5, threshold=0.5, client=None):
    """
    Przeszukuje bazę wiedzy na podstawie podobieństwa semantycznego do zapytania.
    
    Args:
        query_text: Tekst zapytania
        top_k: Maksymalna liczba zwracanych wyników
        threshold: Minimalny próg podobieństwa
        client: Klient OpenAI (opcjonalny)
        
    Returns:
        Lista znalezionych fragmentów tekstu wraz z metadanymi
    """
    if not query_text or query_text.strip() == "":
        logger.warning("Próba przeszukania bazy wiedzy z pustym zapytaniem")
        return []
    
    print(f"[DEBUG] Przeszukuję bazę wiedzy dla: {query_text[:50]}...")
    
    try:
        # Setup clients
        print(f"[DEBUG] Inicjuję klienty API...")
        openai_client = client or openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        
        # Pobierz konfigurację Pinecone
        pinecone_api_key = settings.PINECONE_API_KEY
        pinecone_index_name = settings.PINECONE_INDEX_NAME
        pinecone_namespace = getattr(settings, 'PINECONE_NAMESPACE', 'trading_analysis')
        
        print(f"[DEBUG] API Key: {pinecone_api_key[:5]}...")
        print(f"[DEBUG] Index Name: {pinecone_index_name}")
        print(f"[DEBUG] Namespace: {pinecone_namespace}")
        
        # Import Pinecone
        import pinecone
        
        # Inicjalizacja klienta Pinecone
        pc = pinecone.Pinecone(api_key=pinecone_api_key)
        index = pc.Index(name=pinecone_index_name)
        
        # Get embedding
        query_embedding = get_embedding(query_text, client=openai_client)
        if query_embedding is None:
            logger.error("Nie udało się wygenerować embeddingu dla zapytania")
            return []
            
        print(f"[DEBUG] Query Embedding Length: {len(query_embedding)}")
        
        # Query Pinecone
        results = index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True,
            namespace=pinecone_namespace
        )
        
        print(f"[DEBUG] Otrzymano {len(results['matches'])} wyników z Pinecone")
        
        # Format results
        formatted_results = []
        for match in results['matches']:
            if match['score'] < threshold:
                continue
                
            formatted_result = {
                "text": match['metadata'].get('content', ''),
                "metadata": {
                    "id": match['id'],
                    "main_topic": match['metadata'].get('main_topic', ''),
                    "subtopic": match['metadata'].get('subtopic', ''),
                    "source": match['metadata'].get('source', '')
                },
                "similarity": match['score']
            }
            formatted_results.append(formatted_result)
            print(f"[DEBUG] Znaleziony dokument: {formatted_result['metadata']['id']} | Temat: {formatted_result['metadata']['main_topic']} | Podobieństwo: {formatted_result['similarity']:.4f}")
            print(f"[DEBUG] Fragment tekstu (pierwsze 100 znaków): {formatted_result['text'][:100]}...")
        
        print(f"[DEBUG] Znaleziono {len(formatted_results)} pasujących fragmentów po filtrowaniu")
        return formatted_results
        
    except Exception as e:
        logger.error(f"Błąd podczas przeszukiwania bazy wiedzy: {e}")
        import traceback
        error_traceback = traceback.format_exc()
        logger.error(error_traceback)
        print(f"[DEBUG ERROR] {e}")
        print(f"[DEBUG TRACEBACK] {error_traceback}")
        return [] 