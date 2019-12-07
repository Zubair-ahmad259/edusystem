from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from teachers.models import Teacher  
from Academic.models import Batch, Semester, Section, Discipline



# subject/models.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Subject(models.Model):
    SUBJECT_TYPE_CHOICES = [
        ('core', 'Core'),
        ('elective', 'Elective'),
    ]

    name = models.CharField(
        max_length=100,
        verbose_name="Subject Name",
        help_text="Enter the full name of the subject"
    )

    code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="Subject Code",
        help_text="Short code for the subject (e.g., CS101)"
    )

    # REMOVED: discipline, batch, semester, section
    # These fields are now only in SubjectAssign model
    
    subject_type = models.CharField(
        max_length=10,
        choices=SUBJECT_TYPE_CHOICES,
        default='core',
        verbose_name="Subject Type"
    )

    prerequisites = models.ManyToManyField(
        'self',
        symmetrical=False,
        blank=True,
        verbose_name="Prerequisite Subjects",
        help_text="Select subjects that must be completed before taking this subject",
        related_name='is_prerequisite_for'
    )

    credit_hours = models.PositiveSmallIntegerField(
        default=3,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(10)
        ],
        verbose_name="Credit Hours",
        help_text="Number of credit hours for this subject"
    )

    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="Description",
        help_text="Optional description about the subject"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.code} - {self.name}"

    def check_prerequisites(self, student):
        """Check if student has completed all prerequisites"""
        from student.models import StudentGrade
        
        prereqs = self.prerequisites.all()
        
        if not prereqs:
            return {
                'status': True,
                'message': 'No prerequisites required',
                'missing': []
            }
        
        missing_prereqs = []
        
        for prereq in prereqs:
            try:
                grade = StudentGrade.objects.get(
                    student=student,
                    subject=prereq
                )
                if grade.grade and grade.grade < 40:
                    missing_prereqs.append({
                        'subject': prereq,
                        'reason': f'Failed in {prereq.code} (Grade: {grade.grade})'
                    })
            except StudentGrade.DoesNotExist:
                missing_prereqs.append({
                    'subject': prereq,
                    'reason': f'Not completed {prereq.code}'
                })
        
        if missing_prereqs:
            return {
                'status': False,
                'message': f'Missing {len(missing_prereqs)} prerequisite(s)',
                'missing': missing_prereqs
            }
        
        return {
            'status': True,
            'message': 'All prerequisites completed',
            'missing': []
        }

    @property
    def prerequisite_codes(self):
        return ", ".join([p.code for p in self.prerequisites.all()]) or "None"

    class Meta:
        verbose_name = "Subject"
        verbose_name_plural = "Subjects"
        ordering = ['code']
class SubjectAssign(models.Model):
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE,
        related_name="assigned_subjects",
        verbose_name="Teacher",
        help_text="Select the teacher for this subject"
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="assigned_teachers",
        verbose_name="Subject",
        help_text="Select the subject to assign"
    )

    batch = models.ForeignKey(
        Batch,
        on_delete=models.CASCADE,
        related_name="subject_assignments",
        verbose_name="Batch",
        help_text="Select the batch for this assignment"
    )

    semester = models.ForeignKey(
        Semester,
        on_delete=models.CASCADE,
        related_name="subject_assignments",
        verbose_name="Semester",
        help_text="Select the semester for this assignment"
    )

    sections = models.ManyToManyField(
        Section,
        related_name="subject_assignments",
        verbose_name="Sections",
        help_text="Select multiple sections for this assignment"
    )

    assigned_date = models.DateField(
        auto_now_add=True,
        verbose_name="Assigned Date"
    )
    
    discipline = models.ForeignKey(
        Discipline, 
        on_delete=models.CASCADE,
        verbose_name="Discipline"
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Active SubjectAssign"
    )

    class Meta:
        verbose_name = "Subject Assignment"
        verbose_name_plural = "Subject Assignments"
        unique_together = ['teacher', 'subject', 'batch', 'semester']
        ordering = ['teacher', 'subject']

    def __str__(self):
        # Fix: Use 'field' instead of 'name' for Discipline
        discipline_name = self.discipline.field if self.discipline else "No Discipline"
        
        # Get sections for display
        sections_list = list(self.sections.all())
        if sections_list:
            sections_str = ", ".join([s.name for s in sections_list[:3]])
            if len(sections_list) > 3:
                sections_str += f" and {len(sections_list) - 3} more"
        else:
            sections_str = "No Sections"
        
        return f"{self.subject.code} - {self.subject.name} (Sem {self.semester.number}) - {discipline_name} - Sections: {sections_str}"