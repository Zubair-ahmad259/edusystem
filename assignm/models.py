from django.db import models
from django.core.validators import FileExtensionValidator, MinValueValidator, MaxValueValidator
from teachers.models import Teacher
from subject.models import SubjectAssign
from student.models import Student
from Academic.models import Section, Batch, Semester
import hashlib
from django.utils import timezone

class Assignment(models.Model):
    ASSIGNMENT_TYPES = [
        ('assignment', 'Assignment'),
        ('quiz', 'Quiz'),
        ('project', 'Project'),
        ('lab', 'Lab Report'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    subject_assign = models.ForeignKey(
        SubjectAssign,
        on_delete=models.CASCADE,
        related_name='assignments'
    )
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE,
        related_name='assignments'
    )
    assignment_type = models.CharField(max_length=20, choices=ASSIGNMENT_TYPES, default='assignment')
    
    # Target sections (from SubjectAssign)
    sections = models.ManyToManyField(Section, related_name='assignments', blank=True)
    
    assignment_file = models.FileField(
        upload_to='assignments/',
        validators=[FileExtensionValidator(['pdf', 'doc', 'docx', 'txt', 'ppt', 'pptx'])]
    )
    file_hash = models.CharField(max_length=64, blank=True, null=True)
    file_size = models.IntegerField(blank=True, null=True)
    
    due_date = models.DateTimeField()
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    is_active = models.BooleanField(default=True)
    total_marks = models.IntegerField(default=100, validators=[MinValueValidator(1), MaxValueValidator(1000)])
    
    class Meta:
        ordering = ['-created_date']
    
    def save(self, *args, **kwargs):
        if self.assignment_file:
            if self.file_size is None:
                self.file_size = self.assignment_file.size
            self.assignment_file.seek(0)
            file_content = self.assignment_file.read()
            self.file_hash = hashlib.md5(file_content).hexdigest()
            self.assignment_file.seek(0)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.title} - {self.subject_assign.subject.code}"

class AssignmentSubmission(models.Model):
    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('late', 'Late Submission'),
        ('resubmitted', 'Resubmitted'),
        ('rejected', 'Rejected - Plagiarism'),
        ('graded', 'Graded'),
    ]
    
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='assignment_submissions')
    
    submission_file = models.FileField(
        upload_to='submissions/',
        validators=[FileExtensionValidator(['pdf', 'doc', 'docx', 'txt', 'zip'])]
    )
    file_hash = models.CharField(max_length=64, blank=True, null=True)
    file_size = models.IntegerField(blank=True, null=True)
    
    submitted_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')
    marks_obtained = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0)])
    teacher_feedback = models.TextField(blank=True)
    
    plagiarism_score = models.FloatField(default=0)
    is_plagiarized = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['assignment', 'student']
        ordering = ['-submitted_date']
    
    def check_plagiarism(self):
        other_submissions = AssignmentSubmission.objects.filter(
            assignment=self.assignment
        ).exclude(id=self.id)
        
        for submission in other_submissions:
            if submission.file_hash == self.file_hash:
                self.plagiarism_score = 100
                self.is_plagiarized = True
                self.status = 'rejected'
                self.save()
                return True
        return False
    
    def is_late(self):
        return timezone.now() > self.assignment.due_date
    
    def save(self, *args, **kwargs):
        if self.submission_file:
            self.submission_file.seek(0)
            file_content = self.submission_file.read()
            self.file_hash = hashlib.md5(file_content).hexdigest()
            self.file_size = self.submission_file.size
            self.submission_file.seek(0)
            
            if self.is_late() and self.status not in ['rejected', 'graded']:
                self.status = 'late'
        
        super().save(*args, **kwargs)
        self.check_plagiarism()
    
    def __str__(self):
        return f"{self.student.user.get_full_name()} - {self.assignment.title}"