"""Needs-assessment engine — schema-driven form + email, per product.

Each product defines an ordered list of SECTIONS. A section has a title and a
list of blocks; each block is one of a small set of kinds the generic template
(templates/internal/assessment.html) and the email builder both understand:

  fields   — labelled inputs (text/email/tel/number/textarea)
  choice   — radio (single) or checkbox (multi) option group
  table    — repeating rows (e.g. fleet / hardware), with add-row support
  priority — rank-1-5 number per item
  matrix   — must/nice/no radio per feature row
  note     — helper text (not captured)

No database: a completed assessment is emailed (reuses the SMTP config used by
website/expo.py). Adding a product = add a schema below + register it.
"""
from __future__ import annotations

import re

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')

FEATURE_CHOICES = [('must', 'Must-have'), ('nice', 'Nice-to-have'), ('no', 'Not needed')]
YN = ['Yes', 'No']


# ── block helpers ───────────────────────────────────────────────────────────
def fields(*items, cols=2):
    return {'kind': 'fields', 'cols': cols, 'items': [
        {'name': n, 'label': l, 'type': t, 'full': full} for (n, l, t, full) in items]}


def F(name, label, type='text', full=False):
    return (name, label, type, full)


def choice(name, label, options, multi=False):
    return {'kind': 'choice', 'name': name, 'label': label, 'options': options, 'multi': multi}


def table(prefix, cols, rows=4):
    return {'kind': 'table', 'prefix': prefix, 'cols': cols, 'rows': rows}


def col(key, label, input='text', options=None):
    return {'key': key, 'label': label, 'input': input, 'options': options or []}


def priority(items):
    return {'kind': 'priority', 'items': [{'key': k, 'label': l} for k, l in items]}


def matrix(name, items):
    return {'kind': 'matrix', 'name': name, 'choices': FEATURE_CHOICES,
            'items': [{'key': k, 'label': l} for k, l in items]}


def note(text):
    return {'kind': 'note', 'text': text}


def section(title, *blocks, sub=None):
    return {'title': title, 'sub': sub, 'blocks': list(blocks)}


