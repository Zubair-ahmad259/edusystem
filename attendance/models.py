
# attendance/models.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from datetime import date
from student.models import Student
from teachers.models import Teacher
from subject.models import Subject
from Academic.models import Batch, Semester, Section, Discipline


class AttendanceStatus(models.TextChoices):
    PRESENT = 'P', 'Present'
    ABSENT = 'A', 'Absent'

class Attendance(models.Model):
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='attendances',
        verbose_name="Student"
    )
    
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='attendances',
        verbose_name="Subject"
    )
    
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE,
        related_name='taken_attendances',
        verbose_name="Teacher",
        null=True,
        blank=True
    )
    
    date = models.DateField(
        default=date.today,
        verbose_name="Attendance Date"
    )
    
    time = models.TimeField(
        default=timezone.now,
        verbose_name="Attendance Time"
    )
    
    status = models.CharField(
        max_length=1,
        choices=AttendanceStatus.choices,
        default=AttendanceStatus.PRESENT,
        verbose_name="Attendance Status"
    )
    
    batch = models.ForeignKey(
        Batch,
        on_delete=models.CASCADE,
        related_name='attendances',
        verbose_name="Batch"
    )
    
    semester = models.ForeignKey(
        Semester,
        on_delete=models.CASCADE,
        related_name='attendances',
        verbose_name="Semester"
    )
    
    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        related_name='attendances',
        verbose_name="Section"
    )
    
    discipline = models.ForeignKey(
        Discipline,
        on_delete=models.CASCADE,
        related_name='attendances',
        verbose_name="Discipline"
    )
    
    remarks = models.TextField(
        blank=True,
        null=True,
        verbose_name="Remarks",
        help_text="Any additional notes about attendance"
    )
    
    marked_by = models.ForeignKey(
        Teacher,
        on_delete=models.SET_NULL,
        related_name='marked_attendances',
        verbose_name="Marked By",
        null=True,
        blank=True
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Attendance Record"
        verbose_name_plural = "Attendance Records"
        ordering = ['-date', '-time', 'student']
        unique_together = ['student', 'subject', 'date']
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['student', 'date']),
            models.Index(fields=['subject', 'date']),
            models.Index(fields=['batch', 'semester', 'section', 'date']),
        ]

    def __str__(self):
        return f"{self.student.student_id} - {self.subject.code} - {self.date} - {self.get_status_display()}"

    def save(self, *args, **kwargs):
        # Auto-fill batch, semester, section, discipline from student if not provided
        if not self.batch_id and self.student_id:
            self.batch = self.student.batch
        if not self.semester_id and self.student_id:
            self.semester = self.student.semester
        if not self.section_id and self.student_id:
            self.section = self.student.section
        if not self.discipline_id and self.student_id:
            self.discipline = self.student.discipline
            
        super().save(*args, **kwargs)

class DailyAttendanceSummary(models.Model):
    date = models.DateField(
        default=date.today,
        unique=True,
        verbose_name="Date"
    )
    
    batch = models.ForeignKey(
        Batch,
        on_delete=models.CASCADE,
        related_name='daily_summaries',
        verbose_name="Batch"
    )
    
    semester = models.ForeignKey(
        Semester,
        on_delete=models.CASCADE,
        related_name='daily_summaries',
        verbose_name="Semester"
    )
    
    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        related_name='daily_summaries',
        verbose_name="Section"
    )
    
    discipline = models.ForeignKey(
        Discipline,
        on_delete=models.CASCADE,
        related_name='daily_summaries',
        verbose_name="Discipline"
    )
    
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='daily_summaries',
        verbose_name="Subject"
    )
    
    total_students = models.IntegerField(
        default=0,
        verbose_name="Total Students"
    )
    
    present_count = models.IntegerField(
        default=0,
        verbose_name="Present Count"
    )
    
    absent_count = models.IntegerField(
        default=0,
        verbose_name="Absent Count"
    )
    
    attendance_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        verbose_name="Attendance Percentage",
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Daily Attendance Summary"
        verbose_name_plural = "Daily Attendance Summaries"
        ordering = ['-date', 'batch', 'semester', 'section']
        unique_together = ['date', 'batch', 'semester', 'section', 'subject']

    def __str__(self):
        return f"{self.date} - {self.batch.name} - {self.semester.number} - {self.section.name} - {self.attendance_percentage}%"

    def calculate_summary(self):
        """Calculate attendance summary for the day"""
        attendances = Attendance.objects.filter(
            date=self.date,
            batch=self.batch,
            semester=self.semester,
            section=self.section,
            subject=self.subject
        )
        
        self.total_students = attendances.count()
        self.present_count = attendances.filter(status=AttendanceStatus.PRESENT).count()
        self.absent_count = attendances.filter(status=AttendanceStatus.ABSENT).count()
        
        if self.total_students > 0:
            self.attendance_percentage = (self.present_count / self.total_students) * 100
        else:
            self.attendance_percentage = 0.00
            
        self.save()

