"""
URL configuration for stockstorm_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static



urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('home.urls')),  # Dołączenie URL-i z aplikacji home
    path('hpcrypto/', include('hpcrypto.urls')),
    path('ai_agent/', include('ai_agent.urls')),  # Dodanie URL-i dla AI agenta
    path('gt/', include('gt.urls', namespace='gt')),  # Dodanie URL-i dla aplikacji GT z przestrzenią nazw
    path('livechat/', include('livechat.urls')),  # Dodanie URL-i dla aplikacji livechat
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)