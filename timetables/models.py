# timetables/models.py

from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import time, timedelta
from teachers.models import Teacher
from Academic.models import Batch, Semester, Section, Discipline
from subject.models import Subject, SubjectAssign

class TimeSlot(models.Model):
    """
    Defines available time slots for classes
    From Monday 9:00 AM to 4:00 PM, Friday 9:00 AM to 2:00 PM
    Saturday and Sunday are OFF
    """
    DAY_CHOICES = [
        ('Monday', 'Monday'),
        ('Tuesday', 'Tuesday'),
        ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'),
        ('Friday', 'Friday'),
    ]
    
    day = models.CharField(max_length=10, choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    duration_minutes = models.PositiveIntegerField(help_text="Duration in minutes", default=60)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['day', 'start_time']
        unique_together = ['day', 'start_time', 'end_time']
        verbose_name = "Time Slot"
        verbose_name_plural = "Time Slots"
    
    def __str__(self):
        return f"{self.day} - {self.start_time.strftime('%I:%M %p')} to {self.end_time.strftime('%I:%M %p')}"
    
    def clean(self):
        if self.start_time >= self.end_time:
            raise ValidationError("Start time must be before end time")
        
        # Validate based on day constraints
        if self.day == 'Friday':
            if self.start_time < time(9, 0):
                raise ValidationError("Friday classes cannot start before 9:00 AM")
            if self.end_time > time(14, 0):
                raise ValidationError("Friday classes cannot go beyond 2:00 PM")
        else:  # Monday to Thursday
            if self.start_time < time(9, 0):
                raise ValidationError(f"{self.day} classes cannot start before 9:00 AM")
            if self.end_time > time(16, 0):
                raise ValidationError(f"{self.day} classes cannot go beyond 4:00 PM")
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)



class Classroom(models.Model):
    """
    Classroom information with discipline, batch, semester, and section associations
    """
    room_number = models.CharField(max_length=20, unique=True)
    building = models.CharField(max_length=100, default="Main Building")
    capacity = models.PositiveIntegerField(default=30)
    has_projector = models.BooleanField(default=False)
    has_smartboard = models.BooleanField(default=False)
    is_lab = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    # Add these fields for filtering
    discipline = models.ForeignKey(
        'Academic.Discipline',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="classrooms",
        help_text="Department/Discipline that primarily uses this classroom"
    )
    batch = models.ForeignKey(
        'Academic.Batch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="classrooms",
        help_text="Batch that primarily uses this classroom"
    )
    semester = models.ForeignKey(
        'Academic.Semester',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="classrooms",
        help_text="Semester that primarily uses this classroom"
    )
    section = models.ForeignKey(
        'Academic.Section',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="classrooms",
        help_text="Section that primarily uses this classroom"
    )
    
    class Meta:
        ordering = ['building', 'room_number']
        verbose_name = "Classroom"
        verbose_name_plural = "Classrooms"
    
    def __str__(self):
        base = f"{self.building} - Room {self.room_number}"
        if self.section:
            base += f" ({self.section.name})"
        elif self.batch:
            base += f" ({self.batch.name})"
        return base
    
    @property
    def facilities(self):
        facilities = []
        if self.has_projector:
            facilities.append("Projector")
        if self.has_smartboard:
            facilities.append("Smart Board")
        if self.is_lab:
            facilities.append("Computer Lab")
        return ", ".join(facilities) if facilities else "Basic"
    
    @property
    def classroom_info(self):
        """Return detailed classroom information"""
        info = []
        if self.discipline:
            info.append(f"Dept: {self.discipline}")
        if self.batch:
            info.append(f"Batch: {self.batch.name}")
        if self.semester:
            info.append(f"Sem: {self.semester.number}")
        if self.section:
            info.append(f"Section: {self.section.name}")
        return " | ".join(info) if info else "General Purpose"

