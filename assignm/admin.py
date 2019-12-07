from django.contrib import admin
from django.utils.html import format_html
from .models import Assignment, AssignmentSubmission

class AssignmentSubmissionInline(admin.TabularInline):
    model = AssignmentSubmission
    extra = 0
    readonly_fields = ('submitted_date', 'file_hash', 'plagiarism_score')
    fields = ('student', 'submission_file', 'status', 'marks_obtained', 'teacher_feedback', 'plagiarism_score')

@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject_code', 'teacher_name', 'assignment_type', 'due_date', 'total_marks', 'is_active', 'submissions_count')
    list_filter = ('assignment_type', 'is_active', 'created_date', 'due_date')
    search_fields = ('title', 'description', 'subject_assign__subject__name', 'subject_assign__subject__code', 'teacher__first_name', 'teacher__last_name')
    readonly_fields = ('created_date', 'updated_date', 'file_hash', 'file_size', 'file_preview')
    filter_horizontal = ('sections',)
    inlines = [AssignmentSubmissionInline]
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'assignment_type', 'subject_assign', 'teacher')
        }),
        ('Target Sections', {
            'fields': ('sections',)
        }),
        ('Assignment File', {
            'fields': ('assignment_file', 'file_preview', 'file_hash', 'file_size')
        }),
        ('Grading & Dates', {
            'fields': ('total_marks', 'due_date', 'created_date', 'updated_date')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )
    
    def subject_code(self, obj):
        return f"{obj.subject_assign.subject.code} - {obj.subject_assign.subject.name}"
    subject_code.short_description = "Subject"
    
    def teacher_name(self, obj):
        return f"{obj.teacher.first_name} {obj.teacher.last_name}"
    teacher_name.short_description = "Teacher"
    
    def submissions_count(self, obj):
        count = obj.submissions.count()
        graded = obj.submissions.filter(status='graded').count()
        # Fix: Use format_html with proper arguments
        return format_html('<b>Total:</b> {}<br><b>Graded:</b> {}', count, graded)
    submissions_count.short_description = "Submissions"
    
    def file_preview(self, obj):
        if obj.assignment_file:
            return format_html('<a href="{}" target="_blank">📄 Download File</a>', obj.assignment_file.url)
        return "No file uploaded"
    file_preview.short_description = "File Preview"


@admin.register(AssignmentSubmission)
class AssignmentSubmissionAdmin(admin.ModelAdmin):
    list_display = ('student_name', 'assignment_title', 'submitted_date', 'status_badge', 'marks', 'plagiarism_badge')
    list_filter = ('status', 'is_plagiarized', 'submitted_date', 'assignment__assignment_type')
    search_fields = ('student__user__first_name', 'student__user__last_name', 'assignment__title', 'student__roll_number')
    readonly_fields = ('submitted_date', 'updated_date', 'file_hash', 'plagiarism_score', 'file_preview')
    
    fieldsets = (
        ('Assignment Information', {
            'fields': ('assignment', 'student')
        }),
        ('Submission File', {
            'fields': ('submission_file', 'file_preview', 'file_hash', 'file_size')
        }),
        ('Grading', {
            'fields': ('marks_obtained', 'teacher_feedback', 'status')
        }),
        ('Plagiarism Check', {
            'fields': ('plagiarism_score', 'is_plagiarized')
        }),
        ('Timestamps', {
            'fields': ('submitted_date', 'updated_date')
        }),
    )
    
    def student_name(self, obj):
        return f"{obj.student.user.get_full_name()} ({obj.student.roll_number})"
    student_name.short_description = "Student"
    
    def assignment_title(self, obj):
        return obj.assignment.title
    assignment_title.short_description = "Assignment"
    
    def status_badge(self, obj):
        colors = {
            'submitted': 'blue',
            'late': 'orange',
            'resubmitted': 'purple',
            'rejected': 'red',
            'graded': 'green',
        }
        color = colors.get(obj.status, 'gray')
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, obj.status.upper())
    status_badge.short_description = "Status"
    
    def plagiarism_badge(self, obj):
        if obj.is_plagiarized:
            return format_html('<span style="color: red;">⚠️ {:.1f}%</span>', obj.plagiarism_score)
        return format_html('<span style="color: green;">✓ Clean</span>')
    plagiarism_badge.short_description = "Plagiarism"
    
    def marks(self, obj):
        if obj.marks_obtained is not None:
            return format_html('<b>{}/{}</b>', obj.marks_obtained, obj.assignment.total_marks)
        return "Not graded"
    marks.short_description = "Marks"
    
    def file_preview(self, obj):
        if obj.submission_file:
            return format_html('<a href="{}" target="_blank">📄 Download Submission</a>', obj.submission_file.url)
        return "No file uploaded"
    file_preview.short_description = "File Preview"