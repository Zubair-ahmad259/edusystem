from django.contrib import admin
from django.utils.html import format_html
from .models import Exam, ExamResult, ComprehensiveResult, Transcript, TranscriptRequest


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ['id', 'subject', 'section', 'teacher', 'exam_type', 'total_marks', 'is_published', 'exam_date']
    list_filter = ['exam_type', 'is_published', 'subject', 'section']
    search_fields = ['subject__code', 'subject__name', 'section__name']
    readonly_fields = ['created_at', 'updated_at', 'published_at']


@admin.register(ExamResult)
class ExamResultAdmin(admin.ModelAdmin):
    list_display = ['id', 'student', 'exam', 'marks_obtained', 'is_absent', 'grade', 'entered_at']
    list_filter = ['is_absent', 'exam__exam_type']
    search_fields = ['student__student_id', 'student__first_name', 'student__last_name']
    readonly_fields = ['entered_at', 'updated_at', 'percentage', 'grade', 'grade_point']


@admin.register(ComprehensiveResult)
class ComprehensiveResultAdmin(admin.ModelAdmin):
    list_display = ['id', 'student', 'semester', 'section', 'total_marks', 'percentage', 'cgpa', 'passed_subjects', 'failed_subjects']
    list_filter = ['semester', 'section', 'batch']
    search_fields = ['student__student_id', 'student__first_name', 'student__last_name']
    readonly_fields = ['total_marks', 'total_possible', 'percentage', 'cgpa', 'passed_subjects', 'failed_subjects', 'created_at', 'updated_at']
    
    def subject_marks_display(self, obj):
        """Display subject marks in a readable format"""
        if obj.subject_marks:
            html = '<div style="max-height: 100px; overflow-y: auto;">'
            for subject, data in obj.subject_marks.items():
                grade_color = 'green' if data.get('grade') != 'F' else 'red'
                html += f'<span style="display: inline-block; margin: 2px; padding: 2px 6px; background: #f0f0f0; border-radius: 4px;">'
                html += f'<strong>{subject}</strong>: {data.get("marks", 0)} '
                html += f'<span style="color: {grade_color};">({data.get("grade", "F")})</span>'
                html += f'</span><br>'
            html += '</div>'
            return format_html(html)
        return '-'
    subject_marks_display.short_description = 'Subject Marks'
    
    fieldsets = (
        ('Student Information', {
            'fields': ('student', 'semester', 'section', 'batch')
        }),
        ('Subject Marks (JSON)', {
            'fields': ('subject_marks',),
            'classes': ('wide',),
            'description': 'Format: {"SUB001": {"marks": 85, "grade": "A"}, "SUB002": {"marks": 72, "grade": "B+"}}'
        }),
        ('Calculated Results', {
            'fields': ('total_marks', 'total_possible', 'percentage', 'cgpa', 'passed_subjects', 'failed_subjects'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Transcript)
class TranscriptAdmin(admin.ModelAdmin):
    list_display = ['transcript_number', 'student', 'issue_date', 'cumulative_gpa', 'is_issued']
    list_filter = ['is_issued', 'issue_date']
    search_fields = ['transcript_number', 'student__student_id', 'student__first_name']


@admin.register(TranscriptRequest)
class TranscriptRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'student', 'request_type', 'request_date', 'status', 'delivery_method']
    list_filter = ['status', 'request_type', 'delivery_method']
    search_fields = ['student__student_id', 'student__first_name']