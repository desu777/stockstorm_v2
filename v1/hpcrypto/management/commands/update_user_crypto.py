from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from hpcrypto.tasks import update_prices_for_user
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Updates cryptocurrency prices for a specific user and triggers alerts if needed'

    def add_arguments(self, parser):
        parser.add_argument('user_id', type=int, help='ID of the user to update prices for')

    def handle(self, *args, **options):
        user_id = options['user_id']
        
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            raise CommandError(f'User with ID {user_id} does not exist')
        
        self.stdout.write(self.style.SUCCESS(f'Aktualizuję ceny kryptowalut dla użytkownika {user.username}...'))
        
        try:
            updated = update_prices_for_user(user)
            if updated is not None:
                self.stdout.write(
                    self.style.SUCCESS(f'Zaktualizowano {updated} pozycji dla użytkownika {user.username}')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'Błąd podczas aktualizacji cen kryptowalut dla użytkownika {user.username}')
                )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Błąd: {str(e)}'))
