from django.urls import path
from . import views

urlpatterns = [
    # Authentication URLs
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Password Reset Flow
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('reset-password/<str:token>/', views.reset_password_view, name='reset_password'),
    path('reset-password-confirm/<str:token>/', views.reset_password_confirm_view, name='reset_password_confirm'),
    path('reset-password-success/', views.reset_password_success_view, name='reset_password_success'),

    # Management views
    path('manage-students/', views.manage_students_view, name='manage_students_view'),
    path('manage-teachers/', views.manage_teachers_view, name='manage_teachers'),
    path('manage-admins/', views.manage_admins_view, name='manage_admins'),
    path('test-email/', views.test_email, name='test_email'),
    path('validate-student-email/', views.validate_student_email, name='validate_student_email'),
    # Process password reset (POST request)
    path('process-password-reset/<str:user_type>/<int:user_id>/', views.process_password_reset, name='process_password_reset'),
]