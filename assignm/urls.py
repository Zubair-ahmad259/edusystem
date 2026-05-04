from django.urls import path
from . import views

app_name = 'assignment'

urlpatterns = [
    # Dashboard
    path('dashboard/', views.assignment_dashboard, name='assignment_dashboard'),
    
    # Teacher URLs
    path('teacher/assignments/', views.teacher_assignment_list, name='teacher_assignment_list'),
    path('teacher/assignment/create/', views.teacher_assignment_create, name='teacher_assignment_create'),
    path('teacher/assignment/<int:assignment_id>/', views.teacher_assignment_detail, name='teacher_assignment_detail'),
    path('teacher/submission/<int:submission_id>/grade/', views.teacher_grade_submission, name='teacher_grade_submission'),
    
    # Student URLs
    path('student/assignments/', views.student_assignment_list, name='student_assignment_list'),
    path('student/assignment/<int:assignment_id>/', views.student_assignment_detail, name='student_assignment_detail'),
    path('student/submissions/', views.student_submission_status, name='student_submission_status'),
    
    # API
    path('api/sections-by-subject/', views.get_sections_by_subject, name='get_sections_by_subject'),


    
]