app.conf.beat_schedule = {
    'run_sync_all_bots_daily': {
        'task': 'home.tasks.sync_all_bots',
        'schedule': crontab(hour=4, minute=0),  # codziennie o 4:00
    },
    'run_sync_all_active_bots_hourly': {
        'task': 'home.tasks.sync_active_bots',
        'schedule': crontab(minute=0),  # co godzinę o pełnej godzinie
    },
    'refresh_bnb_data_every_15min': {
        'task': 'home.tasks.schedule_bnb_data_refresh',
        'schedule': crontab(minute='*/15'),  # co 15 minut
    },
} 