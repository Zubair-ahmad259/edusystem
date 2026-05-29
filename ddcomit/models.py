from django.db import models
from teachers.models import Teacher
from student.models import Student
from Academic.models import Batch, Semester, Section, Discipline
from subject.models import Subject


class Cases(models.Model):
    CASE_TYPE = [
        ('ufm', 'Unfair Means'),
        ('ddc', 'Department Discipline Committee'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('under_review', 'Under Review'),
        ('resolved', 'Resolved'),
        ('dismissed', 'Dismissed'),
    ]

    case_type = models.CharField(max_length=10, choices=CASE_TYPE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE)
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE)
    section = models.ForeignKey(Section, on_delete=models.CASCADE)
    Disciplines = models.ForeignKey(Discipline, on_delete=models.CASCADE)
    
    # Committee fields
    committee_hearing_date = models.DateField(null=True, blank=True)
    committee_hearing_time = models.TimeField(null=True, blank=True)
    committee_venue = models.CharField(max_length=200, blank=True, null=True)
    committee_remarks = models.TextField(blank=True, null=True)
    
    fine = models.CharField(blank=True, max_length=50)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')
    
    # Date fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    case_date = models.DateField(null=True, blank=True)
    incident_date = models.DateField(null=True, blank=True, help_text="Date when incident occurred")
    
    description = models.TextField(blank=True, null=True)
    evidence = models.FileField(upload_to='cases/evidence/', blank=True, null=True)

    def __str__(self):
        return f"{self.student} - {self.get_case_type_display()} - {self.case_date}"
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Case"
        verbose_name_plural = "Cases"