from django.core.cache import cache

class LiveStatusMiddleware:
    """
    Middleware dodające informację o statusie do kontekstu szablonów.
    Zmodyfikowano, aby nie używać XTBConnection po wyłączeniu API XTB.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Po wyłączeniu API XTB, zawsze ustawiamy is_live na False
        request.is_live = False
        
        response = self.get_response(request)
        return response
