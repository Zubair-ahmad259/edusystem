from django.urls import path
from . import views

app_name = 'exam_manag'

urlpatterns = [
    # ==================== MAIN DASHBOARDS ====================
    path('dashboard/', views.dashboard, name='dashboard'),
    path('exam-dashboard/<int:exam_id>/', views.exam_dashboard, name='exam_dashboard'),
    
    # ==================== MARKS UPLOAD (TEACHER) - DIRECT UPLOAD ====================
    path('upload-marks/', views.upload_marks_dashboard, name='upload_marks_dashboard'),
    path('upload-direct/<int:subject_id>/<int:section_id>/<str:exam_type>/', views.upload_marks_direct, name='upload_marks_direct'),
    path('view-marks/<int:subject_id>/<int:section_id>/<str:exam_type>/', views.view_marks, name='view_marks'),
    path('publish-section/<int:subject_id>/<int:section_id>/', views.publish_section_marks, name='publish_section_marks'),
    path('delete-all-results/<int:subject_id>/<int:section_id>/<str:exam_type>/', views.delete_all_exam_results, name='delete_all_exam_results'),
path('edit-mark/<int:subject_id>/<int:section_id>/<str:exam_type>/<int:student_id>/', views.edit_student_mark, name='edit_student_mark'),
path('delete-mark/<int:subject_id>/<int:section_id>/<str:exam_type>/<int:student_id>/', views.delete_student_mark, name='delete_student_mark'),
    # ==================== RESULTS & COMPREHENSIVE VIEWS ====================
    path('comprehensive-results/', views.comprehensive_result_view, name='comprehensive_results'),
    path('student-subject-marks/', views.student_subject_marks, name='student_subject_marks'),
    path('delete-comprehensive/', views.delete_comprehensive_results, name='delete_comprehensive'),
    # ==================== STUDENT VIEWS ====================
    path('student-my-marks/', views.student_my_marks, name='student_my_marks'),
    path('student-subject-marks-detail/<int:subject_id>/', views.student_subject_marks_detail, name='student_subject_marks_detail'),
    path('student-marks-api/<int:subject_id>/', views.student_marks_api, name='student_marks_api'),
    # ==================== TRANSCRIPT REQUESTS (STUDENT) ====================
    path('student-transcript-request/', views.student_transcript_request, name='student_transcript_request'),
    path('student-transcript-requests/', views.student_transcript_requests_list, name='student_transcript_requests_list'),
    path('student-view-transcript/<int:request_id>/', views.student_view_transcript, name='student_view_transcript'),
    
    # ==================== ADMIN TRANSCRIPT MANAGEMENT ====================
    path('admin-transcript-requests/', views.admin_transcript_requests, name='admin_transcript_requests'),
    path('approve-transcript/<int:request_id>/', views.approve_transcript_request, name='approve_transcript_request'),
    path('reject-transcript/<int:request_id>/', views.reject_transcript_request, name='reject_transcript_request'),
    path('issue-transcript/<int:request_id>/', views.issue_transcript_request, name='issue_transcript_request'),
    path('generate-transcript-pdf/<int:request_id>/', views.generate_transcript_pdf, name='generate_transcript_pdf'),
    
    # ==================== ADMIN TRANSCRIPT MANAGEMENT (DIRECT) ====================
    path('all-transcripts/', views.all_transcripts_list, name='all_transcripts_list'),
    path('view-transcript/<int:transcript_id>/', views.view_transcript, name='view_transcript'),
    path('generate-transcript/<int:student_id>/', views.generate_transcript, name='generate_transcript'),
    path('print-transcript/<int:transcript_id>/', views.print_transcript, name='print_transcript'),
    path('delete-transcript/<int:transcript_id>/', views.delete_transcript, name='delete_transcript'),
    path('admin-generate-transcript/', views.admin_generate_transcript_form, name='admin_generate_transcript'),
    path('generate-all-transcripts/', views.generate_all_transcripts, name='generate_all_transcripts'),
    
    # ==================== HELPER/DEBUG ====================
    path('debug-exam/<int:exam_id>/', views.debug_exam, name='debug_exam'),
]