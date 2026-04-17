from django.contrib import admin
from django.urls import path,include
from . import views

urlpatterns = [
   path('',views.index, name="index"),
   path('dashboard/', views.admin_dashboard, name='admin_dashboard'), 
   path('student-dashboard/', views.student_dashboard, name='student_dashboard'), 
    path('teachers-dashboard/', views.teacher_dashboard, name='teacher_dashboard'), 

]
