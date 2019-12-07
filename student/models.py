# student/models.py
from django.db import models
from home_auth.models import CustomUser
from Academic.models import Discipline, Batch, Semester, Section  # Import from academic app


class Parent(models.Model):
    father_name = models.CharField(max_length=100)
    mother_name = models.CharField(max_length=100)
    father_email = models.EmailField(blank=True, null=True)
    father_contact = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField()

    def __str__(self):
        return f"{self.father_name}"


class Student(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]

    # Basic Info
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    student_id = models.CharField(max_length=20, unique=True)
    admission_number = models.CharField(max_length=20, unique=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    dob = models.DateField()
    email = models.EmailField(unique=True)
    contact_number = models.CharField(max_length=15, blank=True)
    image = models.ImageField(upload_to='students/', blank=True, null=True)

    # Academic Info - Now using models from academic app
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE)
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE)
    section = models.ForeignKey(Section, on_delete=models.CASCADE)
    discipline = models.ForeignKey(Discipline, on_delete=models.CASCADE)

    parent = models.OneToOneField(Parent, on_delete=models.CASCADE, related_name='student', null=True, blank=True)
    address = models.TextField()

    class Meta:
        ordering = ['batch', 'section', 'last_name']

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.student_id})"