from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import date, datetime
import hashlib
from django.utils.crypto import get_random_string

from student.models import Student
from Academic.models import Batch, Semester, Section, Discipline
from subject.models import Subject
from teachers.models import Teacher

class ExamToken(models.Model):
    """
    Model representing examination tokens issued to students.
    """
    
    class TokenStatus(models.TextChoices):
        GENERATED = 'generated', 'Generated'
        PRINTED = 'printed', 'Printed'
        USED = 'used', 'Used'
        EXPIRED = 'expired', 'Expired'
        CANCELLED = 'cancelled', 'Cancelled'
        VERIFIED = 'verified', 'Verified'
        PENDING = 'pending', 'Pending Verification'

    # Core relationships
    student = models.ForeignKey(
        Student, 
        on_delete=models.CASCADE, 
        related_name='exam_tokens'
    )
    semester = models.ForeignKey(
        Semester, 
        on_delete=models.CASCADE
    )
    batch = models.ForeignKey(
        Batch, 
        on_delete=models.CASCADE
    )
    section = models.ForeignKey(
        Section, 
        on_delete=models.CASCADE
    )
    discipline = models.ForeignKey(
        Discipline, 
        on_delete=models.CASCADE
    )
    
    # Staff/Tracking fields
    issued_by = models.ForeignKey(
        Teacher,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='issued_tokens'
    )
    verified_by = models.ForeignKey(
        Teacher,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_tokens'
    )
    
    # Token identification
    token_number = models.CharField(
        max_length=50, 
        unique=True
    )
    issue_date = models.DateField(
        default=timezone.now
    )
    valid_until = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=TokenStatus.choices,
        default=TokenStatus.GENERATED,
        db_index=True
    )
    
    # Academic data
    eligible_subjects = models.ManyToManyField(
        Subject,
        related_name='tokens',
        blank=True
    )
    qr_code = models.ImageField(
        upload_to='tokens/qrcodes/%Y/%m/%d/',
        blank=True,
        null=True
    )
    
    # Eligibility verification data
    attendance_short = models.JSONField(
        default=dict, 
        blank=True
    )
    fee_defaulters = models.JSONField(
        default=dict, 
        blank=True
    )
    prerequisite_missing = models.JSONField(
        default=dict, 
        blank=True
    )
    
    # Verification metadata
    verification_date = models.DateTimeField(
        null=True,
        blank=True
    )
    verification_notes = models.TextField(
        blank=True
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-issue_date', 'student']
        unique_together = ['student', 'semester', 'issue_date']
        indexes = [
            models.Index(fields=['status', 'valid_until']),
            models.Index(fields=['student', 'status']),
        ]

    def __str__(self):
        return f"{self.token_number} - {self.student} ({self.status})"

    def clean(self):
        """Model validation"""
        if self.issue_date and self.valid_until:
            # Convert to date if they are datetime objects
            issue = self.issue_date if isinstance(self.issue_date, date) else self.issue_date.date()
            valid = self.valid_until if isinstance(self.valid_until, date) else self.valid_until.date()
            
            if issue > valid:
                raise ValidationError({
                    'valid_until': 'Valid until date must be after issue date'
                })

    def save(self, *args, **kwargs):
        # Auto-generate token number if not provided
        if not self.token_number:
            self.token_number = self.generate_token_number()
        
        # Auto-populate academic fields from student if not set
        if self.student:
            if not self.batch_id and self.student.batch:
                self.batch = self.student.batch
            if not self.semester_id and self.student.semester:
                self.semester = self.student.semester
            if not self.section_id and self.student.section:
                self.section = self.student.section
            if not self.discipline_id and self.student.discipline:
                self.discipline = self.student.discipline
        
        # Auto-update status to expired if past validity
        if self.valid_until:
            # Convert to date if it's a datetime
            valid_date = self.valid_until if isinstance(self.valid_until, date) else self.valid_until.date()
            today = date.today()
            
            if valid_date < today:
                if self.status not in [self.TokenStatus.EXPIRED, self.TokenStatus.USED, self.TokenStatus.CANCELLED]:
                    self.status = self.TokenStatus.EXPIRED
        
        super().save(*args, **kwargs)

    def generate_token_number(self):
        """Generate unique token number"""
        timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
        random_suffix = get_random_string(4).upper()
        
        # Create unique token using student ID and timestamp
        base_string = f"{self.student.student_id}-{timestamp}-{random_suffix}"
        token_hash = hashlib.md5(base_string.encode()).hexdigest()[:8].upper()
        
        return f"TKN-{self.student.student_id}-{timestamp}-{token_hash}"

    def verify_token(self, teacher, notes=""):
        """Verify the token and update status"""
        self.status = self.TokenStatus.VERIFIED
        self.verified_by = teacher
        self.verification_date = timezone.now()
        if notes:
            self.verification_notes = notes
        self.save(update_fields=['status', 'verified_by', 'verification_date', 'verification_notes'])

    def mark_as_used(self):
        """Mark token as used"""
        self.status = self.TokenStatus.USED
        self.save(update_fields=['status'])

    def cancel_token(self, teacher, reason=""):
        """Cancel the token"""
        self.status = self.TokenStatus.CANCELLED
        self.issued_by = teacher
        if reason:
            self.verification_notes = f"Cancelled: {reason}"
        self.save(update_fields=['status', 'issued_by', 'verification_notes'])

    @property
    def is_valid(self):
        """Check if token is currently valid"""
        if self.valid_until:
            # Convert to date if it's a datetime
            valid_date = self.valid_until if isinstance(self.valid_until, date) else self.valid_until.date()
            today = date.today()
            
            return (
                self.status == self.TokenStatus.VERIFIED and 
                valid_date >= today
            )
        return False

    @property
    def days_until_expiry(self):
        """Get days until token expires (returns integer, not string)"""
        if self.valid_until:
            try:
                # Convert to date if it's a datetime
                valid_date = self.valid_until if isinstance(self.valid_until, date) else self.valid_until.date()
                today = date.today()
                delta = valid_date - today
                return delta.days  # Returns integer
            except (TypeError, ValueError):
                return None
        return None
    
    def get_days_left_display(self):
        """Safe method to display days left (for templates)"""
        days = self.days_until_expiry
        if days is None:
            return "-"
        try:
            days = int(days)
            if days < 0:
                return "Expired"
            if days == 0:
                return "Today"
            if days < 7:
                return f"{days} days"
            return f"{days} days"
        except (TypeError, ValueError):
            return str(days)

    @classmethod
    def get_expired_tokens(cls):
        """Get all expired tokens"""
        today = date.today()
        return cls.objects.filter(
            valid_until__lt=today
        ).exclude(
            status__in=[cls.TokenStatus.EXPIRED, cls.TokenStatus.USED, cls.TokenStatus.CANCELLED]
        )