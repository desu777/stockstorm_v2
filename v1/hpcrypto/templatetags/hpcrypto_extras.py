from django import template
from decimal import Decimal

register = template.Library()

@register.filter(name='multiply')
def multiply(value, arg):
    """Multiplies the value by the argument"""
    try:
        # Convert to Decimal objects for precise decimal arithmetic
        return Decimal(str(value)) * Decimal(str(arg))
    except (ValueError, TypeError):
        # Return 0 if the values can't be multiplied
        return 0 