"""Host-based routing + password gate for the internal subdomain.

When the request host starts with ``internal.`` this middleware:
  1. Swaps ``request.urlconf`` to ``mharetech.internal_urls`` so the subdomain
     serves the internal tool set (the public site is untouched).
  2. Enforces a shared-password gate backed by a signed-cookie session — no DB.
     Login posts a password compared to ``settings.INTERNAL_PASSWORD``.

In DEBUG with no ``INTERNAL_PASSWORD`` set, the gate is bypassed for convenience.
"""
from django.conf import settings
from django.http import HttpResponseRedirect
from django.urls import reverse

INTERNAL_URLCONF = 'mharetech.internal_urls'
SESSION_FLAG = 'internal_ok'


def _is_internal_host(request) -> bool:
    return request.get_host().split(':')[0].startswith('internal.')


class InternalGateMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not _is_internal_host(request):
            return self.get_response(request)

        # Route this host to the internal URL tree.
        request.urlconf = INTERNAL_URLCONF

        if not self._gate_passed(request) and self._needs_gate(request):
            login_url = reverse('internal_login', urlconf=INTERNAL_URLCONF)
            if request.path != login_url:
                return HttpResponseRedirect(f'{login_url}?next={request.path}')

        return self.get_response(request)

    @staticmethod
    def _gate_passed(request) -> bool:
        password = getattr(settings, 'INTERNAL_PASSWORD', '')
        if not password and settings.DEBUG:
            return True  # dev convenience when no password configured
        return bool(request.session.get(SESSION_FLAG))

    @staticmethod
    def _needs_gate(request) -> bool:
        path = request.path
        login_url = reverse('internal_login', urlconf=INTERNAL_URLCONF)
        # Login page and static assets stay open so the gate can render.
        if path == login_url or path.startswith(settings.STATIC_URL):
            return False
        return True
