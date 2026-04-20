# student/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Student CRUD
    path('add/', views.add_student, name='add_student'),
    path('list/', views.student_list, name='student_list'),
    path('view/<int:student_id>/', views.view_student, name='view_student'),
    path('edit/<int:student_id>/', views.edit_student, name='edit_student'),
    path('delete/<int:student_id>/', views.delete_student, name='delete_student'),
    
    # Bulk Import/Export
    path('bulk-import/', views.bulk_student_import, name='bulk_student_import'),
    path('import-excel/', views.import_students_excel, name='import_students_excel'),
    path('download-template/', views.download_excel_template, name='download_template'),
    path('download-student-template/', views.download_student_template, name='download_student_template'),
    path('export-excel/', views.export_students_excel, name='export_students_excel'),
    # student/urls.py

    # ... your existing URLs ...
    path('bulk-paste/', views.bulk_paste_students, name='bulk_paste_students'),

    # Student Promotion
    path('promote/<int:student_id>/', views.promote_student, name='promote_student'),
    path('promote-all/', views.promote_all_students, name='promote_all_students'),
    
    # AJAX
    path('get-sections/', views.get_sections_by_batch, name='get_sections_by_batch'),
]