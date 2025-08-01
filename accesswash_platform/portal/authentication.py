from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.hashers import check_password
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.utils import timezone
from datetime import timedelta
import jwt
from django.conf import settings
import secrets

from .models import Customer, CustomerSession


class CustomerAuthenticationBackend(BaseBackend):
    """Custom authentication backend for customers"""
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Authenticate customer with email or phone number
        """
        if not username or not password:
            return None
        
        try:
            # Try to find customer by email first
            if '@' in username:
                customer = Customer.objects.get(
                    email=username.lower(),
                    is_active=True,
                    is_deleted=False
                )
            else:
                # Try phone number
                customer = Customer.objects.get(
                    phone_number=username,
                    is_active=True,
                    is_deleted=False
                )
            
            # Check password
            if customer.check_password(password):
                # Update last login
                customer.last_login = timezone.now()
                customer.save(update_fields=['last_login'])
                return customer
                
        except Customer.DoesNotExist:
            pass
        
        return None
    
    def get_user(self, user_id):
        """Get customer by ID"""
        try:
            return Customer.objects.get(pk=user_id, is_active=True, is_deleted=False)
        except Customer.DoesNotExist:
            return None


class CustomerJWTAuthentication:
    """JWT token management for customers"""
    
    @staticmethod
    def generate_tokens(customer, request=None):
        """Generate access and refresh tokens for customer"""
        # Create session record
        session = CustomerSession.objects.create(
            customer=customer,
            session_token=secrets.token_urlsafe(32),
            refresh_token=secrets.token_urlsafe(32),
            ip_address=CustomerJWTAuthentication._get_client_ip(request),
            user_agent=CustomerJWTAuthentication._get_user_agent(request),
            expires_at=timezone.now() + timedelta(days=7)  # Refresh token expiry
        )
        
        # Generate JWT access token
        access_payload = {
            'customer_id': str(customer.id),
            'email': customer.email,
            'account_number': customer.account_number,
            'session_id': session.id,
            'exp': timezone.now() + timedelta(hours=2),  # Access token expiry
            'iat': timezone.now(),
            'type': 'access'
        }
        
        access_token = jwt.encode(
            access_payload,
            settings.SECRET_KEY,
            algorithm='HS256'
        )
        
        # Generate JWT refresh token
        refresh_payload = {
            'customer_id': str(customer.id),
            'session_id': session.id,
            'exp': timezone.now() + timedelta(days=7),
            'iat': timezone.now(),
            'type': 'refresh'
        }
        
        refresh_token = jwt.encode(
            refresh_payload,
            settings.SECRET_KEY,
            algorithm='HS256'
        )
        
        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'expires_in': 7200,  # 2 hours in seconds
            'session_id': session.id
        }
    
    @staticmethod
    def verify_token(token):
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=['HS256']
            )
            
            # Get customer
            customer = Customer.objects.get(
                id=payload['customer_id'],
                is_active=True,
                is_deleted=False
            )
            
            # Verify session is still active
            session = CustomerSession.objects.get(
                id=payload['session_id'],
                customer=customer,
                is_active=True
            )
            
            if not session.is_valid():
                return None
            
            # Update session last used
            session.last_used_at = timezone.now()
            session.save(update_fields=['last_used_at'])
            
            return customer
            
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, 
                Customer.DoesNotExist, CustomerSession.DoesNotExist):
            return None
    
    @staticmethod
    def refresh_access_token(refresh_token):
        """Generate new access token from refresh token"""
        try:
            payload = jwt.decode(
                refresh_token,
                settings.SECRET_KEY,
                algorithms=['HS256']
            )
            
            if payload.get('type') != 'refresh':
                return None
            
            # Get customer and session
            customer = Customer.objects.get(
                id=payload['customer_id'],
                is_active=True,
                is_deleted=False
            )
            
            session = CustomerSession.objects.get(
                id=payload['session_id'],
                customer=customer,
                is_active=True
            )
            
            if not session.is_valid():
                return None
            
            # Generate new access token
            access_payload = {
                'customer_id': str(customer.id),
                'email': customer.email,
                'account_number': customer.account_number,
                'session_id': session.id,
                'exp': timezone.now() + timedelta(hours=2),
                'iat': timezone.now(),
                'type': 'access'
            }
            
            access_token = jwt.encode(
                access_payload,
                settings.SECRET_KEY,
                algorithm='HS256'
            )
            
            # Update session
            session.extend_session()
            
            return {
                'access_token': access_token,
                'expires_in': 7200
            }
            
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError,
                Customer.DoesNotExist, CustomerSession.DoesNotExist):
            return None
    
    @staticmethod
    def logout_customer(customer, session_id=None):
        """Logout customer and invalidate sessions"""
        if session_id:
            # Logout specific session
            CustomerSession.objects.filter(
                customer=customer,
                id=session_id
            ).update(is_active=False)
        else:
            # Logout all sessions
            CustomerSession.objects.filter(
                customer=customer
            ).update(is_active=False)
    
    @staticmethod
    def _get_client_ip(request):
        """Get client IP address from request"""
        if not request:
            return None
        
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    @staticmethod
    def _get_user_agent(request):
        """Get user agent from request"""
        if not request:
            return ''
        return request.META.get('HTTP_USER_AGENT', '')


class CustomerPasswordResetService:
    """Handle password reset functionality for customers"""
    
    @staticmethod
    def request_password_reset(email):
        """Generate password reset token and send email"""
        try:
            customer = Customer.objects.get(
                email=email.lower(),
                is_active=True,
                is_deleted=False
            )
            
            # Create verification token
            from .models import CustomerVerification
            verification = CustomerVerification.objects.create(
                customer=customer,
                verification_type='password_reset',
                email=customer.email,
                expires_at=timezone.now() + timedelta(hours=24)
            )
            
            # Send password reset email
            from core.email_service import email_service
            
            # Build reset URL
            from django.db import connection
            tenant = getattr(connection, 'tenant', None)
            
            if tenant and hasattr(tenant, 'domains'):
                try:
                    primary_domain = tenant.domains.filter(is_primary=True, is_active=True).first()
                    if primary_domain:
                        protocol = 'https' if not settings.DEBUG else 'http'
                        port = '' if not settings.DEBUG else ':8000'
                        base_url = f"{protocol}://{primary_domain.domain}{port}"
                    else:
                        base_url = getattr(settings, 'PLATFORM_URL', 'https://api.accesswash.org')
                except:
                    base_url = getattr(settings, 'PLATFORM_URL', 'https://api.accesswash.org')
            else:
                base_url = getattr(settings, 'PLATFORM_URL', 'https://api.accesswash.org')
            
            reset_url = f"{base_url}/portal/auth/reset-password/{verification.token}/"
            
            # Email context
            context = {
                'customer': customer,
                'reset_url': reset_url,
                'email_subject': 'Reset your customer portal password'
            }
            
            success = email_service.send_email(
                template_name='portal/password_reset',
                context=context,
                to_emails=[customer.email]
            )
            
            return success
            
        except Customer.DoesNotExist:
            # Don't reveal if email exists for security
            return True
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Password reset error for {email}: {e}")
            return False
    
    @staticmethod
    def reset_password(token, new_password):
        """Reset password using verification token"""
        try:
            from .models import CustomerVerification
            
            verification = CustomerVerification.objects.get(
                token=token,
                verification_type='password_reset'
            )
            
            if not verification.is_valid():
                return False
            
            # Update password
            customer = verification.customer
            customer.set_password(new_password)
            customer.save(update_fields=['password_hash'])
            
            # Mark token as used
            verification.use_token()
            
            # Invalidate all existing sessions
            CustomerJWTAuthentication.logout_customer(customer)
            
            # Send confirmation email
            from core.email_service import email_service
            context = {
                'customer': customer,
                'email_subject': 'Your password has been changed'
            }
            
            email_service.send_email(
                template_name='portal/password_changed',
                context=context,
                to_emails=[customer.email]
            )
            
            return True
            
        except CustomerVerification.DoesNotExist:
            return False
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Password reset error for token {token}: {e}")
            return False


# Custom middleware for customer authentication in DRF
from rest_framework.authentication import BaseAuthentication
from rest_framework import exceptions


class CustomerTokenAuthentication(BaseAuthentication):
    """
    Custom DRF authentication class for customer JWT tokens
    """
    
    def authenticate(self, request):
        """
        Authenticate customer from JWT token in Authorization header
        """
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return None
        
        token = auth_header[7:]  # Remove 'Bearer ' prefix
        
        customer = CustomerJWTAuthentication.verify_token(token)
        
        if not customer:
            raise exceptions.AuthenticationFailed('Invalid or expired token')
        
        return (customer, token)
    
    def authenticate_header(self, request):
        """
        Return the authentication header to use for 401 responses
        """
        return 'Bearer'


# Email verification service
class CustomerEmailVerificationService:
    """Handle email verification for customers"""
    
    @staticmethod
    def send_verification_email(customer):
        """Send email verification to customer"""
        try:
            from .models import CustomerVerification
            
            # Create verification token
            verification = CustomerVerification.objects.create(
                customer=customer,
                verification_type='email',
                email=customer.email,
                expires_at=timezone.now() + timedelta(hours=48)
            )
            
            # Send verification email
            from core.email_service import email_service
            from django.db import connection
            
            # Build verification URL
            tenant = getattr(connection, 'tenant', None)
            
            if tenant and hasattr(tenant, 'domains'):
                try:
                    primary_domain = tenant.domains.filter(is_primary=True, is_active=True).first()
                    if primary_domain:
                        protocol = 'https' if not settings.DEBUG else 'http'
                        port = '' if not settings.DEBUG else ':8000'
                        base_url = f"{protocol}://{primary_domain.domain}{port}"
                    else:
                        base_url = getattr(settings, 'PLATFORM_URL', 'https://api.accesswash.org')
                except:
                    base_url = getattr(settings, 'PLATFORM_URL', 'https://api.accesswash.org')
            else:
                base_url = getattr(settings, 'PLATFORM_URL', 'https://api.accesswash.org')
            
            verify_url = f"{base_url}/portal/auth/verify-email/{verification.token}/"
            
            context = {
                'customer': customer,
                'verify_url': verify_url,
                'email_subject': 'Verify your email address'
            }
            
            success = email_service.send_email(
                template_name='portal/email_verification',
                context=context,
                to_emails=[customer.email]
            )
            
            return success
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Email verification error for {customer.email}: {e}")
            return False
    
    @staticmethod
    def verify_email(token):
        """Verify email using token"""
        try:
            from .models import CustomerVerification
            
            verification = CustomerVerification.objects.get(
                token=token,
                verification_type='email'
            )
            
            if not verification.is_valid():
                return False
            
            # Mark email as verified
            customer = verification.customer
            customer.email_verified = True
            customer.save(update_fields=['email_verified'])
            
            # Mark token as used
            verification.use_token()
            
            return True
            
        except CustomerVerification.DoesNotExist:
            return False
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Email verification error for token {token}: {e}")
            return False


# Phone verification service (placeholder for SMS integration)
class CustomerPhoneVerificationService:
    """Handle phone verification for customers"""
    
    @staticmethod
    def send_verification_sms(customer):
        """Send SMS verification code to customer"""
        # Placeholder for SMS integration (Twilio, Africa's Talking, etc.)
        try:
            from .models import CustomerVerification
            
            # Generate 6-digit code
            import random
            code = str(random.randint(100000, 999999))
            
            verification = CustomerVerification.objects.create(
                customer=customer,
                verification_type='phone',
                phone_number=customer.phone_number,
                token=code,  # Use code as token for phone verification
                expires_at=timezone.now() + timedelta(minutes=10)
            )
            
            # TODO: Integrate with SMS service
            # For now, just log the code
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"SMS verification code for {customer.phone_number}: {code}")
            
            return True
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"SMS verification error for {customer.phone_number}: {e}")
            return False
    
    @staticmethod
    def verify_phone(customer, code):
        """Verify phone using SMS code"""
        try:
            from .models import CustomerVerification
            
            verification = CustomerVerification.objects.get(
                customer=customer,
                verification_type='phone',
                token=code
            )
            
            if not verification.is_valid():
                return False
            
            # Mark phone as verified
            customer.phone_verified = True
            customer.save(update_fields=['phone_verified'])
            
            # Mark token as used
            verification.use_token()
            
            return True
            
        except CustomerVerification.DoesNotExist:
            return False
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Phone verification error for {customer.id}: {e}")
            return False