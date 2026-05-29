from django.urls import path
from . import views

app_name = 'ddcomit'

urlpatterns = [
    path('cases/', views.case_list, name='case_list'),
    path('cases/add/', views.add_case, name='add_case'),
    path('cases/<int:case_id>/', views.case_detail, name='case_detail'),
    path('committee-cases/', views.committee_cases, name='committee_cases'),
    path('update-status/<int:case_id>/', views.update_case_status, name='update_case_status'),
    path('schedule-hearing/<int:case_id>/', views.schedule_hearing, name='schedule_hearing'),
    
    # AJAX endpoints - MUST HAVE THESE
    path('ajax/get-batches-by-discipline/', views.get_batches_by_discipline, name='get_batches_by_discipline'),
    path('ajax/get-sections-by-batch/', views.get_sections_by_batch, name='get_sections_by_batch'),
    path('ajax/get-students-by-section/', views.get_students_by_section, name='get_students_by_section'),
    path('ajax/get-subjects-by-semester/', views.get_subjects_by_semester, name='get_subjects_by_semester'),
    path('ajax/get-teachers-by-subject/', views.get_teachers_by_subject, name='get_teachers_by_subject'),
]