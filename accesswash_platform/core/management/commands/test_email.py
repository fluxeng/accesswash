"""
Management command to test email functionality
Usage: python manage.py test_email your-email@example.com
"""

from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from django_tenants.utils import schema_context
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Test email functionality for AccessWash platform'

    def add_arguments(self, parser):
        parser.add_argument(
            'email',
            type=str,
            help='Email address to send test email to'
        )
        parser.add_argument(
            '--schema',
            type=str,
            default='public',
            help='Schema to test email from (default: public)'
        )

    def handle(self, *args, **options):
        email = options['email']
        schema = options['schema']

        self.stdout.write(f"Testing email functionality for: {email}")
        self.stdout.write(f"Schema: {schema}")
        self.stdout.write("-" * 50)

        # Test with specified schema context
        with schema_context(schema):
            self.test_django_email(email)
            self.test_email_service(email)

    def test_django_email(self, email):
        """Test basic Django email functionality"""
        self.stdout.write("Testing Django email...")
        
        try:
            result = send_mail(
                subject='AccessWash Platform - Django Email Test',
                message='This is a test email sent using Django\'s send_mail function.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            
            if result:
                self.stdout.write(
                    self.style.SUCCESS(f"✅ Django email sent successfully to {email}")
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f"❌ Django email failed to send to {email}")
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Django email error: {str(e)}")
            )

    def test_email_service(self, email):
        """Test EmailService functionality"""
        self.stdout.write("Testing EmailService...")
        
        try:
            from core.email_service import email_service
            success = email_service.send_test_email(email)
            
            if success:
                self.stdout.write(
                    self.style.SUCCESS(f"✅ EmailService test email sent successfully to {email}")
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f"❌ EmailService test email failed to send to {email}")
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ EmailService error: {str(e)}")
            )