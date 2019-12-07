from django.urls import path
from . import views

urlpatterns = [
    # Main dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    path('', views.dashboard, name='exam_home'),
    
    # Subject Mark Components
    path('subject-mark-components/', views.subject_mark_components, name='subject_mark_components'),
    
    # Exam management
    path('exams/', views.exam_list, name='exam_list'),
    path('exam/create/', views.create_exam, name='create_exam'),
    path('exam/<int:exam_id>/dashboard/', views.exam_dashboard, name='exam_dashboard'),
    path('exam/<int:exam_id>/publish/', views.publish_exam, name='publish_exam'),
    path('exam/<int:exam_id>/upload-results/', views.upload_results, name='upload_results'),
    
    # Comprehensive results
    path('comprehensive-results/', views.comprehensive_result_view, name='comprehensive_results'),
    path('comprehensive-results/<int:student_id>/', views.comprehensive_result_view, name='student_comprehensive_results'),
    path('comprehensive-results/<int:student_id>/<int:semester_id>/', views.comprehensive_result_view, name='student_semester_comprehensive_results'),
    path('subject-result/<int:student_id>/<int:subject_mark_component_id>/', views.subject_result_detail, name='subject_result_detail'),
    path('select-student/', views.select_student_for_results, name='select_student_for_results'),
    path('subject-mark-components/delete/<int:id>/', views.delete_mark_component, name='delete_mark_component'),
    path('get-available-exam-types/', views.get_available_exam_types, name='get_available_exam_types'),
    path('exam/delete/<int:exam_id>/', views.delete_exam, name='delete_exam'),

    # Transcript management
    path('transcript/generate/<int:student_id>/', views.generate_transcript, name='generate_transcript'),
    path('transcript/<int:transcript_id>/', views.view_transcript, name='view_transcript'),
    path('transcript/<int:transcript_id>/print/', views.print_transcript, name='print_transcript'),
    path('transcript/<int:transcript_id>/delete/', views.delete_transcript, name='delete_transcript'),
    
    # Transcript lists
    path('student/transcripts/', views.student_transcript_list, name='student_transcript_list'),
    path('transcripts/all/', views.all_transcripts_list, name='all_transcripts_list'),
    path('debug-exam/<int:exam_id>/', views.debug_exam, name='debug_exam'),

]