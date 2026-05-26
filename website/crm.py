"""Best-effort sync of expo leads to Mhare CRM (email remains primary)."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import TYPE_CHECKING

from django.conf import settings

if TYPE_CHECKING:
    from .expo import ExpoLead

logger = logging.getLogger(__name__)


def push_expo_lead_to_crm(lead: ExpoLead) -> None:
    """
    POST lead to CRM after email succeeded. Failures are logged only (no visitor impact).
    """
    api_key = getattr(settings, 'CRM_INBOUND_API_KEY', '') or ''
    url = getattr(settings, 'CRM_EXPO_LEAD_URL', '') or ''
    if not api_key or not url:
        return

    from .expo import EVENT_DATE, EVENT_NAME, interest_labels

    body = json.dumps({
        'name': lead.name,
        'email': lead.email,
        'phone': lead.phone,
        'company': lead.company,
        'interests': lead.interests,
        'src': lead.src,
        'event_name': EVENT_NAME,
        'event_date': EVENT_DATE,
    }).encode('utf-8')

    req = urllib.request.Request(
        url,
        data=body,
        method='POST',
        headers={
            'Content-Type': 'application/json',
            'X-Mhare-Integration-Key': api_key,
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status >= 300:
                logger.warning(
                    'CRM expo lead sync unexpected status %s for %s',
                    resp.status,
                    lead.email,
                )
    except urllib.error.HTTPError as exc:
        logger.warning(
            'CRM expo lead sync HTTP %s for %s: %s',
            exc.code,
            lead.email,
            exc.read()[:500],
        )
    except Exception:
        logger.exception('CRM expo lead sync failed for %s', lead.email)
