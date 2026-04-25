from django.urls import path
from . import views

app_name = 'academic'

urlpatterns = [
    # Dashboard
    path('', views.academic_dashboard, name='dashboard'),
    
    # Batch URLs
    path('add-batch/', views.add_batch, name='add_batch'),
    path('view-batch/', views.view_batch, name='view_batch'),
    path('edit-batch/<int:batch_id>/', views.edit_batch, name='edit_batch'),
    path('delete-batch/<int:batch_id>/', views.delete_batch, name='delete_batch'),
    
    # Section URLs
    path('add-section/', views.add_section, name='add_section'),
    path('view-section/', views.view_section, name='view_section'),
    path('edit-section/<int:section_id>/', views.edit_section, name='edit_section'),
    path('delete-section/<int:section_id>/', views.delete_section, name='delete_section'),
    
    # Semester URLs
    path('add-semester/', views.add_semester, name='add_semester'),
    path('view-semester/', views.view_semester, name='view_semester'),
    path('edit-semester/<int:semester_id>/', views.edit_semester, name='edit_semester'),
    path('delete-semester/<int:semester_id>/', views.delete_semester, name='delete_semester'),
    
    # Discipline URLs
    path('add-discipline/', views.add_discipline, name='add_discipline'),
    path('view-discipline/', views.view_discipline, name='view_discipline'),
    path('edit-discipline/<int:discipline_id>/', views.edit_discipline, name='edit_discipline'),
    path('delete-discipline/<int:discipline_id>/', views.delete_discipline, name='delete_discipline'),
]