"""Send a test email using the same SMTP settings as the expo lead form."""

from pathlib import Path

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Test expo SMTP configuration (same as /expo/ lead emails).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--to',
            default=getattr(settings, 'EXPO_LEAD_TO', 'sales@mhareconsulting.co.za'),
            help='Recipient for the test message.',
        )

    def handle(self, *args, **options):
        env_path = Path(settings.BASE_DIR) / '.env'
        host = getattr(settings, 'EMAIL_HOST', '')
        if not host:
            hint = f'No .env at {env_path}' if not env_path.is_file() else (
                f'.env exists at {env_path} but SMTP_HOST is missing or empty. '
                'Add SMTP_HOST, SMTP_PORT, SMTP_USE_SSL, SMTP_USER, SMTP_PASSWORD.'
            )
            raise CommandError(hint)

        to_addr = options['to']
        from_addr = getattr(settings, 'EXPO_LEAD_FROM', settings.DEFAULT_FROM_EMAIL)

        self.stdout.write(f'SMTP host: {host}:{settings.EMAIL_PORT}')
        self.stdout.write(f'SSL={settings.EMAIL_USE_SSL} TLS={settings.EMAIL_USE_TLS}')
        self.stdout.write(f'User: {settings.EMAIL_HOST_USER}')
        self.stdout.write(f'From: {from_addr}')
        self.stdout.write(f'To: {to_addr}')
        self.stdout.write('Sending test message…')

        try:
            send_mail(
                subject='[Mhare Tech] Expo SMTP test',
                message=(
                    'This is a test email from manage.py test_expo_smtp.\n'
                    'If you received this, expo lead emails should work.'
                ),
                from_email=from_addr,
                recipient_list=[to_addr],
                fail_silently=False,
            )
        except Exception as exc:
            raise CommandError(f'SMTP failed: {exc}') from exc

        self.stdout.write(self.style.SUCCESS(f'Sent OK to {to_addr}'))