# ── myTrack assessment ──────────────────────────────────────────────────────
MYTRACK = {
    'slug': 'mytrack',
    'name': 'myTrack',
    'title': 'Business Needs Assessment',
    'sections': [
        section('1 · Client / Company Profile', fields(
            F('company', 'Company name *', full=True),
            F('industry', 'Industry / sector'), F('regno', 'Company reg. no.'),
            F('contact_name', 'Primary contact'), F('contact_role', 'Role'),
            F('contact_phone', 'Phone', 'tel'), F('contact_email', 'Email *', 'email'),
            F('decision_maker', 'Decision-maker (if different)'),
            F('billing', 'Billing contact & email'),
            F('depots_count', 'No. of branches / depots', 'number'),
            F('ho_location', 'Head-office location'),
        )),
        section('2 · Fleet Profile',
            note('One row per vehicle group. Tank size + CAN/OBD availability drive hardware and unit cost.'),
            table('fleet', [
                col('qty', 'Qty', 'text'), col('type', 'Vehicle type'), col('makemodel', 'Make / Model'),
                col('year', 'Year'), col('fuel', 'Fuel'), col('tank', 'Tank (L)'),
                col('can', 'CAN? Y/N', 'select', ['', 'Y', 'N']),
                col('obd', 'OBD? Y/N', 'select', ['', 'Y', 'N'])])),
        section('3 · Operational Context',
            fields(F('regions', 'Operating provinces / regions', full=True)),
            choice('route_profile', 'Route profile',
                   ['Local / urban', 'Long-haul', 'Cross-border (roaming)'], multi=True),
            fields(F('yards', 'Depots & yards (locations)', full=True),
                   F('hours', 'Hours of operation'), F('shift', 'Shift pattern'))),
        section('4 · Objectives & Pain Points',
            note('Rank priorities 1 (highest) to 5. Leave blank if not relevant.'),
            priority([('theft', 'Stop / reduce fuel theft'), ('visibility', 'Asset visibility & recovery'),
                      ('safety', 'Driver safety & behaviour'), ('compliance', 'Compliance (licence / PDP expiry)'),
                      ('utilisation', 'Utilisation & idle-cost reduction'), ('eta', 'Customer ETAs / delivery proof'),
                      ('insurance', 'Insurance premium reduction')]),
            fields(F('objectives_other', 'Other objectives', full=True))),
        section('5 · Feature Requirements',
            note('Mark each myTrack feature as Must-have, Nice-to-have, or Not needed.'),
            matrix('feat', [
                ('live_gps', 'Live GPS tracking'), ('fuel_theft', 'Fuel theft detection'),
                ('driver_score', 'Driver behaviour scoring'), ('speed', 'Speed limit enforcement'),
                ('compliance', 'Compliance alerts (licence / PDP)'), ('fuel_reports', 'Fuel consumption reports'),
                ('whatsapp', 'WhatsApp driver notifications'), ('geofencing', 'Geofencing'),
                ('multi_depot', 'Multi-depot / multi-branch'), ('delivery_share', 'Delivery / customer tracking share'),
                ('idle_cost', 'Idle & fleet-cost reporting'), ('dwell', 'Geofence dwell-time reporting')])),
        section('6 · Hardware Requirements',
            note('Base unit = Teltonika FMB tracker. Data source: CAN adapter (LV-CAN200) preferred, '
                 'OBD plug for light vehicles, LLS fuel probe as fallback. Accessories: panic, immobiliser, '
                 'RFID / iButton, temp sensor, backup battery.'),
            table('hw', [
                col('group', 'Vehicle group'),
                col('source', 'Data source (CAN/OBD/Probe)', 'select', ['', 'CAN', 'OBD', 'Probe', 'None']),
                col('accessories', 'Accessories required'), col('qty', 'Qty')])),
        section('7 · Installation Logistics',
            choice('install_location', 'Install location',
                   ['At depot (single site)', 'Multiple sites', 'Mobile / on-site'], multi=True),
            fields(F('sites_count', 'No. of sites', 'number'), F('furthest_km', 'Furthest site (km)', 'number'),
                   F('downtime', 'Vehicle downtime windows available', full=True)),
            choice('autoelec', 'Certified auto-electrician on-site required?', YN),
            fields(F('sched_notes', 'Scheduling notes / constraints', 'textarea', full=True))),
        section('8 · Connectivity & Data',
            choice('sim_by', 'SIM / data supplied by', ['myTrack', 'Client']),
            choice('roaming', 'Cross-border roaming required?', YN),
            fields(F('coverage', 'Network coverage concerns in operating area', full=True))),
        section('9 · Integration & Reporting',
            fields(F('existing_systems', 'Existing systems (ERP / fuel cards / accounting)', full=True)),
            choice('api_needed', 'API / integration needed?', YN),
            choice('whitelabel', 'White-label / client branding required?', YN),
            fields(F('users_count', 'No. of platform users / logins', 'number'),
                   F('report_cadence', 'Report cadence'))),
        section('10 · Compliance & Data Governance',
            choice('popia', 'POPIA consent process in place for driver tracking?', ['Yes', 'No', 'Needs guidance']),
            fields(F('retention', 'Required data-retention period'), F('data_owner', 'Data owner'))),
        section('11 · Commercial',
            fields(F('budget', 'Budget range / expectation', full=True)),
            choice('contract_term', 'Preferred contract term', ['12 months', '24 months', '36 months']),
            choice('hw_billing', 'Hardware billing preference', ['Upfront (once-off)', 'Amortised into monthly']),
            fields(F('payment_terms', 'Payment terms'), F('billing_entity', 'Billing entity'))),
        section('12 · Service & Support',
            fields(F('sla', 'SLA / response-time expectations', full=True)),
            choice('training', 'Training required?', ['Yes - on-site', 'Yes - remote', 'No']),
            fields(F('support_hours', 'Support hours expected', full=True))),
        section('13 · Sign-off',
            fields(F('assessor', 'myTrack assessor'), F('assessment_date', 'Date'))),
    ],
}


