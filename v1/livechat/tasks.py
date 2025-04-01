from celery import shared_task
from django.utils import timezone
from .models import ChatMessage

@shared_task
def delete_expired_messages():
    """
    Zadanie Celery do usuwania wiadomości czatu starszych niż 24 godziny.
    To zadanie powinno być uruchamiane cyklicznie przez harmonogram Celery.
    """
    expiration_time = timezone.now() - timezone.timedelta(hours=24)
    expired_messages = ChatMessage.objects.filter(timestamp__lt=expiration_time)
    count = expired_messages.count()
    expired_messages.delete()
    return f"Usunięto {count} wygasłych wiadomości."
