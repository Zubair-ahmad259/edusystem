from django.db import models
from home_auth.models import CustomUser
from student.models import Discipline

class AdminProfile(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    father_name = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(max_length=255, unique=True)
    discipline = models.ForeignKey(Discipline, on_delete=models.SET_NULL, null=True, blank=True)
    role = models.CharField(
        max_length=50,
        choices=[
            ('HOD', 'Head of Department'),
            ('Coordinator', 'Coordinator'),
            ('Section Head', 'Section Head'),
        ],
        default=None
    )
    address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.role})"
