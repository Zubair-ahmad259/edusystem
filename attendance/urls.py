# attendance/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('', views.attendance_dashboard, name='attendance_dashboard'),
    
    # Attendance CRUD
    path('list/', views.attendance_list, name='attendance_list'),
    path('mark/', views.mark_attendance, name='mark_attendance'),
    path('bulk/', views.bulk_attendance, name='bulk_attendance'),
    
    # Student Attendance
    path('student/<int:student_id>/', views.student_attendance, name='student_attendance'),
    
    # Subject Attendance
    path('subject/<int:subject_id>/', views.subject_attendance, name='subject_attendance'),
    
    # Reports
    path('daily/', views.daily_summary, name='daily_summary'),
    path('monthly/', views.monthly_reports, name='monthly_reports'),
    path('statistics/', views.attendance_statistics, name='attendance_statistics'),
    
    # API & AJAX
    path('api/', views.attendance_api, name='attendance_api'),
    path('api/students/', views.get_students_by_batch, name='get_students_by_batch'),
    
    # Export
    path('export/', views.export_attendance, name='export_attendance'),

        # AJAX API endpoints
   # New AJAX endpoints
    path('api/disciplines/', views.get_disciplines, name='get_disciplines'),
    path('api/batches/', views.get_batches_by_discipline, name='get_batches_by_discipline'),
    path('api/sections/', views.get_sections_by_batch, name='get_sections_by_batch'),
    path('api/semesters/', views.get_semesters, name='get_semesters'),
    # path('api/subjects-by-semester/', views.get_subjects_by_semester, name='get_subjects_by_semester'),
    path('api/students-by-section/', views.get_students_by_section, name='get_students_by_section'),
    
    path('api/subjects-for-attendance/', views.get_subjects_for_attendance, name='get_subjects_for_attendance'),
        # Subject Attendance
    path('subject/<int:subject_id>/', views.subject_attendance, name='subject_attendance'),
        path('short-attendance/', views.short_attendance, name='short_attendance'),
    path('subject-short-attendance/', views.subject_short_attendance, name='subject_short_attendance'),
    path('subject-short-attendance/<int:subject_id>/', views.subject_detail_short_attendance, name='subject_detail_short_attendance'),
    path('subject-short-attendance-report/<int:subject_id>/', 
         views.subject_short_attendance_report, 
         name='subject_short_attendance_report'),
# Add this to attendance/urls.py
# path('subject/<int:subject_id>/low-attendance/', views.subject_low_attendance, name='subject_low_attendance'),
    # Or keep the old one but fix it
    path('api/subjects-by-semester/', views.get_subjects_by_semester, name='get_subjects_by_semester'),

]