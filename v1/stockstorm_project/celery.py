import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stockstorm_project.settings')

app = Celery('stockstorm_project')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

# Configure Celery Beat schedule
app.conf.beat_schedule = {
    'sync-bots-every-30-seconds': {
        'task': 'home.tasks.sync_all_bots',
        'schedule': 30.0,  # Run every 30 seconds
    },
    'check-pending-orders-every-2-minutes': {
        'task': 'hpcrypto.tasks.check_pending_orders',
        'schedule': 120.0,  # Run every 2 minutes
    },
    'update-stock-prices-every-4-minutes': {
        'task': 'gt.celery_tasks.update_stock_prices',
        'schedule': 60.0,  # Run every 1 minute
    },
    'update-crypto-prices-every-2-minutes': {
        'task': 'hpcrypto.tasks.update_crypto_prices',
        'schedule': 60.0,  # Run every 1 minute
    },
    'delete-expired-chat-messages-every-hour': {
        'task': 'livechat.tasks.delete_expired_messages',
        'schedule': 3600.0,  # Run every 1 hour
    },
}

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')