"""myTrack Business Needs Assessment — web form schema + email builder.

No database: a completed assessment is emailed to the team (reuses the SMTP
config already used by website/expo.py). This module is the single source of
truth for field labels so the email body stays in sync with the form.
"""
from __future__ import annotations

import re

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')

# Objectives ranked 1-5 (section 4) and the feature matrix (section 5).
OBJECTIVES = [
    ('theft', 'Stop / reduce fuel theft'),
    ('visibility', 'Asset visibility & recovery'),
    ('safety', 'Driver safety & behaviour'),
    ('compliance', 'Compliance (licence / PDP expiry)'),
    ('utilisation', 'Utilisation & idle-cost reduction'),
    ('eta', 'Customer ETAs / delivery proof'),
    ('insurance', 'Insurance premium reduction'),
]

FEATURES = [
    ('live_gps', 'Live GPS tracking'),
    ('fuel_theft', 'Fuel theft detection'),
    ('driver_score', 'Driver behaviour scoring'),
    ('speed', 'Speed limit enforcement'),
    ('compliance', 'Compliance alerts (licence / PDP)'),
    ('fuel_reports', 'Fuel consumption reports'),
    ('whatsapp', 'WhatsApp driver notifications'),
    ('geofencing', 'Geofencing'),
    ('multi_depot', 'Multi-depot / multi-branch'),
    ('delivery_share', 'Delivery / customer tracking share'),
    ('idle_cost', 'Idle & fleet-cost reporting'),
    ('dwell', 'Geofence dwell-time reporting'),
]
FEATURE_CHOICES = [('must', 'Must-have'), ('nice', 'Nice-to-have'), ('no', 'Not needed')]

# Simple (non-table) fields grouped by section, in email order.
# (field_name, human label)
EMAIL_SECTIONS = [
    ('1. Client / Company Profile', [
        ('company', 'Company name'),
        ('industry', 'Industry / sector'),
        ('regno', 'Company reg. no.'),
        ('contact_name', 'Primary contact'),
        ('contact_role', 'Role'),
        ('contact_phone', 'Phone'),
        ('contact_email', 'Email'),
        ('decision_maker', 'Decision-maker (if different)'),
        ('billing', 'Billing contact & email'),
        ('depots_count', 'No. of branches / depots'),
        ('ho_location', 'Head-office location'),
    ]),
    ('3. Operational Context', [
        ('regions', 'Operating provinces / regions'),
        ('route_profile', 'Route profile'),
        ('yards', 'Depots & yards (locations)'),
        ('hours', 'Hours of operation'),
        ('shift', 'Shift pattern'),
    ]),
    ('7. Installation Logistics', [
        ('install_location', 'Install location'),
        ('sites_count', 'No. of sites'),
        ('furthest_km', 'Furthest site (km)'),
        ('downtime', 'Vehicle downtime windows'),
        ('autoelec', 'Certified auto-electrician on-site required'),
        ('sched_notes', 'Scheduling notes / constraints'),
    ]),
    ('8. Connectivity & Data', [
        ('sim_by', 'SIM / data supplied by'),
        ('coverage', 'Network coverage concerns'),
        ('roaming', 'Cross-border roaming required'),
    ]),
    ('9. Integration & Reporting', [
        ('existing_systems', 'Existing systems'),
        ('api_needed', 'API / integration needed'),
        ('users_count', 'No. of platform users / logins'),
        ('report_cadence', 'Report cadence'),
        ('whitelabel', 'White-label / client branding'),
    ]),
    ('10. Compliance & Data Governance', [
        ('popia', 'POPIA consent process'),
        ('retention', 'Required data-retention period'),
        ('data_owner', 'Data owner'),
    ]),
    ('11. Commercial', [
        ('budget', 'Budget range / expectation'),
        ('contract_term', 'Preferred contract term'),
        ('hw_billing', 'Hardware billing preference'),
        ('payment_terms', 'Payment terms'),
        ('billing_entity', 'Billing entity'),
    ]),
    ('12. Service & Support', [
        ('sla', 'SLA / response-time expectations'),
        ('training', 'Training required'),
        ('support_hours', 'Support hours expected'),
    ]),
    ('13. Sign-off', [
        ('assessor', 'myTrack assessor'),
        ('assessment_date', 'Date'),
    ]),
]

FLEET_COLS = [('qty', 'Qty'), ('type', 'Vehicle type'), ('makemodel', 'Make / Model'),
              ('year', 'Year'), ('fuel', 'Fuel'), ('tank', 'Tank (L)'),
              ('can', 'CAN?'), ('obd', 'OBD?')]
