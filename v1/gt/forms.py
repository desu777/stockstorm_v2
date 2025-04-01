# gt/forms.py
from django import forms
from .models import GTCategory, StockPosition, StockPriceAlert

class GTCategoryForm(forms.ModelForm):
    class Meta:
        model = GTCategory
        fields = ['name', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class StockPositionForm(forms.ModelForm):
    class Meta:
        model = StockPosition
        fields = ['category', 'ticker', 'quantity', 'entry_price', 'exit_price', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['category'].queryset = GTCategory.objects.filter(user=user)
            self.fields['ticker'].widget.attrs.update({'placeholder': 'e.g., AAPL, MSFT, GOOGL'})
        
        # Dodanie atrybutów do pola exit_price
        self.fields['exit_price'].required = False
        self.fields['exit_price'].widget.attrs.update({'placeholder': 'Opcjonalna cena wyjścia'})
        self.fields['exit_price'].help_text = 'Wypełnij tylko jeśli pozycja jest zamknięta'

class StockPriceAlertForm(forms.ModelForm):
    class Meta:
        model = StockPriceAlert
        fields = ['alert_type', 'threshold_value', 'notes', 'notify_telegram']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        position = kwargs.pop('position', None)
        super().__init__(*args, **kwargs)
        self.fields['threshold_value'].widget.attrs.update({'step': '0.01'})
        if position:
            self.instance.position = position 