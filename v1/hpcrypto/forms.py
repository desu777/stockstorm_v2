# hpcrypto/forms.py
from django import forms
from .models import HPCategory, Position, PriceAlert

class HPCategoryForm(forms.ModelForm):
    class Meta:
        model = HPCategory
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class PositionForm(forms.ModelForm):
    class Meta:
        model = Position
        fields = ['category', 'ticker', 'quantity', 'entry_price', 'exit_price', 'notes']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-control'}),
            'ticker': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Np. BTCUSDT, ETHUSDC - format wymagany przez Binance'
            }),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.00000001'}),
            'entry_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.00000001'}),
            'exit_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.00000001'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['ticker'].help_text = "Wprowadź ticker w formacie Binance, np. BTCUSDT, ETHUSDC. To jest wymagane do prawidłowego pobierania cen."

class PriceAlertForm(forms.ModelForm):
    class Meta:
        model = PriceAlert
        fields = ['alert_type', 'threshold_value', 'notes']
        widgets = {
            'alert_type': forms.Select(attrs={'class': 'form-control'}),
            'threshold_value': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.00000001'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Add notes about this alert (optional)'}),
        }