# ── myRoutes assessment ─────────────────────────────────────────────────────
MYROUTES = {
    'slug': 'myroutes',
    'name': 'myRoutes',
    'title': 'Route Optimisation Needs Assessment',
    'sections': [
        section('1 · Client / Company Profile', fields(
            F('company', 'Company name *', full=True),
            F('industry', 'Industry / sector'), F('regno', 'Company reg. no.'),
            F('contact_name', 'Primary contact'), F('contact_role', 'Role'),
            F('contact_phone', 'Phone', 'tel'), F('contact_email', 'Email *', 'email'),
            F('decision_maker', 'Decision-maker (if different)'),
            F('billing', 'Billing contact & email'),
            F('depots_count', 'No. of depots / branches', 'number'),
            F('ho_location', 'Head-office location'),
        )),
        section('2 · Operation Profile',
            note('The daily dispatch picture — drives how much routing work myRoutes is doing.'),
            fields(
                F('regions', 'Operating provinces / regions', full=True),
                F('delivery_days', 'Delivery days per week', 'number'),
                F('avg_stops_day', 'Average stops / deliveries per day', 'number'),
                F('peak_stops_day', 'Peak stops per day', 'number'),
                F('vehicles_delivery', 'Vehicles used for delivery', 'number'),
                F('drivers_count', 'Number of drivers', 'number'),
                F('dispatch_start', 'Dispatch start time'))),
        section('3 · Current Routing Method',
            choice('current_method', 'How are routes planned today?',
                   ['Manually / by memory', 'Spreadsheet / map', 'Other routing software', 'Not planned']),
            fields(F('planning_time', 'Time spent planning routes daily'),
                   F('planning_pain', 'Biggest routing pain points', 'textarea', full=True))),
        section('4 · Fleet & Constraints',
            fields(F('vehicle_types', 'Vehicle types (van / rigid / bike / bakkie …)', full=True)),
            choice('capacity_basis', 'Capacity is measured by',
                   ['Weight', 'Volume', 'Pallets', 'Units / cases', 'Mixed']),
            fields(F('capacity_notes', 'Capacity per vehicle (notes)', full=True),
                   F('driver_hours', 'Driver hours / shift limits')),
            choice('delivery_windows', 'Customer delivery windows', ['Strict', 'Soft / preferred', 'None']),
            choice('constraints', 'Special constraints',
                   ['Cold chain', 'Zone / area rules', 'Time windows', 'Load-shedding aware', 'Backhauls / collections'],
                   multi=True)),
        section('5 · Stops & Orders',
            choice('order_source', 'Where do stops / orders come from?',
                   ['ERP', 'WMS / KasiStock', 'CSV / Excel upload', 'e-commerce / online', 'Manual entry']),
            choice('address_quality', 'Address data quality', ['Good / structured', 'Mixed', 'Poor / freeform']),
            choice('geocoding_need', 'Geocoding & address validation needed?', YN),
            fields(F('order_cutoff', 'Daily order cut-off time'))),
        section('6 · Objectives & Pain Points',
            note('Rank priorities 1 (highest) to 5. Leave blank if not relevant.'),
            priority([('distance', 'Cut distance / kilometres'), ('drops', 'Fit more drops per day'),
                      ('ontime', 'Improve on-time delivery'), ('planning', 'Save dispatcher planning time'),
                      ('pod', 'Proof of delivery'), ('fuel', 'Reduce fuel cost'),
                      ('visibility', 'Customer delivery visibility')]),
            fields(F('objectives_other', 'Other objectives', full=True))),
        section('7 · Feature Requirements',
            note('Mark each myRoutes feature as Must-have, Nice-to-have, or Not needed.'),
            matrix('feat', [
                ('optimise', 'Multi-stop route optimisation'), ('dispatch', 'Drag-and-drop dispatch'),
                ('constraints', 'Fleet capacity / constraint rules'), ('geocode', 'Address geocoding & validation'),
                ('reoptimise', 'Live re-optimisation'), ('analysis', 'Post-run analysis & replay'),
                ('driverapp', 'Driver app / turn-by-turn'), ('wapod', 'WhatsApp proof-of-delivery'),
                ('loadshed', 'Load-shedding-aware dispatch')])),
        section('8 · Integration & Users',
            fields(F('existing_systems', 'Existing systems (ERP / WMS / e-commerce)', full=True)),
            choice('api_needed', 'API / integration needed?', YN),
            fields(F('export_needs', 'Export / reporting needs'),
                   F('users_seats', 'Dispatcher / planner seats', 'number'))),
        section('9 · Compliance & Data Governance',
            choice('popia', 'POPIA consent process in place?', ['Yes', 'No', 'Needs guidance']),
            fields(F('retention', 'Required data-retention period'), F('data_owner', 'Data owner'))),
        section('10 · Commercial',
            fields(F('budget', 'Budget range / expectation', full=True)),
            choice('contract_term', 'Preferred contract term', ['12 months', '24 months', '36 months']),
            choice('billing_cycle', 'Billing cycle', ['Monthly', 'Annual']),
            fields(F('payment_terms', 'Payment terms'), F('billing_entity', 'Billing entity'))),
        section('11 · Service & Support',
            fields(F('sla', 'SLA / response-time expectations', full=True)),
            choice('training', 'Training required?', ['Yes - on-site', 'Yes - remote', 'No']),
            fields(F('onboarding', 'Target go-live / onboarding timeline'),
                   F('support_hours', 'Support hours expected'))),
        section('12 · Sign-off',
            fields(F('assessor', 'myRoutes assessor'), F('assessment_date', 'Date'))),
    ],
}

