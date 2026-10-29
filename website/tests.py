from django.test import Client, SimpleTestCase, override_settings
from django.urls import reverse

from .expo import EVENT_NAME, build_vcard, normalize_src, parse_interests, parse_lead


class ExpoHelpersTests(SimpleTestCase):
    def test_normalize_src(self):
        self.assertEqual(normalize_src('mytrack'), 'mytrack')
        self.assertEqual(normalize_src('invalid'), 'general')

    def test_build_vcard(self):
        vcf = build_vcard()
        self.assertIn('BEGIN:VCARD', vcf)
        self.assertIn('sales@mhareconsulting.co.za', vcf)
        self.assertIn(EVENT_NAME, vcf)

    def test_parse_multiple_interests(self):
        lead, err = parse_lead(
            {
                'name': 'Jane Doe',
                'email': 'jane@example.com',
                'phone': '+27123456789',
                'interest': ['mytrack', 'myroutes'],
                'src': 'mytrack',
                'consent': 'on',
            },
            'test',
        )
        self.assertIsNone(err)
        self.assertEqual(lead.interests, ['mytrack', 'myroutes'])

    def test_parse_requires_interest(self):
        lead, err = parse_lead(
            {
                'name': 'Jane Doe',
                'email': 'jane@example.com',
                'phone': '+27123456789',
                'src': 'mytrack',
                'consent': 'on',
            },
            'test',
        )
        self.assertIsNone(lead)
        self.assertIn('select at least one', err)

    def test_parse_lead_requires_consent(self):
        lead, err = parse_lead(
            {'name': 'Jane', 'email': 'j@x.co', 'phone': '+27123456789', 'interest': 'mytrack'},
            'test',
        )
        self.assertIsNone(lead)
        self.assertIn('agree', err)

    def test_honeypot_silent(self):
        lead, err = parse_lead({'contact_hp': 'spam'}, 'test')
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
        self.assertContains(r, EVENT_NAME)
        self.assertContains(r, 'expo-header')

    def test_expo_form_post_with_csrf(self):
        r = self.client.get(reverse('expo_connect'))
        token = r.cookies['csrftoken'].value
        r2 = self.client.post(
            reverse('expo_submit'),
            {
                'name': 'Jane Doe',
                'email': 'jane@example.com',
                'phone': '+27123456789',
                'interest': ['mytrack'],
                'src': 'mytrack',
                'consent': 'on',
            },
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertNotEqual(r2.status_code, 403)
        self.assertIn(r2.status_code, (302, 503))

    def test_expo_vcard_download(self):
        r = self.client.get(reverse('expo_vcard'))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'text/vcard; charset=utf-8')
        self.assertIn(b'BEGIN:VCARD', r.content)

    def test_expo_submit_validation(self):
        r = self.client.post(reverse('expo_submit'), {'name': 'x'})
        self.assertEqual(r.status_code, 400)

    def test_website_autofill_does_not_trigger_honeypot(self):
        lead, err = parse_lead(
            {
                'name': 'Jane Doe',
                'email': 'jane@example.com',
                'phone': '+27123456789',
                'interest': ['mytrack'],
                'website': 'https://company.co.za',
                'consent': 'on',
            },
            'test',
        )
        self.assertIsNone(err)
        self.assertEqual(lead.name, 'Jane Doe')

    def test_expo_ajax_returns_json_error_when_no_smtp(self):
        r = self.client.get(reverse('expo_connect'))
        csrf = r.cookies['csrftoken'].value
        r2 = self.client.post(
            reverse('expo_submit'),
            {
                'name': 'Jane Doe',
                'email': 'jane@example.com',
                'phone': '+27123456789',
                'interest': ['mytrack'],
                'src': 'mytrack',
                'consent': 'on',
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            HTTP_X_CSRFTOKEN=csrf,
        )
        self.assertEqual(r2.status_code, 503)
        data = r2.json()
        self.assertFalse(data['ok'])
        self.assertIn('not configured', data['error'])

    @override_settings(EMAIL_HOST='')
    def test_expo_submit_no_smtp(self):
        r = self.client.post(
            reverse('expo_submit'),
            {
                'name': 'Jane Doe',
                'email': 'jane@example.com',
                'phone': '+27123456789',
                'interest': ['mytrack'],
                'src': 'mytrack',
                'consent': 'on',
            },
        )
        self.assertEqual(r.status_code, 503)
        self.assertContains(r, 'not configured', status_code=503)


# Pages that use the site layout ask the manifest storage for hashed file names, which only exist after collectstatic.
PLAIN_STATIC = override_settings(STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage')


@PLAIN_STATIC
class PlansPageTests(SimpleTestCase):
    def setUp(self):
        self.response = Client().get(reverse('plans'))

    def test_page_opens_in_the_site_layout(self):
        self.assertEqual(self.response.status_code, 200)
        self.assertContains(self.response, 'Plans that <em>fit</em> your fleet', html=False)
        self.assertContains(self.response, 'css/plans.css')
        self.assertContains(self.response, 'js/plans.js')
        self.assertContains(self.response, 'nav-links')            # the site's own navigation

    def test_every_product_and_tier_is_shown(self):
        for product in ('Fuel Savings', 'Tracking', 'Driver App', 'Car Guard', 'People &amp; Assets'):
            self.assertContains(self.response, product)
        for tier in ('Card', 'Verified', 'Essential', 'Standard', 'Advanced', 'Clock-in', 'Safety', 'Basic', 'Plus'):
            self.assertContains(self.response, f'<h3>{tier}</h3>')

    def test_each_product_has_a_custom_card_and_a_builder(self):
        self.assertContains(self.response, 'data-custom', count=5)
        for key in ('driver.sos', 'tracking.reports', 'guard.alarms', 'fuel.savings', 'people.depots'):
            self.assertContains(self.response, f'data-fn="{key}"')

    def test_the_rules_the_script_needs_are_in_the_page(self):
        self.assertContains(self.response, 'data-fn="fuel.savings" data-label="Savings finder" data-requires="fuel.directory" data-requires-any="fuel.card fuel.verify"')
        self.assertContains(self.response, 'data-keys="driver.clockin driver.inspections driver.sos"')

    def test_the_request_goes_to_sales_and_nothing_is_stored(self):
        self.assertContains(self.response, 'data-email="sales@mhareconsulting.co.za"')
        self.assertNotContains(self.response, '<form')

    def test_no_prices_are_invented(self):
        self.assertContains(self.response, 'On request')
        self.assertNotContains(self.response, 'per month')

    def test_the_site_navigation_links_to_it(self):
        home = Client().get(reverse('mytrack')).content.decode()
        self.assertIn(reverse('plans'), home)


class PlansSnapshotTests(SimpleTestCase):
    """website/plans.json is an export from myTrack: guard against a broken or stale-shaped file."""

    def setUp(self):
        import json
        from pathlib import Path
        self.data = json.loads((Path(__file__).parent / 'plans.json').read_text(encoding='utf-8'))

    def test_shape(self):
        self.assertEqual([p['key'] for p in self.data['products']],
                         ['fuel_savings', 'tracking', 'driver_app', 'car_guard', 'people'])
        for p in self.data['products']:
            self.assertTrue({'key', 'label', 'intro', 'cards', 'functions', 'rows'} <= set(p))
            keys = {f['key'] for f in p['functions']}
            for c in p['cards']:
                self.assertTrue({'key', 'name', 'summary', 'price', 'recommended', 'keys', 'included'} <= set(c))
                self.assertTrue(set(c['keys']) <= keys, c['key'])          # a tier only grants functions of its product
            for f in p['functions']:
                for need in (f['requires'] + ' ' + f['requires_any']).split():
                    self.assertIn(need, keys, f['key'])
            for r in p['rows']:
                self.assertEqual(len(r['in']), len(p['cards']))

    def test_every_function_a_card_shows_exists(self):
        for p in self.data['products']:
            keys = {f['key'] for f in p['functions']}
            for c in p['cards']:
                self.assertTrue({f['key'] for f in c['included']} <= keys)
