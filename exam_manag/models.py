from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.utils import timezone

from student.models import Student
from Academic.models import Batch, Semester, Section, Discipline
from subject.models import Subject
from teachers.models import Teacher
from home_auth.models import CustomUser


class Exam(models.Model):
    EXAM_TYPE_CHOICES = [
        ('mid_term', 'Mid Term'),
        ('final', 'Final'),
        ('quiz', 'Quiz'),
        ('assignment', 'Assignment'),
        ('lab', 'Lab'),
        ('attendance', 'Attendance'),
    ]

    exam_type = models.CharField(max_length=20, choices=EXAM_TYPE_CHOICES)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='exams')
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='exams')
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='exams')
    
    exam_date = models.DateField(default=timezone.now)
    
    total_marks = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        default=100.00
    )
    
    passing_marks = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        default=40.00
    )
    
    is_published = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('exam_type', 'subject', 'section')
        ordering = ['-exam_date']

    def __str__(self):
        return f"{self.subject.code} - {self.get_exam_type_display()} - {self.section.name}"

    def save(self, *args, **kwargs):
        if self.passing_marks == 0 or not self.passing_marks:
            self.passing_marks = self.total_marks * Decimal('0.40')
        if self.is_published and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    def get_students(self):
        return Student.objects.filter(section=self.section).order_by('student_id')

    @property
    def student_count(self):
        return self.get_students().count()

    @property
    def result_count(self):
        return self.results.count()


class ExamResult(models.Model):
    GRADE_CHOICES = [
        ('A+', 'A+'),
        ('A', 'A'),
        ('B+', 'B+'),
        ('B', 'B'),
        ('C+', 'C+'),
        ('C', 'C'),
        ('D', 'D'),
        ('F', 'F'),
    ]

    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='results')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='exam_results')
    
    marks_obtained = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        null=True,
        blank=True
    )
    
    is_absent = models.BooleanField(default=False)
    remarks = models.TextField(blank=True)
    
    entered_by = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True)
    entered_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('exam', 'student')
        ordering = ['student__student_id']

    def __str__(self):
        return f"{self.student.student_id} - {self.exam.exam_type} - {self.marks_obtained or 'Absent'}"

    @property
    def percentage(self):
        if self.marks_obtained and self.exam.total_marks > 0:
            return (self.marks_obtained / self.exam.total_marks) * 100
        return Decimal('0.00')

    @property
    def grade(self):
        pct = float(self.percentage)
        if pct >= 90:
            return 'A+'
        elif pct >= 80:
            return 'A'
        elif pct >= 70:
            return 'B+'
        elif pct >= 60:
            return 'B'
        elif pct >= 50:
            return 'C+'
        elif pct >= 40:
            return 'C'
        elif pct >= 33:
            return 'D'
        else:
            return 'F'

    @property
    def grade_point(self):
        grade = self.grade
        grade_points = {
            'A+': Decimal('4.00'),
            'A': Decimal('4.00'),
            'B+': Decimal('3.50'),
            'B': Decimal('3.00'),
            'C+': Decimal('2.50'),
            'C': Decimal('2.00'),
            'D': Decimal('1.50'),
            'F': Decimal('0.00'),
        }
        return grade_points.get(grade, Decimal('0.00'))


class StudentSubjectResult(models.Model):
    """
    Student Subject Result - ONE ROW PER SUBJECT PER STUDENT
    Useful for detailed subject-wise analysis
    """
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='subject_results')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, null=True)
    section = models.ForeignKey(Section, on_delete=models.CASCADE, null=True)
    
    # Individual component marks
    mid_term_marks = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    final_marks = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    quiz_marks = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    assignment_marks = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    lab_marks = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    attendance_marks = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    
    # Calculated fields
    total_marks = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    grade = models.CharField(max_length=2, choices=ExamResult.GRADE_CHOICES, blank=True, null=True)
    grade_point = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal('0.00'))
    is_passed = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('student', 'subject')
        ordering = ['subject__code']

    def __str__(self):
        return f"{self.student.student_id} - {self.subject.code} - {self.grade or 'No Grade'}"

    def save(self, *args, **kwargs):
        # Calculate total marks
        self.total_marks = (
            (self.mid_term_marks or Decimal('0.00')) +
            (self.final_marks or Decimal('0.00')) +
            (self.quiz_marks or Decimal('0.00')) +
            (self.assignment_marks or Decimal('0.00')) +
            (self.lab_marks or Decimal('0.00')) +
            (self.attendance_marks or Decimal('0.00'))
        )
        
        # Calculate percentage (max marks = 100)
        self.percentage = self.total_marks
        
        pct = float(self.percentage)
        if pct >= 90:
            self.grade = 'A+'
            self.grade_point = Decimal('4.00')
            self.is_passed = True
        elif pct >= 80:
            self.grade = 'A'
            self.grade_point = Decimal('4.00')
            self.is_passed = True
        elif pct >= 70:
            self.grade = 'B+'
            self.grade_point = Decimal('3.50')
            self.is_passed = True
        elif pct >= 60:
            self.grade = 'B'
            self.grade_point = Decimal('3.00')
            self.is_passed = True
        elif pct >= 50:
            self.grade = 'C+'
            self.grade_point = Decimal('2.50')
            self.is_passed = True
        elif pct >= 40:
            self.grade = 'C'
            self.grade_point = Decimal('2.00')
            self.is_passed = True
        elif pct >= 33:
            self.grade = 'D'
            self.grade_point = Decimal('1.50')
            self.is_passed = True
        else:
            self.grade = 'F'
            self.grade_point = Decimal('0.00')
            self.is_passed = False
        
        super().save(*args, **kwargs)


