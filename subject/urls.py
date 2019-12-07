from django.urls import path
from . import views

app_name = 'subject'

urlpatterns = [
    # DASHBOARD URLS
    path('dashboard/', views.subject_dashboard, name='subject_dashboard'),
    path('dashboard/overview/', views.dashboard_overview, name='dashboard_overview'),
    path('dashboard/analytics/', views.subject_analytics, name='subject_analytics'),
    path('dashboard/health-check/', views.subject_health_check, name='subject_health_check'),
    
    # Dashboard API endpoints
    path('api/dashboard/quick-stats/', views.quick_stats_api, name='quick_stats_api'),
    path('api/dashboard/recent-activity/', views.recent_activity_api, name='recent_activity_api'),
    
    # Main subject URLs
    path('add/', views.add_subject, name='add_subject'),
    path('view/', views.view_subject, name='view_subject'),
    path('import/', views.import_subjects, name='import_subjects'),
    path('export-template/', views.export_subjects_template, name='export_subjects_template'),
    
    # Subject assignment URLs
    path('subject-assign/add/', views.add_subject_assign, name='add_subject_assign'),
    path('subject-assign/show/', views.show_subject_assign, name='show_subject_assign'),
    
    # Student related URLs
    path('student/<int:student_id>/prerequisites/', views.check_student_prerequisites, name='check_student_prerequisites'),
    path('student/subjects/', views.stu_subject, name='stu_subject'),
    
    # API endpoints
    path('api/batches-for-discipline/', views.get_batches_for_discipline, name='get_batches_for_discipline'),
    path('api/prerequisite-suggestions/', views.get_prerequisite_suggestions, name='prerequisite_suggestions'),
    path('api/get-sections/', views.get_sections_for_discipline, name='get_sections_for_discipline'),  # THIS MUST EXIST
    path('api/get-sections-for-assignment/', views.get_sections_for_discipline, name='get_sections_for_assignment'),
    
    # Debug URLs
    path('debug/all/', views.show_all_subjects, name='show_all_subjects'),
    path('debug/prerequisites/', views.debug_prerequisites, name='debug_prerequisites'),
]