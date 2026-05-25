from django.test import Client, SimpleTestCase, override_settings
from django.urls import reverse

from .expo import build_vcard, normalize_src, parse_lead


class ExpoHelpersTests(SimpleTestCase):
    def test_normalize_src(self):
        self.assertEqual(normalize_src('mytrack'), 'mytrack')
        self.assertEqual(normalize_src('invalid'), 'general')

    def test_build_vcard(self):
        vcf = build_vcard()
        self.assertIn('BEGIN:VCARD', vcf)
        self.assertIn('sales@mhareconsulting.co.za', vcf)

    def test_parse_lead_requires_consent(self):
        lead, err = parse_lead(
            {'name': 'Jane', 'email': 'j@x.co', 'phone': '+27123456789', 'interest': 'mytrack'},
            'test',
        )
        self.assertIsNone(lead)
        self.assertIn('agree', err)

    def test_honeypot_silent(self):
        lead, err = parse_lead({'website': 'spam'}, 'test')
        self.assertIsNone(lead)
        self.assertEqual(err, 'invalid')


class ExpoViewsTests(SimpleTestCase):
    def setUp(self):
        self.client = Client()

    def test_expo_landing_ok(self):
        r = self.client.get(reverse('expo_connect'), {'src': 'mytrack'})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'myTrack')
        self.assertContains(r, 'Share your details')

    def test_expo_vcard_download(self):
        r = self.client.get(reverse('expo_vcard'))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'text/vcard; charset=utf-8')
        self.assertIn(b'BEGIN:VCARD', r.content)

    def test_expo_submit_validation(self):
        r = self.client.post(reverse('expo_submit'), {'name': 'x'})
        self.assertEqual(r.status_code, 400)

    @override_settings(EMAIL_HOST='')
    def test_expo_submit_no_smtp(self):
        r = self.client.post(
            reverse('expo_submit'),
            {
                'name': 'Jane Doe',
                'email': 'jane@example.com',
                'phone': '+27123456789',
                'interest': 'mytrack',
                'consent': 'on',
            },
        )
        self.assertEqual(r.status_code, 503)
        self.assertContains(r, 'not configured', status_code=503)