class MonthlyAttendanceReport(models.Model):
    month = models.IntegerField(
        verbose_name="Month",
        validators=[MinValueValidator(1), MaxValueValidator(12)]
    )
    
    year = models.IntegerField(
        verbose_name="Year",
        validators=[MinValueValidator(2000), MaxValueValidator(2100)]
    )
    
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='monthly_reports',
        verbose_name="Student"
    )
    
    batch = models.ForeignKey(
        Batch,
        on_delete=models.CASCADE,
        related_name='monthly_reports',
        verbose_name="Batch"
    )
    
    semester = models.ForeignKey(
        Semester,
        on_delete=models.CASCADE,
        related_name='monthly_reports',
        verbose_name="Semester"
    )
    
    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        related_name='monthly_reports',
        verbose_name="Section"
    )
    
    total_days = models.IntegerField(
        default=0,
        verbose_name="Total Days"
    )
    
    present_days = models.IntegerField(
        default=0,
        verbose_name="Present Days"
    )
    
    absent_days = models.IntegerField(
        default=0,
        verbose_name="Absent Days"
    )
    
    attendance_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        verbose_name="Attendance Percentage"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Monthly Attendance Report"
        verbose_name_plural = "Monthly Attendance Reports"
        ordering = ['-year', '-month', 'student']
        unique_together = ['month', 'year', 'student']

    def __str__(self):
        return f"{self.student.student_id} - {self.month}/{self.year} - {self.attendance_percentage}%"

    def calculate_report(self):
        """Calculate monthly attendance report"""
        from django.db.models import Count
        
        attendances = Attendance.objects.filter(
            student=self.student,
            date__month=self.month,
            date__year=self.year
        )
        
        self.total_days = attendances.count()
        self.present_days = attendances.filter(status=AttendanceStatus.PRESENT).count()
        self.absent_days = attendances.filter(status=AttendanceStatus.ABSENT).count()
        
        if self.total_days > 0:
            self.attendance_percentage = (self.present_days / self.total_days) * 100
        else:
            self.attendance_percentage = 0.00
            
        self.save()

class AttendanceConfiguration(models.Model):
    """Configuration settings for attendance system"""
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Configuration Name"
    )
    
    minimum_attendance_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=75.00,
        verbose_name="Minimum Attendance Percentage",
        help_text="Minimum percentage required to be eligible for exams"
    )
    
    auto_calculate_summary = models.BooleanField(
        default=True,
        verbose_name="Auto Calculate Summary",
        help_text="Automatically calculate daily summaries"
    )
    
    send_notifications = models.BooleanField(
        default=True,
        verbose_name="Send Notifications",
        help_text="Send notifications for low attendance"
    )
    
    notification_threshold = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=80.00,
        verbose_name="Notification Threshold",
        help_text="Percentage below which notifications are sent"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Attendance Configuration"
        verbose_name_plural = "Attendance Configurations"

    def __str__(self):
        return self.name

class AttendanceNotification(models.Model):
    NOTIFICATION_TYPE_CHOICES = [
        ('LOW_ATTENDANCE', 'Low Attendance Alert'),
        ('ATTENDANCE_MARKED', 'Attendance Marked'),
        ('SYSTEM', 'System Notification'),
    ]
    
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='attendance_notifications',
        verbose_name="Student"
    )
    
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE,
        related_name='attendance_notifications',
        null=True,
        blank=True,
        verbose_name="Teacher"
    )
    
    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPE_CHOICES,
        verbose_name="Notification Type"
    )
    
    title = models.CharField(
        max_length=200,
        verbose_name="Notification Title"
    )
    
    message = models.TextField(
        verbose_name="Notification Message"
    )
    
    is_read = models.BooleanField(
        default=False,
        verbose_name="Is Read"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Attendance Notification"
        verbose_name_plural = "Attendance Notifications"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student.student_id} - {self.notification_type} - {self.created_at.date()}"
