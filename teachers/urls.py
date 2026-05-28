from django.urls import path
from . import views

urlpatterns = [
    path("", views.teacher_list, name="teacher_list"),
    path("add/", views.add_teacher, name="add_teacher"),
    path("view/<str:teacher_id>/", views.view_teacher, name="view_teacher"),
    path("edit/<str:teacher_id>/", views.edit_teacher, name="edit_teacher"),
    path("delete/<str:teacher_id>/", views.delete_teacher, name="delete_teacher"),
    
    # Bulk operations
    
    path("bulk-paste/", views.bulk_paste_teachers, name="bulk_paste_teachers"),
    path("download-template/", views.download_teacher_template, name="download_teacher_template"),
    path("export-excel/", views.export_teachers_excel, name="export_teachers_excel"),



    path('profile/', views.teacher_profile, name='teacher_profile'),
    path('edit-profile/', views.edit_teacher_profile, name='edit_teacher_profile'),
    path('change-password/', views.change_password, name='change_password'),
    path('settings/', views.teacher_settings, name='teacher_settings'),
    # ... other URLs
]
