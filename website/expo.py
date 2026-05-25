"""Expo QR contact capture — vCard, validation, email, rate limiting."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.utils import timezone

EXPO_SOURCES: dict[str, dict[str, str]] = {
    'mytrack': {
        'label': 'myTrack',
        'headline': 'Fleet intelligence, live.',
        'tagline': 'Share your details and we will follow up after the expo.',
    },
    'myroutes': {
        'label': 'myRoutes',
        'headline': 'Cut delivery kilometres.',
        'tagline': 'Share your details and we will follow up after the expo.',
    },
    'kasistock': {
        'label': 'KasiStock',
        'headline': 'Stop guessing. Start knowing.',
        'tagline': 'Share your details and we will follow up after the expo.',
    },
    'general': {
        'label': 'Mhare Tech',
        'headline': 'Software built for African logistics.',
        'tagline': 'Share your details and we will follow up after the expo.',
    },
}

DEFAULT_SRC = 'general'
RATE_LIMIT_MAX = 8
RATE_LIMIT_SECONDS = 3600

EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
PHONE_RE = re.compile(r'^[\d\s+\-().]{7,24}$')


@dataclass
class ExpoLead:
    name: str
    email: str
    phone: str
    company: str
    interest: str
    src: str
    consent: bool
    user_agent: str


def normalize_src(raw: str | None) -> str:
    key = (raw or '').strip().lower()
    return key if key in EXPO_SOURCES else DEFAULT_SRC


def source_context(src: str) -> dict[str, str]:
    return EXPO_SOURCES.get(src, EXPO_SOURCES[DEFAULT_SRC])


def build_vcard() -> str:
    """Organization vCard for visitors to save Mhare to their phone."""
    lines = [
        'BEGIN:VCARD',
        'VERSION:3.0',
        'FN:Mhare Consulting',
        'ORG:Mhare Consulting',
        'TITLE:Fleet & logistics software',
        'EMAIL;TYPE=work:sales@mhareconsulting.co.za',
        'TEL;TYPE=work:+27765168718',
        'URL:https://mharetech.co.za',
        'ADR;TYPE=work:;;Sandton;;;South Africa',
        'NOTE:Logistics Expo SA 2026 — myTrack, myRoutes, KasiStock by Mhare Tech',
        'END:VCARD',
    ]
    return '\r\n'.join(lines) + '\r\n'


def _client_ip(request) -> str:
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


def is_rate_limited(request) -> bool:
    ip = _client_ip(request)
    key = f'expo_submit:{ip}'
    count = cache.get(key, 0)
    return count >= RATE_LIMIT_MAX


def record_submission(request) -> None:
    ip = _client_ip(request)
    key = f'expo_submit:{ip}'
    count = cache.get(key, 0)
    cache.set(key, count + 1, RATE_LIMIT_SECONDS)


def parse_lead(post_data: dict[str, Any], user_agent: str) -> tuple[ExpoLead | None, str | None]:
    """Return (lead, error_message). error_message is set on validation failure."""
    honeypot = (post_data.get('website') or '').strip()
    if honeypot:
        return None, 'invalid'

    name = (post_data.get('name') or '').strip()
    email = (post_data.get('email') or '').strip()
    phone = (post_data.get('phone') or '').strip()
    company = (post_data.get('company') or '').strip()
    interest = normalize_src(post_data.get('interest') or post_data.get('src'))
    consent = post_data.get('consent') in ('on', 'true', '1', True)

    if not consent:
        return None, 'Please agree so we may store your details and follow up.'
    if not name or len(name) < 2:
        return None, 'Please enter your name.'
    if not email or not EMAIL_RE.match(email):
        return None, 'Please enter a valid email address.'
    if not phone or not PHONE_RE.match(phone):
        return None, 'Please enter a valid phone number.'

    return ExpoLead(
        name=name[:120],
        email=email[:254],
        phone=phone[:32],
        company=company[:120],
        interest=interest,
        src=interest,
        consent=True,
        user_agent=(user_agent or '')[:500],
    ), None


def send_lead_email(lead: ExpoLead) -> tuple[bool, str]:
    """Send lead notification. Returns (ok, message)."""
    to_addr = getattr(settings, 'EXPO_LEAD_TO', 'sales@mhareconsulting.co.za')
    from_addr = getattr(settings, 'EXPO_LEAD_FROM', None) or getattr(
        settings, 'DEFAULT_FROM_EMAIL', 'noreply@mharetech.co.za'
    )
    host = getattr(settings, 'EMAIL_HOST', '')
    if not host:
        return False, 'Email is not configured on the server yet. Please try again later or email sales@mhareconsulting.co.za.'

    product = source_context(lead.src)['label']
    now = timezone.localtime(timezone.now()).strftime('%Y-%m-%d %H:%M %Z')
    subject = f'[Expo] {product} lead — {lead.name}'
    body = '\n'.join([
        'New expo contact',
        '================',
        f'Name: {lead.name}',
        f'Email: {lead.email}',
        f'Phone: {lead.phone}',
        f'Company: {lead.company or "(not provided)"}',
        f'Interest: {product} ({lead.src})',
        f'Submitted: {now}',
        '',
        f'User-Agent: {lead.user_agent}',
    ])

    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=from_addr,
            recipient_list=[to_addr],
            fail_silently=False,
        )
        return True, ''
    except Exception:
        return False, 'We could not send your details right now. Please email sales@mhareconsulting.co.za directly.'
