from django.urls import path
from . import views

app_name = 'admin_profile'

urlpatterns = [
    # List and Create
    path('', views.admin_profile_list, name='admin_profile_list'),
    path('create/', views.admin_profile_create, name='admin_profile_create'),
    
    # Detail, Update, Delete
    path('<int:pk>/', views.admin_profile_detail, name='admin_profile_detail'),
    path('<int:pk>/update/', views.admin_profile_update, name='admin_profile_update'),
    path('<int:pk>/delete/', views.admin_profile_delete, name='admin_profile_delete'),
    
    # Import/Export
    path('import/', views.import_admin_profiles, name='import_admin_profiles'),
    path('download-sample/', views.download_sample_excel, name='download_sample_excel'),
    
    # Debug
    path('debug-permissions/', views.debug_admin_permissions, name='debug_admin_permissions'),
]