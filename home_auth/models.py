# home_auth/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.mail import send_mail
from django.conf import settings
from django.utils.crypto import get_random_string
from django.utils import timezone
from datetime import timedelta

class CustomUser(AbstractUser):
    username = models.CharField(max_length=100, unique=True)
    email = models.EmailField(max_length=255, unique=True, db_index=True)
    is_authorized = models.BooleanField(default=False)
    login_token = models.CharField(max_length=6, blank=True, null=True)
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    date_joined = models.DateTimeField(auto_now_add=True)

    # Fields for user roles
    is_student = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    is_teacher = models.BooleanField(default=False)
    
    # Password management fields
    password_change_deadline = models.DateTimeField(blank=True, null=True)  # Keep but won't be used
    password_generated = models.BooleanField(default=False)
    temp_password = models.CharField(max_length=100, blank=True, null=True)

    # Set related_name to prevent reverse relationship creation
    groups = models.ManyToManyField(
        'auth.Group',
        related_name="+",
        blank=True
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name="+",
        blank=True
    )

    def save(self, *args, **kwargs):
        # Generate and send password only when creating user
        if not self.pk and not self.password_generated:
            random_password = get_random_string(length=10)
            self.set_password(random_password)
            self.password_generated = True
            self.temp_password = random_password
            # Remove the deadline - set to None (no expiration)
            self.password_change_deadline = None
            super().save(*args, **kwargs)
            self.send_password_email(random_password)
        else:
            super().save(*args, **kwargs)

    def send_password_email(self, password):
        subject = "Your Account Password"
        message = (
            f"Dear {self.first_name or 'User'},\n\n"
            f"Welcome to the edusphare  System.\n\n"
            f"Your account has been successfully created.\n\n"
            f"Login Details:\n"
            f"Username: {self.username}\n"
            f"Temporary Password: {password}\n\n"
            f"Important Information:\n"
            f"• You can change your password anytime from your profile settings\n"
            f"• Keep your credentials secure\n"
            f"• Do not share your password with anyone\n\n"
            f"Login URL: http://127.0.0.1:8000/login/\n\n"
            f"Best regards,\n"
            f"edusphare Administration Team"
        )
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [self.email], fail_silently=False)

    def can_change_password(self):
        """Check if user can change password (always True now)"""
        return True  # Always allow password change

    def __str__(self):
        return self.username
# Define PasswordResetRequest AFTER CustomUser
class PasswordResetRequest(models.Model):
    # Use string reference 'CustomUser' instead of the class name
    user = models.ForeignKey(
        'CustomUser',  # Use string reference
        on_delete=models.PROTECT,  # PROTECT is best for important data
        related_name='password_reset_requests'
    )
    email = models.EmailField()
    token = models.CharField(
        max_length=32,
        default=get_random_string,
        editable=False,
        unique=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # Define token validity period (e.g., 1 hour)
    TOKEN_VALIDITY_PERIOD = timezone.timedelta(hours=1)

    def is_valid(self):
        """Check if reset token is still valid"""
        return timezone.now() <= self.created_at + self.TOKEN_VALIDITY_PERIOD

    def send_reset_email(self):
        """Send password reset email to user"""
        reset_link = f"http://localhost:8000/authentication/reset-password/{self.token}/"
        send_mail(
            'Password Reset Request',
            f'Click the following link to reset your password: {reset_link}\n\n'
            f'This link will expire in 1 hour.',
            settings.DEFAULT_FROM_EMAIL,
            [self.email],
            fail_silently=False,
        )
    
    def __str__(self):
        return f"Password reset for {self.user.username} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"