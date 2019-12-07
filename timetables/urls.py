# timetables/urls.py

from django.urls import path
from . import views

app_name = 'timetables'

urlpatterns = [
    # Dashboard
    path('dashboard/', views.timetable_dashboard, name='dashboard'),
    path('', views.timetable_dashboard, name='timetable_dashboard'),
        path('classroom-timetable/', views.classroom_timetable_view, name='classroom_list_timetable'),
    path('classroom-timetable/<int:classroom_id>/', views.classroom_timetable_view, name='classroom_timetable'),
    
    # Section Timetable URLs
    path('section-timetable/', views.section_timetable_view, name='section_list_timetable'),
    path('section-timetable/<int:section_id>/', views.section_timetable_view, name='section_timetable'),
# Section Timetable URLs
    path('section-timetable/', views.section_timetable_view, name='section_list_timetable'),
    path('section-timetable/<int:section_id>/', views.section_timetable_view, name='section_timetable'),
    
    
    # Teacher Timetable URLs
    path('teacher/<int:teacher_id>/', views.teacher_timetable_view, name='teacher_timetable'),
    path('teacher/', views.teacher_timetable_view, name='my_timetable'),
    
    # Section Timetable URLs
    path('section/<int:section_id>/', views.section_timetable_view, name='section_timetable'),
    
    # Generate Timetable URLs - ORDER MATTERS! Put the one without ID first
    path('generate/teacher/', views.teacher_list_for_generate, name='generate_teacher_list'),
    path('generate/teacher/<int:teacher_id>/', views.generate_teacher_timetable, name='generate_teacher_timetable'),
    path('generate/section/<int:section_id>/', views.generate_section_timetable, name='generate_section_timetable'),
    
    # Time Slot URLs
    path('time-slots/', views.time_slot_list, name='time_slot_list'),
    path('time-slots/create/', views.time_slot_create, name='time_slot_create'),
    path('time-slots/<int:slot_id>/edit/', views.time_slot_edit, name='time_slot_edit'),
    path('time-slots/<int:slot_id>/delete/', views.time_slot_delete, name='time_slot_delete'),
    path('time-slots/<int:slot_id>/toggle/', views.time_slot_toggle_status, name='time_slot_toggle'),
    
      path('classrooms/', views.classroom_list, name='classroom_list'),
    path('classrooms/create/', views.classroom_create, name='classroom_create'),
    path('classrooms/<int:classroom_id>/edit/', views.classroom_edit, name='classroom_edit'),
    path('classrooms/<int:classroom_id>/delete/', views.classroom_delete, name='classroom_delete'),
    
path('get-sections-by-batch/', views.get_sections_by_batch, name='get_sections_by_batch'),

    # Teacher Availability URLs
    path('availability/', views.teacher_availability_view, name='teacher_availability'),
    
    # Conflict Check URLs
    path('conflicts/', views.check_conflicts, name='check_conflicts'),

    path('timetable-entry/<int:entry_id>/edit/', views.edit_timetable_entry, name='edit_timetable_entry'),
# Laboratory URLs
    path('laboratories/', views.laboratory_list, name='laboratory_list'),
    path('laboratories/create/', views.laboratory_create, name='laboratory_create'),
    path('laboratories/<int:lab_id>/edit/', views.laboratory_edit, name='laboratory_edit'),
    path('laboratories/<int:lab_id>/delete/', views.laboratory_delete, name='laboratory_delete'),
    path('laboratories/<int:lab_id>/timetable/', views.laboratory_timetable, name='laboratory_timetable'),
    
    # Exam Timetable URLs
    path('exams/', views.exam_timetable_view, name='exam_timetable'),
    path('exams/create/', views.create_exam_timetable, name='create_exam_timetable'),
    
    # AJAX endpoints
    path('get-teacher-subjects/', views.get_teacher_subjects, name='get_teacher_subjects'),
]