HW_COLS = [('group', 'Vehicle group'), ('source', 'Data source'),
           ('accessories', 'Accessories'), ('qty', 'Qty')]
MAX_ROWS = 12


def validate(post) -> str | None:
    """Return an error message, or None if the assessment is acceptable."""
    if (post.get('contact_hp') or '').strip():
        return 'invalid'  # honeypot tripped
    if not (post.get('company') or '').strip():
        return 'Please enter the company name.'
    email = (post.get('contact_email') or '').strip()
    if not email or not EMAIL_RE.match(email):
        return 'Please enter a valid primary contact email.'
    return None


def _vals(post, name) -> str:
    """Join one or more posted values for a field into a display string."""
    if hasattr(post, 'getlist'):
        items = [v.strip() for v in post.getlist(name) if v and v.strip()]
        if items:
            return ', '.join(items)
    v = post.get(name)
    return v.strip() if v else ''


def _table_rows(post, prefix, cols):
    rows = []
    for i in range(MAX_ROWS):
        cells = {key: (post.get(f'{prefix}_{i}_{key}') or '').strip() for key, _ in cols}
        if any(cells.values()):
            rows.append(cells)
    return rows


def build_email_body(post) -> str:
    lines = [
        'myTrack — Business Needs Assessment',
        '===================================',
        f'Submitted: {timezone.localtime(timezone.now()).strftime("%Y-%m-%d %H:%M %Z")}',
        '',
    ]

    def section(title):
        lines.append('')
        lines.append(title)
        lines.append('-' * len(title))

    # Section 1
    section(EMAIL_SECTIONS[0][0])
    for name, label in EMAIL_SECTIONS[0][1]:
        lines.append(f'{label}: {_vals(post, name) or "-"}')

    # Section 2 — Fleet table
    section('2. Fleet Profile')
    fleet = _table_rows(post, 'fleet', FLEET_COLS)
    if fleet:
        for r in fleet:
            lines.append('  ' + ' | '.join(f'{lab}: {r[key] or "-"}' for key, lab in FLEET_COLS))
    else:
        lines.append('  (none captured)')

    # Section 3
    sec3 = EMAIL_SECTIONS[1]
    section(sec3[0])
    for name, label in sec3[1]:
        lines.append(f'{label}: {_vals(post, name) or "-"}')

    # Section 4 — Objectives priorities
    section('4. Objectives & Pain Points (priority 1-5)')
    for key, label in OBJECTIVES:
        lines.append(f'{label}: {_vals(post, f"priority_{key}") or "-"}')
    if _vals(post, 'objectives_other'):
        lines.append(f'Other objectives: {_vals(post, "objectives_other")}')

    # Section 5 — Feature matrix
    section('5. Feature Requirements')
    choice_label = dict(FEATURE_CHOICES)
    for key, label in FEATURES:
        sel = _vals(post, f'feat_{key}')
        lines.append(f'{label}: {choice_label.get(sel, "-")}')

    # Section 6 — Hardware table
    section('6. Hardware Requirements')
    hw = _table_rows(post, 'hw', HW_COLS)
    if hw:
        for r in hw:
            lines.append('  ' + ' | '.join(f'{lab}: {r[key] or "-"}' for key, lab in HW_COLS))
    else:
        lines.append('  (none captured)')

    # Sections 7-13 (simple)
    for title, fields in EMAIL_SECTIONS[2:]:
        section(title)
        for name, label in fields:
            lines.append(f'{label}: {_vals(post, name) or "-"}')

    return '\n'.join(lines)


def send_assessment_email(post) -> tuple[bool, str]:
    """Email the completed assessment. Returns (ok, message)."""
    to_addr = getattr(settings, 'INTERNAL_ASSESSMENT_TO', '') or getattr(
        settings, 'EXPO_LEAD_TO', 'sales@mhareconsulting.co.za')
    from_addr = getattr(settings, 'EXPO_LEAD_FROM', None) or getattr(
        settings, 'DEFAULT_FROM_EMAIL', 'noreply@mharetech.co.za')
    if not getattr(settings, 'EMAIL_HOST', '') and not settings.DEBUG:
        return False, ('Email is not configured on the server yet. '
                       'Please try again later or email sales@mhareconsulting.co.za.')

    company = (post.get('company') or '').strip()
    subject = f'[Needs Assessment] {company}'
    try:
        send_mail(
            subject=subject,
            message=build_email_body(post),
            from_email=from_addr,
            recipient_list=[to_addr],
            fail_silently=False,
        )
        return True, ''
    except Exception:
        return False, ('We could not send the assessment right now. '
                       'Please email sales@mhareconsulting.co.za directly.')
