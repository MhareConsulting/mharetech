from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from .crm import push_expo_lead_to_crm
from .expo import (
    EVENT_DATE,
    EVENT_NAME,
    EXPO_PRODUCT_OPTIONS,
    build_vcard,
    is_rate_limited,
    normalize_src,
    parse_interests,
    parse_lead,
    record_submission,
    send_lead_email,
    source_context,
)


def _expo_context(
    *,
    src: str,
    thanks: bool = False,
    form_error: str | None = None,
    post=None,
) -> dict:
    selected = parse_interests(post, fallback_src=src) if post else [src]
    return {
        'src': src,
        'source': source_context(src),
        'event_name': EVENT_NAME,
        'event_date': EVENT_DATE,
        'thanks': thanks,
        'form_error': form_error,
        'form_values': post or {},
        'selected_interests': selected,
        'expo_product_options': EXPO_PRODUCT_OPTIONS,
    }


def index(request):
    return render(request, 'index.html')


def mytrack(request):
    return render(request, 'mytrack.html')


def myroutes(request):
    return render(request, 'myroutes.html')


def kasistock(request):
    return render(request, 'kasistock.html')


def mywms(request):
    return render(request, 'mywms.html')


@xframe_options_sameorigin
def sloane_loop(request):
    # Embedded as a same-origin iframe on the product pages (?product=<id>),
    # so override Django's default X-Frame-Options: DENY.
    return render(request, '22onsloane.html')


@ensure_csrf_cookie
@require_GET
def expo_connect(request):
    src = normalize_src(request.GET.get('src'))
    thanks = request.GET.get('thanks') == '1'
    return render(request, 'expo_connect.html', _expo_context(src=src, thanks=thanks))


@require_GET
def expo_vcard(request):
    content = build_vcard()
    response = HttpResponse(content, content_type='text/vcard; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="mhare-consulting.vcf"'
    return response


@require_POST
def expo_submit(request):
    if is_rate_limited(request):
        msg = 'Too many submissions from this connection. Please wait a while or email sales@mhareconsulting.co.za.'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'error': msg}, status=429)
        src = normalize_src(request.POST.get('src'))
        return render(
            request,
            'expo_connect.html',
            _expo_context(src=src, form_error=msg, post=request.POST),
            status=429,
        )

    src = normalize_src(request.POST.get('src'))
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    lead, err = parse_lead(request.POST, request.META.get('HTTP_USER_AGENT', ''))
    if err == 'invalid':
        if is_ajax:
            return JsonResponse({'ok': True, 'redirect': f'/expo/?src={src}&thanks=1'})
        return redirect(f'/expo/?src={src}&thanks=1')

    if lead is None:
        if is_ajax:
            return JsonResponse({'ok': False, 'error': err}, status=400)
        return render(
            request,
            'expo_connect.html',
            _expo_context(src=src, form_error=err, post=request.POST),
            status=400,
        )

    ok, mail_err = send_lead_email(lead)
    if not ok:
        if is_ajax:
            return JsonResponse({'ok': False, 'error': mail_err}, status=503)
        return render(
            request,
            'expo_connect.html',
            _expo_context(src=src, form_error=mail_err, post=request.POST),
            status=503,
        )

    push_expo_lead_to_crm(lead)

    record_submission(request)

    if is_ajax:
        return JsonResponse({'ok': True, 'redirect': f'/expo/?src={src}&thanks=1'})

    return redirect(f'/expo/?src={src}&thanks=1')
