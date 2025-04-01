# sync_bot_middleware.py

from django.core.cache import cache
from home.models import Bot
from django.conf import settings

class SyncBotMiddleware:
    """
    Lightweight middleware that only adds a flag to the request context
    indicating if the user has active bots. Actual synchronization is
    handled by Celery tasks.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Check cache first for active bots
            cache_key = f'user_{request.user.id}_has_active_bots'
            has_active_bots = cache.get(cache_key)
            
            if has_active_bots is None:
                # Cache miss, check database
                has_active_bots = Bot.objects.filter(
                    user=request.user, 
                    status__in=['NEW', 'RUNNING']
                ).exists()
                
                # Cache for 5 minutes
                cache.set(cache_key, has_active_bots, 300)
                
            # Add to request context for templates
            request.has_active_bots = has_active_bots
        else:
            request.has_active_bots = False
            
        response = self.get_response(request)
        return response

    def sync_bot_status(self, request):
        # Szukamy botów usera o statusie NEW lub RUNNING
        bots = Bot.objects.filter(user=request.user, status__in=['NEW', 'RUNNING'])
        for bot in bots:
            try:
                # Sprawdzamy, czy user ma token
                if not hasattr(request.user, 'auth_token'):
                    print(f"[SYNC BOT] Użytkownik {request.user.id} nie ma auth_token – pomijam.")
                    continue
                token = request.user.auth_token.key

                # Bez microservice_bot_id nie możemy się komunikować
                if not bot.microservice_bot_id:
                    print(f"[SYNC BOT] Bot {bot.id} nie ma microservice_bot_id. Pomijam.")
                    continue

                # Rozróżniamy broker_type
                if bot.broker_type == 'BNB':
                    base_url = settings.BNB_MICROSERVICE_URL
                else:
                    continue  # Nieznany broker, pomijamy

                api_endpoint = f"{base_url}/get_bot_status/{bot.microservice_bot_id}/"

                headers = {
                    'Authorization': f'Token {token}'
                }

                resp = requests.get(api_endpoint, headers=headers, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    print(f"[SYNC BOT] Dane z mikroserwisu {bot.broker_type} dla bota {bot.id}: {data}")
                    new_status = data.get("status")

                    if new_status and bot.status != new_status:
                        bot.status = new_status
                        if new_status == 'FINISHED' and not bot.finished_at:
                            bot.finished_at = timezone.now()
                            print(f"[SYNC BOT] finished_at dla bota {bot.id} = {bot.finished_at}")
                        bot.save()
                        print(f"[SYNC BOT] Bot {bot.id} (micro_id={bot.microservice_bot_id}) zaktualizowany: {bot.status}")
                else:
                    print(f"[SYNC BOT] Błąd sync bota {bot.id}: {resp.status_code} {resp.text}")
            except Exception as e:
                print(f"[SYNC BOT] Błąd podczas sync bota {bot.id}: {e}")

