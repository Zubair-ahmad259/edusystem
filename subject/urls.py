# subject/urls.py
from django.urls import path
from . import views

app_name = 'subject'

urlpatterns = [
    # Dashboard
    path('dashboard/', views.subject_dashboard, name='subject_dashboard'),
    path('', views.subject_dashboard, name='subject_dashboard'),
    
    # Subject CRUD
    path('add/', views.add_subject, name='add_subject'),
    path('view/', views.view_subject, name='view_subject'),
    path('edit/<int:subject_id>/', views.edit_subject, name='edit_subject'),
    path('delete/<int:subject_id>/', views.delete_subject, name='delete_subject'),
    
    # Subject Assignments
    path('assign/add/', views.add_subject_assign, name='add_subject_assign'),
    path('assign/view/', views.show_subject_assign, name='show_subject_assign'),
    path('assign/edit/<int:assign_id>/', views.edit_subject_assign, name='edit_subject_assign'),
    path('assign/delete/<int:assign_id>/', views.delete_subject_assign, name='delete_subject_assign'),
    
    # API endpoints
    path('api/quick-stats/', views.quick_stats_api, name='quick_stats_api'),
    path('api/get-sections/', views.get_sections_for_assignment, name='get_sections_for_assignment'),
    path('api/get-prerequisites/', views.get_prerequisite_suggestions, name='get_prerequisite_suggestions'),
]