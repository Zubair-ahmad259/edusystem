from django.urls import path
from . import views

app_name = 'token_app'

urlpatterns = [
    # Home
    path('', views.index, name='index'),
    
    # Dashboard & Statistics
    path('dashboard/', views.dashboard, name='dashboard'),
    path('statistics/', views.statistics, name='statistics'),
    
    # Token Lists
    path('tokens/', views.all_tokens, name='all_tokens'),
    path('student-tokens/', views.student_tokens, name='student_tokens'),
    path('student-tokens/<int:student_id>/', views.student_tokens, name='student_tokens'),
    
    # Token Details
    path('token/<int:token_id>/', views.token_detail, name='token_detail'),
    path('token/<int:token_id>/print/', views.print_token, name='print_token'),
    
    # Create Tokens
    path('create/', views.create_token, name='create_token'),
    path('create/<int:student_id>/', views.create_token_for_student, name='create_token_for_student'),
    path('bulk-create/', views.bulk_create_tokens, name='bulk_create_tokens'),
    
    # Token Actions
    path('token/<int:token_id>/update-status/', views.update_token_status, name='update_token_status'),
    path('token/<int:token_id>/verify/', views.verify_token, name='verify_token'),
    
    # API/JSON
    path('api/student/<int:student_id>/', views.get_student_info, name='get_student_info'),
    path('api/student/<int:student_id>/subjects/', views.get_student_subjects, name='get_student_subjects'),
    path('api/check-token/<str:token_number>/', views.check_token_validity, name='check_token_validity'),

    # Token Generated Students
    path('token-generated-students/', views.token_generated_students, name='token_generated_students'),
    path('student/<int:student_id>/token-history/', views.student_token_history, name='student_token_history'),
    path('student/<int:student_id>/token/<int:token_id>/', views.student_token_detail, name='student_token_detail'),
]
