from django.db import models
from home_auth.models import CustomUser
from student.models import Discipline

class AdminProfile(models.Model):
    ROLE_CHOICES = [
        ('HOD', 'Head of Department'),
        ('Coordinator', 'Coordinator'),
        ('Section Head', 'Section Head'),
        ('Office Clerk', 'Office Clerk'),  # Added Office Clerk role
        ('Accounts', 'Accounts Officer'),
        ('Librarian', 'Librarian'),
    ]
    
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    father_name = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(max_length=255, unique=True)
    discipline = models.ForeignKey(Discipline, on_delete=models.SET_NULL, null=True, blank=True)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='Office Clerk')
    address = models.TextField(blank=True, null=True)
    employee_id = models.CharField(max_length=50, unique=True, blank=True, null=True)
    joining_date = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.get_role_display()})"
    
    def save(self, *args, **kwargs):
        if not self.employee_id:
            # Generate employee ID: EMP-YYYY-XXXX
            import random
            import datetime
            year = datetime.datetime.now().year
            random_num = random.randint(1000, 9999)
            self.employee_id = f"EMP-{year}-{random_num}"
        super().save(*args, **kwargs)