class TeacherAvailability(models.Model):
    """
    Defines when a teacher is available/unavailable for classes
    Only for Monday to Friday
    """
    DAY_CHOICES = [
        ('Monday', 'Monday'),
        ('Tuesday', 'Tuesday'),
        ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'),
        ('Friday', 'Friday'),
    ]
    
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE,
        related_name="availabilities"
    )
    day = models.CharField(max_length=10, choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True)
    reason = models.CharField(max_length=255, blank=True, help_text="Reason if unavailable")
    
    class Meta:
        verbose_name = "Teacher Availability"
        verbose_name_plural = "Teacher Availabilities"
        unique_together = ['teacher', 'day', 'start_time', 'end_time']
    
    def __str__(self):
        status = "Available" if self.is_available else "Unavailable"
        return f"{self.teacher} - {self.day} {self.start_time.strftime('%I:%M %p')} to {self.end_time.strftime('%I:%M %p')} ({status})"
    
    def clean(self):
        if self.start_time >= self.end_time:
            raise ValidationError("Start time must be before end time")
        
        # Validate based on day constraints
        if self.day == 'Friday':
            if self.start_time < time(9, 0):
                raise ValidationError("Friday availability cannot start before 9:00 AM")
            if self.end_time > time(14, 0):
                raise ValidationError("Friday availability cannot go beyond 2:00 PM")
        else:
            if self.start_time < time(9, 0):
                raise ValidationError(f"{self.day} availability cannot start before 9:00 AM")
            if self.end_time > time(16, 0):
                raise ValidationError(f"{self.day} availability cannot go beyond 4:00 PM")


