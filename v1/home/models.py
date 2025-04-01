# models.py
from django.db import models
from django.contrib.auth.models import User
from cryptography.fernet import Fernet

FERNET_KEY = 'GiLFpoI4-TzsPAheWRYytzPXuOlZVHOz5FrZsjHYZSk='  # Klucz do szyfrowania/dekryptacji
fernet = Fernet(FERNET_KEY)

class Bot(models.Model):
    STATUS_CHOICES = (
        ('NEW', 'New'),
        ('RUNNING', 'Running'),
        ('FINISHED', 'Finished'),
        ('ERROR', 'Error'),
    )

    BROKER_CHOICES = (
    ('BNB', 'Binance'),
    )
    broker_type = models.CharField(
        max_length=3,
        choices=BROKER_CHOICES,
        default='BNB'
    )


    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    instrument = models.CharField(max_length=50)
    max_price = models.DecimalField(max_digits=10, decimal_places=2)
    percent = models.IntegerField()
    capital = models.DecimalField(max_digits=12, decimal_places=2)
    stream_session_id = models.CharField(max_length=200, blank=True, null=True)
    is_active = models.BooleanField(default=True, help_text="Whether the bot is active or not")
    total_profit = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, help_text="Total profit accumulated by this bot")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='NEW')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  # Adding updated_at field
    finished_at = models.DateTimeField(null=True, blank=True)  # Zaktualizowane pole
    # id bota w mikroserwisie
    microservice_bot_id = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return f"Bot {self.name} (user={self.user}, {self.instrument}, {self.status})"


# Update UserProfile model in home/models.py
# Updated UserProfile model in home/models.py
class UserProfile(models.Model):
    # Existing fields
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    # Profile picture field
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    
    # Binance API fields
    binance_api_key = models.CharField(max_length=255, blank=True, null=True)
    binance_api_secret_enc = models.BinaryField(blank=True, null=True)
    
    # Telegram notification preferences
    telegram_notifications_enabled = models.BooleanField(default=False, verbose_name="Enable Telegram Notifications")
    
    def set_binance_api_secret(self, plain_secret):
        """Encrypts and stores the Binance API secret"""
        if plain_secret:
            self.binance_api_secret_enc = fernet.encrypt(plain_secret.encode('utf-8'))
    
    def get_binance_api_secret(self):
        """Decrypts and returns the Binance API secret"""
        if self.binance_api_secret_enc:
            return fernet.decrypt(self.binance_api_secret_enc).decode('utf-8')
        return None

class TelegramConfig(models.Model):
    """Configuration for Telegram bot for a specific user"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='telegram_config')
    chat_id = models.CharField(max_length=255, help_text="Telegram chat ID for notifications")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    verification_code = models.CharField(max_length=32, blank=True, null=True, 
                                        help_text="Temporary code for verifying Telegram account ownership")
    is_verified = models.BooleanField(default=False, 
                                     help_text="Whether the Telegram chat ID has been verified")
    
    def __str__(self):
        return f"Telegram config for {self.user.username}"

class BotLog(models.Model):
    """Logi dla botów, przechowujące informacje o statusie i ważnych wydarzeniach"""
    bot = models.ForeignKey(Bot, on_delete=models.CASCADE, related_name='logs')
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Log dla {self.bot.name}: {self.message[:50]}..."