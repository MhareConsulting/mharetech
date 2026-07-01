"""Root URLconf for the internal.mharetech.co.za subdomain.

InternalGateMiddleware swaps request.urlconf to this module when the request
host starts with 'internal.'. The public site keeps using mharetech.urls.
"""
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', include('internal.urls')),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
