# hpcrypto/management/commands/update_prices.py
# -----------------------------------------------------------------------------
# Komenda do aktualizacji cen kryptowalut z Binance
# 
# Uruchomienie serwisu aktualizacji cen w tle:
# python manage.py update_prices --daemon --interval 60
#
# Uruchomienie jednorazowej aktualizacji:
# python manage.py update_prices --one-time
# -----------------------------------------------------------------------------
import logging
import time
import sys
from django.core.management.base import BaseCommand
from django.utils import timezone
from hpcrypto.tasks import update_all_prices

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Update cryptocurrency prices for all positions using Binance API'

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=60,
            help='Interval between updates in seconds (default: 60)'
        )
        parser.add_argument(
            '--daemon',
            action='store_true',
            help='Run as a daemon (continuously in the background)'
        )
        parser.add_argument(
            '--one-time',
            action='store_true',
            help='Run once and exit (default behavior)'
        )

    def handle(self, *args, **options):
        interval = options['interval']
        daemon_mode = options['daemon']
        one_time = options['one_time']
        
        # If neither --daemon nor --one-time is specified, default to one-time
        if not daemon_mode and not one_time:
            one_time = True
        
        self.stdout.write(f'Starting cryptocurrency price update service...')
        if daemon_mode:
            self.stdout.write(f'Running in daemon mode with {interval} second interval')
            
        try:
            while True:
                start_time = time.time()
                self.stdout.write(f"{timezone.now().strftime('%Y-%m-%d %H:%M:%S')} - Updating prices...")
                
                # Call the task function that updates all prices
                update_count = update_all_prices()
                
                if update_count is not None:
                    self.stdout.write(self.style.SUCCESS(
                        f'Successfully updated prices for {update_count} positions'
                    ))
                else:
                    self.stdout.write(self.style.WARNING(
                        'Price update service completed with errors. Check logs for details.'
                    ))
                
                # If not in daemon mode, break after one run
                if not daemon_mode:
                    break
                
                # Calculate sleep time to maintain consistent interval
                elapsed = time.time() - start_time
                sleep_time = max(1, interval - elapsed)  # Ensure at least 1 second of sleep
                
                self.stdout.write(f"Next update in {sleep_time:.1f} seconds")
                time.sleep(sleep_time)
        
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('Price update service stopped by user'))
            sys.exit(0)
        except Exception as e:
            logger.error(f"Error running price update service: {str(e)}")
            self.stdout.write(self.style.ERROR(f'Error updating prices: {str(e)}'))
            if daemon_mode:
                # In daemon mode, we might want to continue despite errors
                self.stdout.write("Continuing after error in daemon mode...")
                time.sleep(interval)
            else:
                sys.exit(1)