class ComprehensiveResult(models.Model):
    """
    Comprehensive Result - ONE ROW PER STUDENT (all subjects in one row)
    Perfect for the main comprehensive results table view
    """
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='comprehensive_results')
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, null=True)
    section = models.ForeignKey(Section, on_delete=models.CASCADE, null=True)
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, null=True)
    
    # Store all subject marks in JSON format: {"SUB001": {"marks": 85, "grade": "A"}, "SUB002": {"marks": 72, "grade": "B+"}}
    subject_marks = models.JSONField(default=dict, help_text="JSON object containing marks for each subject")
    
    # Calculated fields
    total_marks = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    total_possible = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    cgpa = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal('0.00'))
    passed_subjects = models.IntegerField(default=0)
    failed_subjects = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('student', 'semester')
        ordering = ['student__student_id']

    def __str__(self):
        return f"{self.student.student_id} - Semester {self.semester.number if self.semester else 'N/A'}"

    def update_from_subject_results(self):
        """Update comprehensive result from StudentSubjectResult records"""
        subject_results = StudentSubjectResult.objects.filter(
            student=self.student,
            semester=self.semester
        )
        
        self.subject_marks = {}
        total = Decimal('0.00')
        passed = 0
        failed = 0
        
        for result in subject_results:
            self.subject_marks[result.subject.code] = {
                'marks': float(result.total_marks),
                'grade': result.grade,
                'percentage': float(result.percentage)
            }
            total += result.total_marks
            if result.is_passed:
                passed += 1
            else:
                failed += 1
        
        self.total_marks = total
        self.total_possible = Decimal(str(len(subject_results) * 100))
        self.passed_subjects = passed
        self.failed_subjects = failed
        
        if self.total_possible > 0:
            self.percentage = (self.total_marks / self.total_possible) * 100
            self.cgpa = self.percentage / 25
        
        self.save()

    def calculate_totals(self):
        """Calculate totals from subject_marks JSON"""
        total = Decimal('0.00')
        passed = 0
        failed = 0
        
        for subject_code, data in self.subject_marks.items():
            marks = Decimal(str(data.get('marks', 0)))
            total += marks
            grade = data.get('grade', 'F')
            if grade != 'F':
                passed += 1
            else:
                failed += 1
        
        self.total_marks = total
        self.total_possible = Decimal(str(len(self.subject_marks) * 100))
        self.passed_subjects = passed
        self.failed_subjects = failed
        
        if self.total_possible > 0:
            self.percentage = (self.total_marks / self.total_possible) * 100
            self.cgpa = self.percentage / 25


class Transcript(models.Model):
    TRANSCRIPT_TYPES = [
        ('official', 'Official Transcript'),
        ('unofficial', 'Unofficial Transcript'),
        ('provisional', 'Provisional Certificate'),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='transcripts')
    transcript_number = models.CharField(max_length=50, unique=True)
    transcript_type = models.CharField(max_length=20, choices=TRANSCRIPT_TYPES)
    issue_date = models.DateField()
    
    cumulative_gpa = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal('0.00'))
    total_credits_attempted = models.PositiveIntegerField(default=0)
    total_credits_earned = models.PositiveIntegerField(default=0)
    total_quality_points = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    
    is_issued = models.BooleanField(default=True)
    issued_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-issue_date']

    def __str__(self):
        return f"Transcript {self.transcript_number} - {self.student.student_id}"

    def save(self, *args, **kwargs):
        if not self.transcript_number:
            self.transcript_number = f"TR-{self.student.student_id}-{timezone.now().strftime('%Y%m%d%H%M%S')}"
        super().save(*args, **kwargs)


class TranscriptRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('issued', 'Issued'),
    ]
    
    REQUEST_TYPE_CHOICES = [
        ('official', 'Official Transcript'),
        ('unofficial', 'Unofficial Transcript'),
        ('provisional', 'Provisional Certificate'),
        ('duplicate', 'Duplicate Degree'),
    ]
    
    DELIVERY_CHOICES = [
        ('pickup', 'Pickup from Office'),
        ('courier', 'Courier Service'),
        ('email', 'Email'),
    ]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='transcript_requests')
    request_type = models.CharField(max_length=20, choices=REQUEST_TYPE_CHOICES, default='official')
    purpose = models.TextField(blank=True)
    
    request_date = models.DateTimeField(auto_now_add=True)
    number_of_copies = models.PositiveIntegerField(default=1)
    
    delivery_method = models.CharField(max_length=20, choices=DELIVERY_CHOICES, default='pickup')
    delivery_address = models.TextField(blank=True)
    
    payment_status = models.CharField(max_length=20, default='pending')
    payment_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    payment_date = models.DateTimeField(null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    remarks = models.TextField(blank=True)
    
    processed_by = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, blank=True)
    processed_date = models.DateTimeField(null=True, blank=True)
    issued_date = models.DateTimeField(null=True, blank=True)
    
    tracking_number = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-request_date']

    def __str__(self):
        return f"{self.student.student_id} - {self.get_request_type_display()} - {self.status}"