ASSESSMENTS = {MYTRACK['slug']: MYTRACK, MYROUTES['slug']: MYROUTES}


# ── submission handling ─────────────────────────────────────────────────────
def validate(post) -> str | None:
    if (post.get('contact_hp') or '').strip():
        return 'invalid'  # honeypot
    if not (post.get('company') or '').strip():
        return 'Please enter the company name.'
    email = (post.get('contact_email') or '').strip()
    if not email or not EMAIL_RE.match(email):
        return 'Please enter a valid primary contact email.'
    return None


def _vals(post, name) -> str:
    if hasattr(post, 'getlist'):
        items = [v.strip() for v in post.getlist(name) if v and v.strip()]
        if items:
            return ', '.join(items)
    v = post.get(name)
    return v.strip() if v else ''


def _table_rows(post, prefix, cols):
    rows = []
    for i in range(12):
        cells = {c['key']: (post.get(f'{prefix}_{i}_{c["key"]}') or '').strip() for c in cols}
        if any(cells.values()):
            rows.append(cells)
    return rows


def build_email_body(post, cfg) -> str:
    lines = [f'{cfg["name"]} — {cfg["title"]}', '=' * 40,
             f'Submitted: {timezone.localtime(timezone.now()).strftime("%Y-%m-%d %H:%M %Z")}', '']
    choice_label = dict(FEATURE_CHOICES)
    for sec in cfg['sections']:
        lines.append(''); lines.append(sec['title']); lines.append('-' * len(sec['title']))
        for b in sec['blocks']:
            kind = b['kind']
            if kind == 'fields':
                for it in b['items']:
                    lines.append(f'{it["label"].rstrip(" *")}: {_vals(post, it["name"]) or "-"}')
            elif kind == 'choice':
                lines.append(f'{b["label"]}: {_vals(post, b["name"]) or "-"}')
            elif kind == 'table':
                rows = _table_rows(post, b['prefix'], b['cols'])
                if rows:
                    for r in rows:
                        lines.append('  ' + ' | '.join(f'{c["label"]}: {r[c["key"]] or "-"}' for c in b['cols']))
                else:
                    lines.append('  (none captured)')
            elif kind == 'priority':
                for it in b['items']:
                    lines.append(f'{it["label"]}: {_vals(post, "priority_" + it["key"]) or "-"}')
            elif kind == 'matrix':
                for it in b['items']:
                    lines.append(f'{it["label"]}: {choice_label.get(_vals(post, b["name"] + "_" + it["key"]), "-")}')
    return '\n'.join(lines)


def send_assessment_email(post, cfg) -> tuple[bool, str]:
    to_addr = getattr(settings, 'INTERNAL_ASSESSMENT_TO', '') or getattr(
        settings, 'EXPO_LEAD_TO', 'sales@mhareconsulting.co.za')
    from_addr = getattr(settings, 'EXPO_LEAD_FROM', None) or getattr(
        settings, 'DEFAULT_FROM_EMAIL', 'noreply@mharetech.co.za')
    if not getattr(settings, 'EMAIL_HOST', '') and not settings.DEBUG:
        return False, ('Email is not configured on the server yet. '
                       'Please try again later or email sales@mhareconsulting.co.za.')
    company = (post.get('company') or '').strip()
    subject = f'[{cfg["name"]} Assessment] {company}'
    try:
        send_mail(subject=subject, message=build_email_body(post, cfg),
                  from_email=from_addr, recipient_list=[to_addr], fail_silently=False)
        return True, ''
    except Exception:
        return False, ('We could not send the assessment right now. '
                       'Please email sales@mhareconsulting.co.za directly.')
