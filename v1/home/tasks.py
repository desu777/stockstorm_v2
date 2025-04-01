from celery import shared_task
import logging
import requests
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta
import pytz
from .models import Bot, User, BotLog, UserProfile, TelegramConfig

logger = logging.getLogger(__name__)

@shared_task
def sync_all_bots():
    """
    Async task to sync the status of all active bots with their respective microservices.
    This replaces the synchronous middleware.
    """
    # Get all active bots
    active_bots = Bot.objects.filter(status__in=['NEW', 'RUNNING'])
    
    for bot in active_bots:
        try:
            sync_bot_status.delay(bot.id)
        except Exception as e:
            logger.error(f"Error scheduling sync for bot {bot.id}: {e}")

@shared_task
def sync_bot_status(bot_id):
    """
    Sync a single bot's status with its microservice
    """
    try:
        bot = Bot.objects.get(id=bot_id)
        user = bot.user
        
        # Try to get user's token
        try:
            from rest_framework.authtoken.models import Token
            token = Token.objects.get(user=user).key
        except Exception as e:
            logger.error(f"User {user.id} has no auth token - skipping bot {bot_id}")
            return
        
        # Skip if no microservice bot ID
        if not bot.microservice_bot_id:
            logger.warning(f"Bot {bot.id} has no microservice_bot_id. Skipping.")
            return
        
        # Determine which microservice to use based on broker type and bot name
        if bot.broker_type == 'BNB':
            # Check if this is a 51015rei bot or 51015 bot based on the name
            is_rei_bot = "51015rei" in bot.name.lower()
            base_url = settings.BNB_MICROSERVICE_URL if is_rei_bot else settings.BNB_MICROSERVICE_URL_2
            microservice_name = "51015rei" if is_rei_bot else "51015"
            logger.info(f"Bot {bot.id} identified as {microservice_name} type, using URL: {base_url}")
        else:
            logger.warning(f"Bot {bot.id} has unknown broker type: {bot.broker_type}. Skipping.")
            return
        
        api_endpoint = f"{base_url}/get_bot_status/{bot.microservice_bot_id}/"
        
        headers = {
            'Authorization': f'Token {token}'
        }
        
        # Use a timeout to prevent hanging
        timeout = getattr(settings, 'REQUESTS_TIMEOUT', 10)
        resp = requests.get(api_endpoint, headers=headers, timeout=timeout)
        
        if resp.status_code == 200:
            data = resp.json()
            logger.info(f"Data from microservice {microservice_name} for bot {bot.id}: {data}")
            new_status = data.get("status")
            
            if new_status and bot.status != new_status:
                old_status = bot.status  # Store old status for notification
                bot.status = new_status
                if new_status == 'FINISHED' and not bot.finished_at:
                    bot.finished_at = timezone.now()
                    logger.info(f"finished_at for bot {bot.id} = {bot.finished_at}")
                bot.save()
                logger.info(f"Bot {bot.id} (micro_id={bot.microservice_bot_id}) updated: {bot.status}")
                
                # Send notification when a bot finishes
                if new_status == 'FINISHED':
                    notify_bot_finished(bot.id, bot.name, bot.instrument)
        else:
            logger.error(f"Error syncing bot {bot.id} with {microservice_name}: {resp.status_code} {resp.text}")
    
    except Exception as e:
        logger.error(f"Error during sync of bot {bot_id}: {e}")

