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

    case_type = models.CharField(max_length=10, choices=CASE_TYPE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE)
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE)
    section = models.ForeignKey(Section, on_delete=models.CASCADE)
    Disciplines = models.ForeignKey(Discipline, on_delete=models.CASCADE)
    fine=models.CharField(blank=True, max_length=50)
    status=models.CharField(blank=True, max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)  

    def __str__(self):
        return f"{self.student} - {self.get_case_type_display()}"
