from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
# Znajdź na początku pliku v1/home/forms.py
from .models import UserProfile, Bot, TelegramConfig  # Removing XTBConnection


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, label="Email")

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user

# bots/forms.py
class BotForm(forms.ModelForm):
    class Meta:
        model = Bot
        fields = ['name', 'broker_type', 'instrument', 'max_price', 'percent', 'capital', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter bot name'}),
            'broker_type': forms.Select(attrs={'class': 'form-control'}),
            'instrument': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. BTC-USD'}),
            'max_price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Maximum price to buy at'}),
            'percent': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Target profit percentage'}),
            'capital': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Amount to invest (USD)'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    # Optional API fields, shown only for certain broker types
    api_key = forms.CharField(
        max_length=255, 
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter API key'})
    )
    
    api_secret = forms.CharField(
        max_length=255, 
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter API secret'})
    )

    def __init__(self, *args, **kwargs):
        super(BotForm, self).__init__(*args, **kwargs)
        self.fields['name'].required = True
        self.fields['broker_type'].required = True
        self.fields['instrument'].required = True
        self.fields['max_price'].required = True
        self.fields['percent'].required = True
        self.fields['capital'].required = True
        
        # Add labels
        self.fields['is_active'].label = "Activate bot immediately"
        
        # Set initial values
        self.fields['is_active'].initial = True
        
    def clean_percent(self):
        percent = self.cleaned_data.get('percent')
        if percent is not None and percent <= 0:
            raise forms.ValidationError("Profit percentage must be greater than 0")
        return percent
    
    def clean_max_price(self):
        max_price = self.cleaned_data.get('max_price')
        if max_price is not None and max_price <= 0:
            raise forms.ValidationError("Maximum price must be greater than 0")
        return max_price
    
    def clean_capital(self):
        capital = self.cleaned_data.get('capital')
        if capital is not None and capital <= 0:
            raise forms.ValidationError("Capital must be greater than 0")
        return capital

#---------------------------------------------------------#

class BinanceApiForm(forms.ModelForm):
    binance_api_secret = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '••••••••'}),
        required=False,
        help_text="Leave empty to keep your existing secret"
    )
    
    class Meta:
        model = UserProfile
        fields = ['binance_api_key', 'telegram_notifications_enabled']
        widgets = {
            'binance_api_key': forms.TextInput(attrs={'class': 'form-control'}),
            'telegram_notifications_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Get the plaintext secret from the form
        binance_api_secret = self.cleaned_data.get('binance_api_secret')
        
        # Only update the secret if one was provided
        if binance_api_secret:
            instance.set_binance_api_secret(binance_api_secret)
            
        if commit:
            instance.save()
        
        return instance

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['profile_picture', 'telegram_notifications_enabled']
        widgets = {
            'telegram_notifications_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class TelegramCodeForm(forms.Form):
    code = forms.CharField(
        max_length=32,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter verification code'})
    )

class UserRegisterForm(UserCreationForm):
    email = forms.EmailField()
    registration_key = forms.CharField(max_length=50, required=True, help_text="Enter your registration key")

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'registration_key']

class TelegramConfigForm(forms.ModelForm):
    class Meta:
        model = TelegramConfig
        fields = ['verification_code']
        widgets = {
            'verification_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter verification code'})
        }