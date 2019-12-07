from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Discipline(models.Model):  # Fixed spelling from Decipline to Discipline
    PROGRAM_CHOICES = [
        ('BS', 'BS'),
        ('MS', 'MS'),
        ('PhD', 'PhD'),
    ]

    FIELD_CHOICES = [
        ('Computer Science', 'Computer Science'),
        ('Software Engineering', 'Software Engineering'),
        ('Artificial Intelligence', 'Artificial Intelligence'),
        ('Cyber Security', 'Cyber Security'),
        ('Data Science', 'Data Science'),
    ]

    program = models.CharField(max_length=40, choices=PROGRAM_CHOICES)
    field = models.CharField(max_length=40, choices=FIELD_CHOICES)

    class Meta:
        unique_together = ('program', 'field')
        verbose_name_plural = "Disciplines"

    def __str__(self):
        return f"{self.program} in {self.field}"


class Batch(models.Model):
    name = models.CharField(max_length=10)
    start_session = models.CharField(max_length=10)
    end_session = models.CharField(max_length=10)
    discipline = models.ForeignKey(Discipline, on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.name}'


class Semester(models.Model):
    number = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(8)],
        unique=True
    )

    def __str__(self):
        return f'Semester {self.number}'


class Section(models.Model):  # Changed from Sections to Section (singular)
    name = models.CharField(max_length=10)
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE)
    discipline = models.ForeignKey(Discipline, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('name', 'batch')

    def __str__(self):
        return f'{self.name} ({self.batch.name})'


class Department(models.Model):
    name = models.CharField(max_length=10)

    def __str__(self):
        return f'{self.name}'