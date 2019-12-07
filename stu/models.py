# from django.db import models

# class Batch(models.Model):
#     name = models.CharField(max_length=50, unique=False)
#     start_year = models.IntegerField()
#     end_year = models.IntegerField()


#     def __str__(self):
#         return self.name

# class Semester(models.Model):
#     number = models.CharField(max_length=20)
#     def __str__(self):
#         return f"Semester {self.number}"

# class Section(models.Model):
#     name = models.CharField(max_length=10, unique=False)
#     batch = models.ForeignKey(Batch, on_delete=models.SET_NULL, null=True, blank=True)

#     class Meta:
#         unique_together = ('name', 'batch') 

#     def __str__(self):
#         if self.batch:
#             return f"{self.name} ({self.batch.name})"
#         return self.name

# class Parent(models.Model):
#     father_name = models.CharField(max_length=100)
#     father_email = models.EmailField(blank=True, null=True)
#     father_contact = models.CharField(max_length=15, blank=True, null=True)
#     address = models.TextField()

#     def __str__(self):
#         return f"{self.father_name}"
    


# # Create your models here.
# class Student(models.Model):
#     first_name=models.CharField(max_length=20)
#     last_name=models.CharField(max_length=30)
#     roll_noid=models.CharField(max_length=40)
#     contect_number=models.CharField(max_length=50) 
#     matric_marks=models.CharField(max_length=50)
#     fsc_marks=models.CharField(max_length=50)
#     batches = models.ForeignKey(Batch, on_delete=models.CASCADE)
#     semesters = models.ForeignKey(Semester, on_delete=models.CASCADE)
#     sections = models.ForeignKey(Section, on_delete=models.CASCADE)


#     def __str__(self):
#      return f"({self.roll_noid}) {self.first_name} {self.last_name} "