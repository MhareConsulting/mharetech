from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST

from .expo import (
    build_vcard,
    is_rate_limited,
    normalize_src,
    parse_lead,
    record_submission,
    send_lead_email,
    source_context,
)


def index(request):
    return render(request, 'index.html')


def mytrack(request):
    return render(request, 'mytrack.html')


def myroutes(request):
    return render(request, 'myroutes.html')


@require_GET
def expo_connect(request):
    src = normalize_src(request.GET.get('src'))
    thanks = request.GET.get('thanks') == '1'
    ctx = {
        'src': src,
        'source': source_context(src),
        'thanks': thanks,
        'form_error': None,
        'form_values': {},
        'expo_sources': [
            ('mytrack', 'myTrack'),
            ('myroutes', 'myRoutes'),
            ('kasistock', 'KasiStock'),
            ('general', 'General / Mhare Tech'),
        ],
    }
    return render(request, 'expo_connect.html', ctx)


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
        return render(
            request,
            'expo_connect.html',
            {
                'src': normalize_src(request.POST.get('interest') or request.POST.get('src')),
                'source': source_context(normalize_src(request.POST.get('interest') or request.POST.get('src'))),
                'thanks': False,
                'form_error': msg,
                'expo_sources': [
                    ('mytrack', 'myTrack'),
                    ('myroutes', 'myRoutes'),
                    ('kasistock', 'KasiStock'),
                    ('general', 'General / Mhare Tech'),
                ],
                'form_values': request.POST,
            },
            status=429,
        )

    lead, err = parse_lead(request.POST, request.META.get('HTTP_USER_AGENT', ''))
    if err == 'invalid':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'ok': True})
        src = normalize_src(request.POST.get('interest') or request.POST.get('src'))
        return redirect(f'/expo/?src={src}&thanks=1')

    src = normalize_src(request.POST.get('interest') or request.POST.get('src'))
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if lead is None:
        if is_ajax:
            return JsonResponse({'ok': False, 'error': err}, status=400)
        return render(
            request,
            'expo_connect.html',
            {
                'src': src,
                'source': source_context(src),
                'thanks': False,
                'form_error': err,
                'expo_sources': [
                    ('mytrack', 'myTrack'),
                    ('myroutes', 'myRoutes'),
                    ('kasistock', 'KasiStock'),
                    ('general', 'General / Mhare Tech'),
                ],
                'form_values': request.POST,
            },
            status=400,
        )

    ok, mail_err = send_lead_email(lead)
    if not ok:
        if is_ajax:
            return JsonResponse({'ok': False, 'error': mail_err}, status=503)
        return render(
            request,
            'expo_connect.html',
            {
                'src': src,
                'source': source_context(src),
                'thanks': False,
                'form_error': mail_err,
                'expo_sources': [
                    ('mytrack', 'myTrack'),
                    ('myroutes', 'myRoutes'),
                    ('kasistock', 'KasiStock'),
                    ('general', 'General / Mhare Tech'),
                ],
                'form_values': request.POST,
            },
            status=503,
        )

    record_submission(request)

    if is_ajax:
        return JsonResponse({'ok': True, 'redirect': f'/expo/?src={src}&thanks=1'})

    return redirect(f'/expo/?src={src}&thanks=1')
