from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from django.utils import timezone

from student.models import Student
from Academic.models import Batch, Semester, Section, Discipline
from subject.models import Subject
from teachers.models import Teacher
from home_auth.models import CustomUser


class SubjectMarkComponents(models.Model):
    """Model to define mark distribution for a subject across different exam types based on credit hours"""
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='mark_components')
    teacher = models.ForeignKey(Teacher, on_delete=models.PROTECT, related_name='subject_mark_components')
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE)
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE)
    section = models.ForeignKey(Section, on_delete=models.CASCADE, null=True, blank=True)
    discipline = models.ForeignKey(Discipline, on_delete=models.CASCADE)
    academic_year = models.CharField(max_length=9, default=f"{timezone.now().year}-{timezone.now().year+1}")
    
    subject_type = models.CharField(max_length=20, default='theory')
    
    # Mark distribution percentages - Different defaults based on credit hours
    mid_term_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=20.00)
    final_term_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=65.00)
    quiz_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=5.00)
    assignment_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=5.00)
    presentation_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=5.00)
    lab_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    viva_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    attendance_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=5.00)
    internal_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=15.00, 
                                              help_text="Total internal marks (quiz + assignment + presentation + attendance)")
    
    total_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=100.00)
    
    notes = models.TextField(blank=True, help_text="Any notes about mark distribution")
    
    class Meta:
        unique_together = ('subject', 'teacher', 'semester', 'batch', 'section', 'academic_year')
        verbose_name = "Subject Mark Distribution"
        verbose_name_plural = "Subject Mark Distributions"
    
    def __str__(self):
        ch = self.subject.credit_hours
        ch_display = int(ch) if ch == int(ch) else ch
        return f"{self.subject.code} ({ch_display} CH) - {self.semester} - {self.batch}"
    

    def save(self, *args, **kwargs):
        # Determine if it's a lab/practical subject
        subject_name_lower = self.subject.name.lower()
        subject_code_lower = self.subject.code.lower()
        self.subject_type = 'lab' if ('lab' in subject_name_lower or 
                                      'practical' in subject_name_lower or 
                                      'lab' in subject_code_lower or 
                                      'prac' in subject_code_lower) else 'theory'
        
        # Calculate total percentage from user input
        self.total_percentage = (
            self.mid_term_percentage + 
            self.final_term_percentage + 
            self.quiz_percentage + 
            self.assignment_percentage + 
            self.presentation_percentage + 
            self.lab_percentage + 
            self.viva_percentage + 
            self.attendance_percentage
        )
        
        # Calculate internal percentage
        self.internal_percentage = (
            self.quiz_percentage + 
            self.assignment_percentage + 
            self.presentation_percentage + 
            self.attendance_percentage
        )
        
        super().save(*args, **kwargs)
    
    # ... (rest of the model remains the same) ...
    # Properties to access subject information easily
    @property
    def subject_name(self):
        return self.subject.name
    
    @property
    def subject_code(self):
        return self.subject.code
    
    @property
    def credit_hours(self):
        return self.subject.credit_hours
    
    def get_available_exam_types(self):
        """Get available exam types based on subject credit hours"""
        if self.credit_hours >= 6:
            return Exam.EXAM_TYPE_CHOICES  # All exam types
        elif self.credit_hours == 1 or self.credit_hours == 2:
            # For 1-2 credit hours: lab and viva only
            return [
                ('lab', 'Lab'),
                ('viva', 'Viva'),
            ]
        else:
            # For 3-5 credit hours: mid_term, final, quiz, assignment, presentation, attendance
            return [
                ('mid_term', 'Mid Term'),
                ('final', 'Final'),
                ('quiz', 'Quiz'),
                ('assignment', 'Assignment'),
                ('presentation', 'Presentation'),
                ('attendance', 'Attendance'),
            ]


