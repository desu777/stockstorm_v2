from django.apps import AppConfig


class HomeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'home'

    def ready(self):
        import os
        if os.environ.get('RUN_MAIN') == 'true':  # Run only in the main process
            # Any initialization code can go here
            pass