def notify_bot_finished(bot_id, bot_name, instrument):
    """
    Send a notification that a bot has finished its job
    
    Args:
        bot_id: The ID of the bot
        bot_name: The name of the bot
        instrument: The trading instrument
    """
    try:
        # Get the bot
        bot = Bot.objects.select_related('user').get(id=bot_id)
        user = bot.user
        
        # Get the user's telegram config and profile
        telegram_config = TelegramConfig.objects.filter(user=user, is_verified=True).first()
        if not telegram_config or not telegram_config.chat_id:
            logger.info(f"No valid Telegram config for user {user.id}")
            return
            
        # Check if the user has enabled Telegram notifications
        profile = UserProfile.objects.get(user=user)
        if not profile.telegram_notifications_enabled:
            logger.info(f"Telegram notifications not enabled for user {user.id}")
            return
            
        # Format the message
        message = (
            f"🤖 <b>Bot Finished!</b> 🏁\n\n"
            f"🎯 Your bot <b>{bot_name}</b> has <b>FINISHED</b> its job! 🚀\n\n"
            f"📊 <b>Bot Details:</b>\n"
            f"📈 Instrument: <b>{instrument}</b>\n"
            f"⏱️ Finished at: <b>{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}</b>\n"
        )
        
        # Add more details if available
        if hasattr(bot, 'total_profit'):
            message += f"💰 Total Profit: <b>${bot.total_profit}</b>\n"
        
        # Send the notification
        from v1.hpcrypto.telegram_utils import send_telegram_notification
        success, result = send_telegram_notification(telegram_config.chat_id, message)
        if success:
            logger.info(f"Bot finished notification sent for bot {bot_id} to user {user.id}")
        else:
            logger.error(f"Failed to send bot finished notification for bot {bot_id}: {result}")
            
    except Exception as e:
        logger.error(f"Error sending bot finished notification for bot {bot_id}: {str(e)}")

@shared_task
def cache_live_status():
    """
    Ta funkcja nie jest już potrzebna po wyłączeniu API XTB.
    Pozostawiona tylko jako zaślepka, aby nie powodować błędów w przypadku wywołania.
    """
    from django.core.cache import cache
    cache.set('xtb_live_status', {}, 300)
    return 0

@shared_task
def refresh_bnb_bot_data(bot_id):
    """
    Odświeża dane bota BNB, pobierając aktualne informacje z mikrousługi
    """
    try:
        from .utils import get_token
        
        bot = Bot.objects.get(pk=bot_id, broker_type='BNB')
        user = User.objects.get(pk=bot.user_id)
        
        # Pobierz token dla mikrousługi
        token = get_token(user.id)
        if not token:
            # Zapisz log do bazy
            BotLog.objects.create(
                bot=bot,
                message="Nie udało się autoryzować z mikrousługą podczas automatycznego odświeżania."
            )
            return False
            
        # Określ typ bota na podstawie nazwy
        is_rei_bot = "51015rei" in bot.name.lower()
        microservice_url = settings.BNB_MICROSERVICE_URL if is_rei_bot else settings.BNB_MICROSERVICE_URL_2
        
        # Konfiguracja zapytania
        headers = {'Authorization': f'Token {token}'}
        
        # Pobierz aktualne dane bota
        response = requests.get(
            f"{microservice_url}/get_bot_details/{bot.microservice_bot_id}/",
            headers=headers,
            timeout=5
        )
        
        if response.status_code == 200:
            # Dane zostały odświeżone pomyślnie
            bot_data = response.json()
            
            # Aktualizacja statusu bota
            if bot_data.get('status'):
                bot.status = bot_data.get('status')
                bot.save()
                
            # Dodanie wpisu do logów
            BotLog.objects.create(
                bot=bot,
                message=f"Automatyczne odświeżenie danych: status {bot.status}"
            )
            return True
        else:
            # Błąd podczas pobierania danych
            BotLog.objects.create(
                bot=bot,
                message=f"Błąd podczas automatycznego odświeżania danych: {response.status_code}"
            )
            return False
            
    except Bot.DoesNotExist:
        return False
    except Exception as e:
        # Logowanie błędu
        try:
            BotLog.objects.create(
                bot_id=bot_id,
                message=f"Wyjątek podczas automatycznego odświeżania danych: {str(e)}"
            )
        except:
            pass
        return False

@shared_task
def schedule_bnb_data_refresh():
    """
    Planuje odświeżanie danych dla wszystkich aktywnych botów BNB
    """
    try:
        active_bots = Bot.objects.filter(is_active=True, broker_type='BNB')
        
        for bot in active_bots:
            # Zaplanuj odświeżenie danych dla każdego aktywnego bota
            refresh_bnb_bot_data.delay(bot.id)
            
        return f"Zaplanowano odświeżenie danych dla {active_bots.count()} botów"
    except Exception as e:
        return f"Błąd podczas planowania odświeżania danych: {str(e)}" 