class Exam(models.Model):
    EXAM_TYPE_CHOICES = [
        ('mid_term', 'Mid Term'),
        ('final', 'Final'),
        ('quiz', 'Quiz'),
        ('assignment', 'Assignment'),
        ('presentation', 'Presentation'),
        ('lab', 'Lab'),
        ('viva', 'Viva'),
        ('attendance', 'Attendance'),
    ]

    exam_type = models.CharField(max_length=20, choices=EXAM_TYPE_CHOICES)
    subject_mark_component = models.ForeignKey(
        SubjectMarkComponents, 
        on_delete=models.PROTECT,
        related_name='exams',
        help_text="Select subject mark distribution configuration"
    )
    
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
        default=40.00,
        help_text="Passing marks (default: 40% of total marks)"
    )
    
    is_published = models.BooleanField(default=False)
    
    weightage_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=100.00,
        help_text="Percentage weightage of this exam in overall subject marks"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('exam_type', 'subject_mark_component')
        ordering = ['-exam_date']

    def __str__(self):
        return f"{self.subject_mark_component.subject.code} - {self.get_exam_type_display()}"

    def save(self, *args, **kwargs):
        # Auto-calculate passing marks if not set or 0
        if self.passing_marks == 0 or not self.passing_marks:
            self.passing_marks = self.total_marks * Decimal('0.40')

        if self.is_published and not self.published_at:
            self.published_at = timezone.now()

        super().save(*args, **kwargs)
    
    def get_students(self):
        """Get all students enrolled for this exam based on subject, semester, batch"""
        from student.models import Student
        
        # Get filter criteria from subject_mark_component
        component = self.subject_mark_component
        
        # Build query with safety checks
        filters = {}
        
        # Check each filter exists and is not None
        if component.batch:
            filters['batch'] = component.batch
        
        if component.semester:
            filters['semester'] = component.semester
        
        if component.discipline:
            filters['discipline'] = component.discipline
        
        # Add section filter if specified
        if component.section:
            filters['section'] = component.section
        
        # If we have any filters, apply them
        if filters:
            try:
                return Student.objects.filter(**filters).order_by('student_id')
            except Exception as e:
                # Log error and return empty queryset
                print(f"Error getting students for exam {self.id}: {e}")
                return Student.objects.none()
        else:
            # No valid filters, return empty queryset
            return Student.objects.none()
    
    @property
    def student_count(self):
        """Property to get count of students for this exam"""
        return self.get_students().count()
    
    @property
    def result_count(self):
        """Property to get count of results entered"""
        return self.results.count()
    
    @property
    def is_ready_for_results(self):
        """Check if exam is published and ready for results entry"""
        return self.is_published and self.student_count > 0
    
    def get_exam_summary(self):
        """Get summary statistics for this exam"""
        from django.db.models import Count, Avg
        
        results = self.results.all()
        summary = {
            'total_students': self.student_count,
            'results_entered': results.count(),
            'absent_count': results.filter(is_absent=True).count(),
            'passed_count': results.exclude(grade='F').exclude(grade__isnull=True).count(),
            'failed_count': results.filter(grade='F').count(),
        }
        
        # Calculate average marks if results exist
        marks_results = results.filter(marks_obtained__isnull=False).exclude(is_absent=True)
        if marks_results.exists():
            avg_data = marks_results.aggregate(
                avg_marks=Avg('marks_obtained'),
                avg_percentage=Avg('percentage')
            )
            summary['avg_marks'] = avg_data['avg_marks'] or Decimal('0.00')
            summary['avg_percentage'] = avg_data['avg_percentage'] or Decimal('0.00')
        else:
            summary['avg_marks'] = Decimal('0.00')
            summary['avg_percentage'] = Decimal('0.00')
        
        return summary
class ExamResult(models.Model):
    GRADE_CHOICES = [
        ('A+', 'A+ (4.00)'),
        ('A', 'A (4.00)'),
        ('A-', 'A- (3.67)'),
        ('B+', 'B+ (3.33)'),
        ('B', 'B (3.00)'),
        ('B-', 'B- (2.67)'),
        ('C+', 'C+ (2.33)'),
        ('C', 'C (2.00)'),
        ('D', 'D (1.67)'),
        ('F', 'F (0.00)'),
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
    
    weighted_marks = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Marks after applying weightage percentage"
    )
    
    percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    grade = models.CharField(max_length=2, choices=GRADE_CHOICES, null=True, blank=True)
    grade_point = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    
    is_absent = models.BooleanField(default=False)
    remarks = models.TextField(blank=True)
    
    entered_by = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True)
    entered_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('exam', 'student')
        ordering = ['student__student_id']

    def __str__(self):
        return f"{self.student.student_id} - {self.exam} - {self.marks_obtained or 'Absent'}"

    def save(self, *args, **kwargs):
        if self.is_absent:
            self.marks_obtained = Decimal('0.00')
            self.weighted_marks = Decimal('0.00')

        if self.marks_obtained is not None and self.exam.total_marks > 0:
            # Calculate weighted marks
            weightage = self.exam.weightage_percentage / Decimal('100.00')
            self.weighted_marks = self.marks_obtained * weightage
            
            # Calculate percentage
            self.percentage = (self.marks_obtained / self.exam.total_marks) * 100
            
            # Calculate grade and grade point
            self.grade, self.grade_point = self.calculate_grade()

        super().save(*args, **kwargs)

    def calculate_grade(self):
        if self.percentage is None:
            return None, None
            
        pct = float(self.percentage)

        if pct >= 90:
            return 'A+', Decimal('4.00')
        if pct >= 85:
            return 'A', Decimal('4.00')
        if pct >= 80:
            return 'A-', Decimal('3.67')
        if pct >= 75:
            return 'B+', Decimal('3.33')
        if pct >= 70:
            return 'B', Decimal('3.00')
        if pct >= 65:
            return 'B-', Decimal('2.67')
        if pct >= 60:
            return 'C+', Decimal('2.33')
        if pct >= 55:
            return 'C', Decimal('2.00')
        if pct >= 50:
            return 'D', Decimal('1.67')
        return 'F', Decimal('0.00')


