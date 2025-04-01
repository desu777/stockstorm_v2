import requests
from django.conf import settings
import logging

# utils.py

from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token

logger = logging.getLogger(__name__)

def get_token(user_id):
    """
    Pobiera token mikroserwisu dla danego user_id.
    Dodatkowo zapewnia, że token jest zarejestrowany w mikroserwisach.

    Args:
        user_id (int): ID użytkownika.

    Returns:
        str or None: Klucz tokena, jeśli istnieje, w przeciwnym razie None.
    """
    try:
        token = Token.objects.get(user_id=user_id)
        
        # Attempt to ensure token is registered in microservices
        ensure_token_in_microservices(user_id, token.key)
        
        return token.key
    except Token.DoesNotExist:
        logger.error(f"Token dla użytkownika z id={user_id} nie istnieje.")
        return None

def ensure_token_in_microservices(user_id, token_key):
    """
    Ensures token is registered in all microservices.
    This helps fix token registration issues.
    """
    microservices = [
        {
            'name': 'BNB1 (51015rei)',
            'url': f"{settings.BNB_MICROSERVICE_URL}/register_token/",
            'headers': {
                'Authorization': f'Bearer {settings.MICROSERVICE_API_TOKEN}',
                'Content-Type': 'application/json',
            },
        },
        {
            'name': 'BNB2 (51015)',
            'url': f"{settings.BNB_MICROSERVICE_URL_2}/register_token/",
            'headers': {
                'Authorization': f'Bearer {settings.MICROSERVICE_API_TOKEN}',
                'Content-Type': 'application/json',
            },
        }
    ]

    for service in microservices:
        try:
            payload = {
                'user_id': user_id,
                'token': token_key
            }
            requests.post(
                service['url'],
                json=payload,
                headers=service['headers'],
                timeout=3
            )
            # We don't care about the response - even if it exists already, that's fine
        except Exception as e:
            logger.warning(f"Could not register token in {service['name']}: {str(e)}")

# home/utils.py
from binance.client import Client
from binance.exceptions import BinanceAPIException

def test_binance_connection(api_key, api_secret):
    """Test Binance API connection with the provided credentials"""
    try:
        client = Client(api_key, api_secret)
        
        # Try a basic, non-intrusive API call
        status = client.get_system_status()
        if status['status'] == 0:
            # Also get account info to verify API key permissions
            try:
                account = client.get_account()
                return "Success! API connected and authenticated properly."
            except BinanceAPIException as e:
                if e.code == -2015:  # This code is for invalid API key/signature
                    return "API connected, but account access failed. Check API permissions."
                return f"API connected, but account access error: {e}"
        else:
            return f"Binance system is currently unavailable: {status['msg']}"
            
    except BinanceAPIException as e:
        return f"Binance API error (code {e.code}): {e.message}"
    except Exception as e:
        return f"Connection error: {str(e)}"