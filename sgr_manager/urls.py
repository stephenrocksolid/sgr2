"""
URL configuration for sgr_manager project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
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
from django.contrib.auth.views import LogoutView

from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required

@login_required
def redirect_to_machines(request):
    return redirect('inventory:machines_list')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),  # Add authentication URLs
    path("accounts/logout/", LogoutView.as_view(next_page="login"), name="logout"),
    path('', redirect_to_machines),  # Redirect root to machines
    path('core/', include('core.urls')),  # Core app URLs
    path('inventory/', include('inventory.urls')),  # Add back for sidebar navigation
    path('imports/', include('imports.urls')),
]

# Serve static and media files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
