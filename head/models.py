from django.db import models
from home_auth.models import CustomUser
from student.models import Discipline

class AdminProfile(models.Model):
    ROLE_CHOICES = [
        ('HOD', 'Head of Department'),
        ('Coordinator', 'Coordinator'),
        ('Section Head', 'Section Head'),
        ('Office Clerk', 'Office Clerk'),
        ('Accounts', 'Accounts Officer'),
        ('Librarian', 'Librarian'),
    ]
    
    # Add this OneToOneField to link to CustomUser
    user = models.OneToOneField(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='admin_profile'
    )
    
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    father_name = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(max_length=255, unique=True)
    
    # Single discipline (for HOD, Coordinator, Section Head)
    discipline = models.ForeignKey(Discipline, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Multiple disciplines (for Office Clerk, Accounts, Librarian)
    assigned_disciplines = models.JSONField(default=list, blank=True, help_text="List of discipline IDs for multi-discipline roles")
    
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='Office Clerk')
    address = models.TextField(blank=True, null=True)
    employee_id = models.CharField(max_length=50, unique=True, blank=True, null=True)
    joining_date = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.get_role_display()})"
    
    def get_disciplines_display(self):
        """Get display string for disciplines"""
        multi_discipline_roles = ['Office Clerk', 'Accounts', 'Librarian']
        
        if self.role in multi_discipline_roles:
            if self.assigned_disciplines:
                from student.models import Discipline
                disciplines = Discipline.objects.filter(id__in=self.assigned_disciplines)
                return ", ".join([f"{d.program} in {d.field}" for d in disciplines])
            return "All Disciplines"
        else:
            if self.discipline:
                return f"{self.discipline.program} in {self.discipline.field}"
        return "—"
    
    def save(self, *args, **kwargs):
        if not self.employee_id:
            import random
            import datetime
            year = datetime.datetime.now().year
            random_num = random.randint(1000, 9999)
            self.employee_id = f"EMP-{year}-{random_num}"
        
        # Clear assigned_disciplines if role is single-discipline
        multi_discipline_roles = ['Office Clerk', 'Accounts', 'Librarian']
        if self.role not in multi_discipline_roles:
            self.assigned_disciplines = []
        
        super().save(*args, **kwargs)