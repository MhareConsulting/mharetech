"""Expo QR contact capture — vCard, validation, email, rate limiting."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.utils import timezone

EVENT_NAME = 'Sloane Connect'
EVENT_DATE = 'Friday 29 May'

EXPO_SOURCES: dict[str, dict[str, str]] = {
    'mytrack': {
        'label': 'myTrack',
        'headline': 'Fleet intelligence, live.',
        'tagline': f'Share your details and we will follow up after {EVENT_NAME}.',
    },
    'myroutes': {
        'label': 'myRoutes',
        'headline': 'Cut delivery kilometres.',
        'tagline': f'Share your details and we will follow up after {EVENT_NAME}.',
    },
    'kasistock': {
        'label': 'KasiStock',
        'headline': 'Stop guessing. Start knowing.',
        'tagline': f'Share your details and we will follow up after {EVENT_NAME}.',
    },
    'general': {
        'label': 'Mhare Tech',
        'headline': 'Software built for African logistics.',
        'tagline': f'Share your details and we will follow up after {EVENT_NAME}.',
    },
}

EXPO_PRODUCT_OPTIONS = [
    ('mytrack', 'myTrack'),
    ('myroutes', 'myRoutes'),
    ('kasistock', 'KasiStock'),
    ('general', 'Mhare Tech (general)'),
]

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
    interests: list[str]
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
        f'NOTE:{EVENT_NAME} — {EVENT_DATE} — myTrack, myRoutes, KasiStock by Mhare Tech',
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


def parse_interests(post_data: Any, fallback_src: str | None = None) -> list[str]:
    """Read one or more interest values from form POST data."""
    if hasattr(post_data, 'getlist'):
        raw = post_data.getlist('interest')
    else:
        val = post_data.get('interest') if hasattr(post_data, 'get') else None
        raw = val if isinstance(val, list) else ([val] if val else [])

    selected: list[str] = []
    for item in raw:
        key = normalize_src(item)
        if key not in selected:
            selected.append(key)

    if not selected and fallback_src:
        selected = [normalize_src(fallback_src)]
    return selected


def parse_lead(post_data: Any, user_agent: str) -> tuple[ExpoLead | None, str | None]:
    """Return (lead, error_message). error_message is set on validation failure."""
    honeypot = (post_data.get('website') or '').strip()
    if honeypot:
        return None, 'invalid'

    name = (post_data.get('name') or '').strip()
    email = (post_data.get('email') or '').strip()
    phone = (post_data.get('phone') or '').strip()
    company = (post_data.get('company') or '').strip()
    qr_src = normalize_src(post_data.get('src'))
    interests = parse_interests(post_data)
    consent = post_data.get('consent') in ('on', 'true', '1', True)

    if not consent:
        return None, 'Please agree so we may store your details and follow up.'
    if not interests:
        return None, 'Please select at least one product you are interested in.'
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
        interests=interests,
        src=qr_src,
        consent=True,
        user_agent=(user_agent or '')[:500],
    ), None


def interest_labels(keys: list[str]) -> str:
    return ', '.join(source_context(k)['label'] for k in keys)


def send_lead_email(lead: ExpoLead) -> tuple[bool, str]:
    """Send lead notification. Returns (ok, message)."""
    to_addr = getattr(settings, 'EXPO_LEAD_TO', 'sales@mhareconsulting.co.za')
    from_addr = getattr(settings, 'EXPO_LEAD_FROM', None) or getattr(
        settings, 'DEFAULT_FROM_EMAIL', 'noreply@mharetech.co.za'
    )
    host = getattr(settings, 'EMAIL_HOST', '')
    if not host:
        return False, 'Email is not configured on the server yet. Please try again later or email sales@mhareconsulting.co.za.'

    products = interest_labels(lead.interests)
    scan_label = source_context(lead.src)['label']
    now = timezone.localtime(timezone.now()).strftime('%Y-%m-%d %H:%M %Z')
    subject = f'[{EVENT_NAME}] {products} — {lead.name}'
    body = '\n'.join([
        f'New contact — {EVENT_NAME} ({EVENT_DATE})',
        '================',
        f'Name: {lead.name}',
        f'Email: {lead.email}',
        f'Phone: {lead.phone}',
        f'Company: {lead.company or "(not provided)"}',
        f'Interested in: {products}',
        f'QR / scan source: {scan_label} ({lead.src})',
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