class TimetableEntry(models.Model):
    """
    Main timetable entry for scheduled classes
    """
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE,
        related_name="timetable_entries"
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="timetable_entries"
    )
    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        related_name="timetable_entries"
    )
    batch = models.ForeignKey(
        Batch,
        on_delete=models.CASCADE,
        related_name="timetable_entries"
    )
    semester = models.ForeignKey(
        Semester,
        on_delete=models.CASCADE,
        related_name="timetable_entries"
    )
    time_slot = models.ForeignKey(
        TimeSlot,
        on_delete=models.CASCADE,
        related_name="timetable_entries"
    )
    classroom = models.ForeignKey(
        Classroom,
        on_delete=models.CASCADE,
        related_name="timetable_entries"
    )
    
    # Optional: For exam timetables
    is_exam = models.BooleanField(default=False)
    exam_type = models.CharField(max_length=50, blank=True, choices=[
        ('midterm', 'Midterm Exam'),
        ('final', 'Final Exam'),
        ('quiz', 'Quiz'),
        ('other', 'Other'),
    ])
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Timetable Entry"
        verbose_name_plural = "Timetable Entries"
        ordering = ['time_slot__day', 'time_slot__start_time']
        unique_together = [
            ['section', 'time_slot'],  # One section can't have two classes at same time
            ['teacher', 'time_slot'],  # One teacher can't teach two classes at same time
            ['classroom', 'time_slot'],  # One classroom can't have two classes at same time
        ]
    
    def __str__(self):
        return f"{self.subject.code} - {self.section} - {self.time_slot.day} {self.time_slot.start_time.strftime('%I:%M %p')}"
    
    def clean(self):
        # Check if teacher is available during this time
        teacher_availability = TeacherAvailability.objects.filter(
            teacher=self.teacher,
            day=self.time_slot.day,
            start_time__lte=self.time_slot.start_time,
            end_time__gte=self.time_slot.end_time
        )
        
        if teacher_availability.exists() and not teacher_availability.first().is_available:
            raise ValidationError(f"Teacher {self.teacher} is not available during this time slot")
        
        # Check if teacher is not overworked (max 8 hours per day)
        daily_hours = TimetableEntry.objects.filter(
            teacher=self.teacher,
            time_slot__day=self.time_slot.day,
            is_active=True
        ).exclude(id=self.id)
        
        total_minutes = 0
        for entry in daily_hours:
            duration = (entry.time_slot.end_time.hour * 60 + entry.time_slot.end_time.minute) - \
                      (entry.time_slot.start_time.hour * 60 + entry.time_slot.start_time.minute)
            total_minutes += duration
        
        current_duration = (self.time_slot.end_time.hour * 60 + self.time_slot.end_time.minute) - \
                          (self.time_slot.start_time.hour * 60 + self.time_slot.start_time.minute)
        
        if total_minutes + current_duration > 8 * 60:  # 8 hours max
            raise ValidationError(f"Teacher {self.teacher} already has 8 hours of classes on {self.time_slot.day}")
        
        # Check if section already has a class at this time (handled by unique_together)
        # Check if teacher already has a class at this time (handled by unique_together)
        # Check if classroom is available at this time (handled by unique_together)
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class TimetableGenerationRequest(models.Model):
    """
    Track automatic timetable generation requests
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE,
        related_name="timetable_generations",
        null=True,
        blank=True
    )
    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        related_name="timetable_generations",
        null=True,
        blank=True
    )
    batch = models.ForeignKey(
        Batch,
        on_delete=models.CASCADE,
        related_name="timetable_generations"
    )
    semester = models.ForeignKey(
        Semester,
        on_delete=models.CASCADE,
        related_name="timetable_generations"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Timetable Generation Request"
        verbose_name_plural = "Timetable Generation Requests"
        ordering = ['-created_at']
    
    def __str__(self):
        if self.teacher:
            return f"Timetable for {self.teacher} - {self.batch} Semester {self.semester}"
        elif self.section:
            return f"Timetable for {self.section} - {self.batch} Semester {self.semester}"
        return f"Timetable Request - {self.created_at}"


class ExamTimetable(models.Model):
    """
    Separate model for exam timetables with additional exam-specific fields
    """
    EXAM_TYPE_CHOICES = [
        ('midterm', 'Midterm Exam'),
        ('final', 'Final Exam'),
        ('quiz', 'Quiz'),
        ('practical', 'Practical Exam'),
        ('viva', 'Viva Voce'),
    ]
    
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE,
        related_name="exam_timetables"
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="exam_timetables"
    )
    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        related_name="exam_timetables"
    )
    batch = models.ForeignKey(
        Batch,
        on_delete=models.CASCADE,
        related_name="exam_timetables"
    )
    semester = models.ForeignKey(
        Semester,
        on_delete=models.CASCADE,
        related_name="exam_timetables"
    )
    exam_type = models.CharField(max_length=20, choices=EXAM_TYPE_CHOICES)
    exam_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    classroom = models.ForeignKey(
        Classroom,
        on_delete=models.CASCADE,
        related_name="exam_timetables"
    )
    total_marks = models.PositiveIntegerField(default=100)
    duration_minutes = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Exam Timetable"
        verbose_name_plural = "Exam Timetables"
        ordering = ['exam_date', 'start_time']
        unique_together = [
            ['section', 'exam_date', 'start_time'],  # One section can't have two exams at same time
            ['teacher', 'exam_date', 'start_time'],  # One teacher can't conduct two exams at same time
            ['classroom', 'exam_date', 'start_time'],  # One classroom can't host two exams at same time
        ]
    
    def __str__(self):
        return f"{self.subject.code} - {self.section} - {self.exam_date} ({self.exam_type})"
    
    def clean(self):
        # Validate exam time constraints
        if self.start_time >= self.end_time:
            raise ValidationError("Start time must be before end time")
        
        # Validate based on exam date day
        exam_day = self.exam_date.strftime('%A')
        
        if exam_day in ['Saturday', 'Sunday']:
            raise ValidationError("Exams cannot be scheduled on Saturday or Sunday")
        
        if exam_day == 'Friday':
            if self.start_time < time(9, 0) or self.end_time > time(14, 0):
                raise ValidationError("Friday exams must be between 9:00 AM and 2:00 PM")
        else:  # Monday to Thursday
            if self.start_time < time(9, 0) or self.end_time > time(16, 0):
                raise ValidationError(f"{exam_day} exams must be between 9:00 AM and 4:00 PM")





# timetables/models.py - Complete Laboratory model

class Laboratory(models.Model):
    """
    Computer Laboratory model with full details for all batches, sections, and semesters
    """
    # Basic Information
    lab_code = models.CharField(max_length=20, unique=True, help_text="e.g., LAB-101, CS-LAB-1")
    lab_name = models.CharField(max_length=100, help_text="e.g., Computer Science Lab 1")
    building = models.CharField(max_length=100, default="Main Building")
    floor = models.CharField(max_length=10, blank=True, help_text="e.g., Ground Floor, 1st Floor")
    capacity = models.PositiveIntegerField(default=30, help_text="Number of students that can sit")
    
    # Computer Details
    computer_count = models.PositiveIntegerField(default=0, help_text="Number of computers")
    computer_config = models.TextField(blank=True, help_text="e.g., Intel i5, 8GB RAM, 512GB SSD")
    operating_system = models.CharField(max_length=50, blank=True, help_text="e.g., Windows 11, Ubuntu 22.04")
    
    # Software
    software_installed = models.TextField(blank=True, help_text="List of installed software (one per line)")
    
    # Facilities
    has_projector = models.BooleanField(default=False)
    has_smartboard = models.BooleanField(default=False)
    has_ac = models.BooleanField(default=False, help_text="Air Conditioning")
    has_generator = models.BooleanField(default=False, help_text="Generator Backup")
    has_wifi = models.BooleanField(default=False, help_text="WiFi Available")
    has_printer = models.BooleanField(default=False, help_text="Printer Available")
    has_whiteboard = models.BooleanField(default=False, help_text="Whiteboard Available")
    
    # Network Details
    internet_speed = models.CharField(max_length=50, blank=True, help_text="e.g., 100 Mbps")
    network_type = models.CharField(max_length=50, blank=True, help_text="e.g., LAN, Fiber Optic")
    
    # Association with ALL batches, sections, semesters (Many-to-Many relationships)
    batches = models.ManyToManyField(
        'Academic.Batch',
        blank=True,
        related_name="laboratories",
        help_text="Batches that can use this lab"
    )
    sections = models.ManyToManyField(
        'Academic.Section',
        blank=True,
        related_name="laboratories",
        help_text="Sections that can use this lab"
    )
    semesters = models.ManyToManyField(
        'Academic.Semester',
        blank=True,
        related_name="laboratories",
        help_text="Semesters that can use this lab"
    )
    disciplines = models.ManyToManyField(
        'Academic.Discipline',
        blank=True,
        related_name="laboratories",
        help_text="Disciplines that can use this lab"
    )
    
    # Direct associations (for primary assignment)
    primary_batch = models.ForeignKey(
        'Academic.Batch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="primary_laboratory",
        help_text="Primary batch for this lab"
    )
    primary_section = models.ForeignKey(
        'Academic.Section',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="primary_laboratory",
        help_text="Primary section for this lab"
    )
    primary_semester = models.ForeignKey(
        'Academic.Semester',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="primary_laboratory",
        help_text="Primary semester for this lab"
    )
    primary_discipline = models.ForeignKey(
        'Academic.Discipline',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="primary_laboratory",
        help_text="Primary discipline for this lab"
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    last_maintenance = models.DateField(null=True, blank=True)
    next_maintenance = models.DateField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['lab_code']
        verbose_name = "Laboratory"
        verbose_name_plural = "Laboratories"
    
    def __str__(self):
        return f"{self.lab_code} - {self.lab_name}"
    
    @property
    def facilities_list(self):
        """Return list of facilities available"""
        facilities = []
        if self.has_projector:
            facilities.append("📽️ Projector")
        if self.has_smartboard:
            facilities.append("🖥️ Smart Board")
        if self.has_ac:
            facilities.append("❄️ AC")
        if self.has_generator:
            facilities.append("⚡ Generator")
        if self.has_wifi:
            facilities.append("📶 WiFi")
        if self.has_printer:
            facilities.append("🖨️ Printer")
        if self.has_whiteboard:
            facilities.append("📝 Whiteboard")
        return facilities
    
    @property
    def software_list(self):
        """Return list of installed software"""
        if self.software_installed:
            return [s.strip() for s in self.software_installed.split('\n') if s.strip()]
        return []
    
    @property
    def assigned_batches_display(self):
        """Display all assigned batches"""
        return ", ".join([b.name for b in self.batches.all()]) or "All Batches"
    
    @property
    def assigned_sections_display(self):
        """Display all assigned sections"""
        return ", ".join([s.name for s in self.sections.all()]) or "All Sections"
    
    @property
    def assigned_semesters_display(self):
        """Display all assigned semesters"""
        return ", ".join([f"Sem {s.number}" for s in self.semesters.all()]) or "All Semesters"