class SubjectComprehensiveResult(models.Model):
    """Comprehensive result for a subject combining all exam types"""
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='comprehensive_results')
    subject_mark_component = models.ForeignKey(
        SubjectMarkComponents, 
        on_delete=models.CASCADE,
        related_name='comprehensive_results'
    )
    
    # Marks from different components
    mid_term_marks = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    final_marks = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    quiz_marks = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    assignment_marks = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    presentation_marks = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    lab_marks = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    viva_marks = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    attendance_marks = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    
    # Calculated fields
    total_marks = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    grade = models.CharField(max_length=2, choices=ExamResult.GRADE_CHOICES, null=True, blank=True)
    grade_point = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    
    quality_points = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('student', 'subject_mark_component')
        ordering = ['subject_mark_component__semester', 'subject_mark_component__subject__code']
        verbose_name = "Comprehensive Subject Result"
        verbose_name_plural = "Comprehensive Subject Results"

    def __str__(self):
        return f"{self.student.student_id} - {self.subject.code} - {self.grade or 'No Grade'}"

    def save(self, *args, **kwargs):
        # Calculate total marks
        self.total_marks = (
            self.mid_term_marks + 
            self.final_marks + 
            self.quiz_marks + 
            self.assignment_marks + 
            self.presentation_marks + 
            self.lab_marks + 
            self.viva_marks + 
            self.attendance_marks
        )
        
        # Calculate percentage (assuming max 100 marks)
        self.percentage = self.total_marks
        
        # Calculate grade and grade point
        self.grade, self.grade_point = self.calculate_grade()
        
        # Calculate quality points using subject's credit hours
        self.quality_points = self.grade_point * self.subject.credit_hours
        
        super().save(*args, **kwargs)
    
    def calculate_grade(self):
        if self.total_marks >= 90:
            return 'A+', Decimal('4.00')
        if self.total_marks >= 85:
            return 'A', Decimal('4.00')
        if self.total_marks >= 80:
            return 'A-', Decimal('3.67')
        if self.total_marks >= 75:
            return 'B+', Decimal('3.33')
        if self.total_marks >= 70:
            return 'B', Decimal('3.00')
        if self.total_marks >= 65:
            return 'B-', Decimal('2.67')
        if self.total_marks >= 60:
            return 'C+', Decimal('2.33')
        if self.total_marks >= 55:
            return 'C', Decimal('2.00')
        if self.total_marks >= 50:
            return 'D', Decimal('1.67')
        return 'F', Decimal('0.00')
    
    # Properties to access information
    @property
    def subject(self):
        return self.subject_mark_component.subject
    
    @property
    def subject_name(self):
        return self.subject.name
    
    @property
    def subject_code(self):
        return self.subject.code
    
    @property
    def credit_hours(self):
        return self.subject.credit_hours
    
    @property
    def semester(self):
        return self.subject_mark_component.semester
    
    @property
    def batch(self):
        return self.subject_mark_component.batch
    
    @property
    def section(self):
        return self.subject_mark_component.section
    
    @property
    def teacher(self):
        return self.subject_mark_component.teacher


class Transcript(models.Model):
    TRANSCRIPT_TYPES = [
        ('official', 'Official'),
        ('unofficial', 'Unofficial'),
        ('provisional', 'Provisional'),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='transcripts')
    transcript_number = models.CharField(max_length=50, unique=True)
    transcript_type = models.CharField(max_length=20, choices=TRANSCRIPT_TYPES)
    issue_date = models.DateField()
    
    # GPA Information
    semester_gpa = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    cumulative_gpa = models.DecimalField(max_digits=3, decimal_places=2)
    total_credits_attempted = models.PositiveIntegerField(default=0)
    total_credits_earned = models.PositiveIntegerField()
    total_quality_points = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    
    # Institution Information
    university_name = models.CharField(max_length=200, blank=True)
    department_name = models.CharField(max_length=200, blank=True)
    program_name = models.CharField(max_length=200, blank=True)
    
    # Status
    is_issued = models.BooleanField(default=False)
    issued_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-issue_date']
        verbose_name = "Academic Transcript"
        verbose_name_plural = "Academic Transcripts"

    def __str__(self):
        return f"Transcript {self.transcript_number} - {self.student.student_id}"
    
    def save(self, *args, **kwargs):
        # Generate transcript number if not provided
        if not self.transcript_number:
            self.transcript_number = f"TR-{self.student.student_id}-{timezone.now().strftime('%Y%m%d%H%M%S')}"
        super().save(*args, **kwargs)