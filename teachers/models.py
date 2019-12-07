from django.db import models
from django.utils.text import slugify
from django.utils.crypto import get_random_string
from home_auth.models import CustomUser

class Teacher(models.Model):  #
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="teacher", null=True, blank=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    father_name = models.CharField(max_length=100)
    teacher_id = models.CharField(max_length=20, unique=True)  
    gender = models.CharField(max_length=10, choices=[('Male','Male'),('Female','Female'),('Others','Others')], blank=True, null=True)
    date_of_birth = models.DateField(null=True, blank=True)
    salary = models.DecimalField(max_digits=10, decimal_places=2,blank=True,null=True)  
    religion = models.CharField(max_length=50, blank=True)  
    joining_date = models.DateField(null=True, blank=True)
    mobile_number = models.CharField(max_length=15)  
    email = models.EmailField(max_length=100)  
    field = models.CharField(max_length=50, verbose_name="Specialization")  
    experience = models.PositiveIntegerField(blank=True,null=True)  
    teacher_image = models.ImageField(upload_to='teachers/', blank=True) 
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    is_active = models.BooleanField(default=True) 
    role = models.CharField(max_length=50, blank=True, default="Teacher") 
    class Meta:
        ordering = ['first_name', 'last_name']
        verbose_name = "Teacher"
        verbose_name_plural = "Teachers"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.first_name}-{self.last_name}-{self.teacher_id}")
            self.slug = base_slug
            while Teacher.objects.filter(slug=self.slug).exists():
                self.slug = f"{base_slug}-{get_random_string(4)}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.teacher_id})"