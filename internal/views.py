from django.conf import settings
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from website.expo import is_rate_limited, record_submission

from . import assessment as az
from .middleware import SESSION_FLAG


@require_GET
def hub(request):
    return render(request, 'internal/hub.html', {'active': 'hub'})


def login_view(request):
    # If already in, or gate disabled in DEBUG, skip straight to the hub.
    password = getattr(settings, 'INTERNAL_PASSWORD', '')
    if request.session.get(SESSION_FLAG) or (not password and settings.DEBUG):
        return redirect('internal_hub')

    error = None
    next_url = request.GET.get('next') or request.POST.get('next') or reverse('internal_hub')
    if request.method == 'POST':
        if password and request.POST.get('password') == password:
            request.session[SESSION_FLAG] = True
            return redirect(next_url if next_url.startswith('/') else reverse('internal_hub'))
        error = 'Incorrect password.'
    return render(request, 'internal/login.html', {'error': error, 'next': next_url})


def logout_view(request):
    request.session.pop(SESSION_FLAG, None)
    return redirect('internal_login')


def _assessment_context(**extra):
    ctx = {
        'active': 'assessment',
        'objectives': az.OBJECTIVES,
        'features': az.FEATURES,
        'feature_choices': az.FEATURE_CHOICES,
        'fleet_cols': az.FLEET_COLS,
        'hw_cols': az.HW_COLS,
        'fleet_rows': range(4),
        'hw_rows': range(4),
    }
    ctx.update(extra)
    return ctx


@require_GET
def assessment(request):
    return render(request, 'internal/assessment.html',
                  _assessment_context(thanks=request.GET.get('thanks') == '1'))


@require_POST
def assessment_submit(request):
    if is_rate_limited(request):
        return render(request, 'internal/assessment.html', _assessment_context(
            form_error='Too many submissions from this connection. Please wait a while.',
            form_values=request.POST), status=429)

    err = az.validate(request.POST)
    if err == 'invalid':
        return redirect('/assessment/?thanks=1')  # honeypot — pretend success
    if err:
        return render(request, 'internal/assessment.html',
                      _assessment_context(form_error=err, form_values=request.POST), status=400)

    ok, mail_err = az.send_assessment_email(request.POST)
    if not ok:
        return render(request, 'internal/assessment.html',
                      _assessment_context(form_error=mail_err, form_values=request.POST), status=503)

    record_submission(request)
    return redirect('/assessment/?thanks=1')


@require_GET
def pricing(request):
    return render(request, 'internal/pricing.html', {'active': 'pricing'})


@require_GET
def downloads(request):
    return render(request, 'internal/downloads.html', {'active': 'downloads'})
