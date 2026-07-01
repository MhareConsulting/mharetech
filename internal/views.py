import json

from django.conf import settings
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from website.expo import is_rate_limited, record_submission

from . import assessments as az
from . import pricing_config as pc
from .middleware import SESSION_FLAG
from .quote_pdf import build_quote_pdf

# Per-product portal metadata (name + which tools/resources exist).
PRODUCTS = {
    'mytrack': {'name': 'myTrack', 'tagline': 'Fleet telematics — tracking, fuel & driver behaviour.'},
    'myroutes': {'name': 'myRoutes', 'tagline': 'Route optimisation — plan, dispatch, analyse.'},
}

DOWNLOADS = {
    'mytrack': [
        ('Needs Assessment (Word)', 'Editable 13-section requirements form.',
         'internal/downloads/myTrack_Needs_Assessment.docx', '.docx'),
        ('Needs Assessment (PDF)', 'Fillable / printable form with signature block.',
         'internal/downloads/myTrack_Needs_Assessment.pdf', '.pdf'),
        ('Pricing Toolkit (Excel)', 'Cost inputs, quote builder, tier rate card.',
         'internal/downloads/myTrack_Pricing_Toolkit.xlsx', '.xlsx'),
    ],
}


def _product(slug):
    if slug not in PRODUCTS:
        raise Http404('Unknown product')
    return PRODUCTS[slug]


# ── portal ──────────────────────────────────────────────────────────────────
@require_GET
def home(request):
    return render(request, 'internal/home.html', {'active': 'home', 'products': PRODUCTS})


@require_GET
def toolkit(request, product):
    meta = _product(product)
    return render(request, 'internal/toolkit.html', {
        'active': product, 'product': product, 'product_name': meta['name'],
        'tagline': meta['tagline'], 'has_downloads': product in DOWNLOADS,
    })


# ── gate ────────────────────────────────────────────────────────────────────
def login_view(request):
    password = getattr(settings, 'INTERNAL_PASSWORD', '')
    if request.session.get(SESSION_FLAG) or (not password and settings.DEBUG):
        return redirect('internal_home')
    error = None
    next_url = request.GET.get('next') or request.POST.get('next') or reverse('internal_home')
    if request.method == 'POST':
        if password and request.POST.get('password') == password:
            request.session[SESSION_FLAG] = True
            return redirect(next_url if next_url.startswith('/') else reverse('internal_home'))
        error = 'Incorrect password.'
    return render(request, 'internal/login.html', {'error': error, 'next': next_url})


def logout_view(request):
    request.session.pop(SESSION_FLAG, None)
    return redirect('internal_login')


# ── assessment ──────────────────────────────────────────────────────────────
def _assessment_ctx(product, cfg, **extra):
    ctx = {'active': product, 'product': product, 'product_name': cfg['name'],
           'title': cfg['title'], 'sections': cfg['sections']}
    ctx.update(extra)
    return ctx


@require_GET
def assessment(request, product):
    _product(product)
    cfg = az.ASSESSMENTS[product]
    return render(request, 'internal/assessment.html',
                  _assessment_ctx(product, cfg, thanks=request.GET.get('thanks') == '1'))


@require_POST
def assessment_submit(request, product):
    _product(product)
    cfg = az.ASSESSMENTS[product]
    done = reverse('internal_assessment', args=[product]) + '?thanks=1'

    if is_rate_limited(request):
        return render(request, 'internal/assessment.html', _assessment_ctx(
            product, cfg, form_error='Too many submissions from this connection. Please wait a while.',
            form_values=request.POST), status=429)

    err = az.validate(request.POST)
    if err == 'invalid':
        return redirect(done)  # honeypot
    if err:
        return render(request, 'internal/assessment.html',
                      _assessment_ctx(product, cfg, form_error=err, form_values=request.POST), status=400)

    ok, mail_err = az.send_assessment_email(request.POST, cfg)
    if not ok:
        return render(request, 'internal/assessment.html',
                      _assessment_ctx(product, cfg, form_error=mail_err, form_values=request.POST), status=503)

    record_submission(request)
    return redirect(done)


# ── pricing ─────────────────────────────────────────────────────────────────
@require_GET
@ensure_csrf_cookie
def pricing(request, product):
    _product(product)
    cfg = pc.PRICING[product]
    return render(request, 'internal/pricing.html', {
        'active': product, 'product': product, 'product_name': cfg['name'],
        'config_json': json.dumps(cfg),
        'has_downloads': product in DOWNLOADS,
    })


@require_POST
def quote_pdf(request):
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except (ValueError, UnicodeDecodeError):
        return HttpResponse('Bad request', status=400)
    pdf = build_quote_pdf(payload)
    resp = HttpResponse(pdf, content_type='application/pdf')
    ref = (payload.get('quote_ref') or 'quote').replace('/', '-')
    resp['Content-Disposition'] = f'attachment; filename="Mhare_Quote_{ref}.pdf"'
    return resp


# ── downloads ───────────────────────────────────────────────────────────────
@require_GET
def downloads(request, product):
    _product(product)
    items = DOWNLOADS.get(product)
    if not items:
        raise Http404('No downloads for this product')
    return render(request, 'internal/downloads.html', {
        'active': product, 'product': product,
        'product_name': PRODUCTS[product]['name'], 'items': items,
    })
