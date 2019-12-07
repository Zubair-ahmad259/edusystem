from django.contrib import admin
from .models import SubjectMarkComponents, Exam, ExamResult, SubjectComprehensiveResult, Transcript

@admin.register(SubjectMarkComponents)
class SubjectMarkComponentsAdmin(admin.ModelAdmin):
    list_display = ('subject', 'teacher', 'semester', 'batch', 'section', 'academic_year', 'total_percentage')
    list_filter = ('semester', 'batch', 'academic_year')
    search_fields = ('subject__name', 'subject__code', 'teacher__first_name', 'teacher__last_name')
    readonly_fields = ('total_percentage', 'internal_percentage')

@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ('subject_mark_component', 'exam_type', 'exam_date', 'total_marks', 'passing_marks', 'is_published')
    list_filter = ('exam_type', 'is_published', 'exam_date')
    search_fields = ('subject_mark_component__subject__name', 'subject_mark_component__subject__code')
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Set default passing marks based on exam type
        if not obj:  # Only for new objects
            form.base_fields['passing_marks'].initial = 40.00
        return form
    
    def save_model(self, request, obj, form, change):
        # Auto-set passing marks if not provided
        if not obj.passing_marks:
            obj.passing_marks = obj.total_marks * Decimal('0.40')
        super().save_model(request, obj, form, change)

@admin.register(ExamResult)
class ExamResultAdmin(admin.ModelAdmin):
    list_display = ('student', 'exam', 'marks_obtained', 'grade', 'is_absent', 'entered_at')
    list_filter = ('grade', 'is_absent', 'exam__exam_type')
    search_fields = ('student__student_id', 'student__first_name', 'exam__subject_mark_component__subject__name')

@admin.register(SubjectComprehensiveResult)
class SubjectComprehensiveResultAdmin(admin.ModelAdmin):
    list_display = ('student', 'subject_mark_component', 'total_marks', 'grade', 'grade_point')
    list_filter = ('grade', 'subject_mark_component__semester')
    search_fields = ('student__student_id', 'subject_mark_component__subject__name')

@admin.register(Transcript)
class TranscriptAdmin(admin.ModelAdmin):
    list_display = ('transcript_number', 'student', 'issue_date', 'cumulative_gpa', 'is_issued')
    list_filter = ('transcript_type', 'is_issued')
    search_fields = ('transcript_number', 'student__student_id')
    readonly_fields = ('transcript_number',)