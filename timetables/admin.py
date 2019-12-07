# timetables/admin.py - Simplified version

from django.contrib import admin
from .models import (
    TimeSlot, 
    Classroom, 
    TeacherAvailability, 
    TimetableEntry, 
    TimetableGenerationRequest,
    ExamTimetable
)

class TimeSlotAdmin(admin.ModelAdmin):
    list_display = ['day', 'start_time', 'end_time', 'duration_minutes', 'is_active']
    list_filter = ['day', 'is_active']
    search_fields = ['day']
    list_editable = ['is_active']
    list_per_page = 20



from django.contrib import admin
from django.utils.html import format_html
from .models import Classroom

class ClassroomAdmin(admin.ModelAdmin):
    list_display = ['room_number', 'building', 'capacity', 'discipline_display', 'batch_display', 'semester_display', 'section_display', 'facilities_icons', 'is_active']
    list_filter = ['building', 'has_projector', 'has_smartboard', 'is_lab', 'is_active', 'discipline', 'batch', 'semester']
    search_fields = ['room_number', 'building', 'discipline__field', 'batch__name', 'section__name']
    list_editable = ['is_active']
    list_per_page = 20
    autocomplete_fields = ['discipline', 'batch', 'semester', 'section']
    
    fieldsets = (
        ('Room Information', {
            'fields': ('room_number', 'building', 'capacity')
        }),
        ('Facilities', {
            'fields': ('has_projector', 'has_smartboard', 'is_lab')
        }),
        ('Association (Optional - for filtering)', {
            'fields': ('discipline', 'batch', 'semester', 'section'),
            'classes': ('collapse',),
            'description': 'These fields help filter classrooms by discipline, batch, semester, and section'
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )
    
    def discipline_display(self, obj):
        if obj.discipline:
            return format_html('<span style="color: #17a2b8;">{}</span>', obj.discipline)
        return '-'
    discipline_display.short_description = 'Discipline'
    
    def batch_display(self, obj):
        if obj.batch:
            return format_html('<span style="color: #28a745;">{}</span>', obj.batch.name)
        return '-'
    batch_display.short_description = 'Batch'
    
    def semester_display(self, obj):
        if obj.semester:
            return format_html('<span style="color: #ffc107;">Sem {}</span>', obj.semester.number)
        return '-'
    semester_display.short_description = 'Semester'
    
    def section_display(self, obj):
        if obj.section:
            return format_html('<span style="color: #dc3545;">{}</span>', obj.section.name)
        return '-'
    section_display.short_description = 'Section'
    
    def facilities_icons(self, obj):
        icons = []
        if obj.has_projector:
            icons.append('📽️')
        if obj.has_smartboard:
            icons.append('🖥️')
        if obj.is_lab:
            icons.append('💻')
        return ' '.join(icons) if icons else '-'
    facilities_icons.short_description = 'Facilities'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('discipline', 'batch', 'semester', 'section')


# Register the Classroom model
admin.site.register(Classroom, ClassroomAdmin)


class TeacherAvailabilityAdmin(admin.ModelAdmin):
    list_display = ['teacher', 'day', 'start_time', 'end_time', 'is_available', 'reason']
    list_filter = ['day', 'is_available']
    search_fields = ['teacher__first_name', 'teacher__last_name', 'teacher__teacher_id']
    list_per_page = 20
    autocomplete_fields = ['teacher']


class TimetableEntryAdmin(admin.ModelAdmin):
    list_display = ['teacher', 'subject', 'section', 'batch', 'semester', 'time_slot', 'classroom', 'is_exam', 'is_active']
    list_filter = ['is_active', 'is_exam', 'exam_type', 'time_slot__day', 'batch', 'semester']
    search_fields = [
        'teacher__first_name', 
        'teacher__last_name', 
        'subject__code', 
        'subject__name',
        'section__name',
        'classroom__room_number'
    ]
    list_per_page = 25
    autocomplete_fields = ['teacher', 'subject', 'section', 'batch', 'semester', 'time_slot', 'classroom']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Teacher & Subject Information', {
            'fields': ('teacher', 'subject')
        }),
        ('Class Information', {
            'fields': ('section', 'batch', 'semester')
        }),
        ('Schedule Information', {
            'fields': ('time_slot', 'classroom')
        }),
        ('Exam Details', {
            'fields': ('is_exam', 'exam_type'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )
    
    actions = ['make_active', 'make_inactive', 'mark_as_exam', 'mark_as_class']
    
    def make_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} entries marked as active.')
    make_active.short_description = "Mark selected entries as active"
    
    def make_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} entries marked as inactive.')
    make_inactive.short_description = "Mark selected entries as inactive"
    
    def mark_as_exam(self, request, queryset):
        updated = queryset.update(is_exam=True)
        self.message_user(request, f'{updated} entries marked as exam.')
    mark_as_exam.short_description = "Mark selected entries as exam"
    
    def mark_as_class(self, request, queryset):
        updated = queryset.update(is_exam=False)
        self.message_user(request, f'{updated} entries marked as regular class.')
    mark_as_class.short_description = "Mark selected entries as regular class"


class TimetableGenerationRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'teacher', 'section', 'batch', 'semester', 'status', 'created_at', 'completed_at']
    list_filter = ['status', 'batch', 'semester', 'created_at']
    search_fields = ['teacher__first_name', 'teacher__last_name', 'section__name', 'batch__name']
    list_per_page = 20
    readonly_fields = ['created_at', 'completed_at']
    autocomplete_fields = ['teacher', 'section', 'batch', 'semester']
    
    fieldsets = (
        ('Request Information', {
            'fields': ('teacher', 'section', 'batch', 'semester')
        }),
        ('Status', {
            'fields': ('status', 'error_message')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['retry_failed_requests']
    
    def retry_failed_requests(self, request, queryset):
        updated = queryset.filter(status='failed').update(status='pending')
        self.message_user(request, f'{updated} failed requests marked for retry.')
    retry_failed_requests.short_description = "Retry selected failed requests"


class ExamTimetableAdmin(admin.ModelAdmin):
    list_display = ['subject', 'teacher', 'section', 'exam_type', 'exam_date', 'start_time', 'end_time', 'classroom', 'total_marks', 'is_active']
    list_filter = ['exam_type', 'exam_date', 'batch', 'semester', 'is_active']
    search_fields = [
        'subject__code', 
        'subject__name', 
        'teacher__first_name', 
        'teacher__last_name',
        'section__name'
    ]
    list_per_page = 25
    date_hierarchy = 'exam_date'
    autocomplete_fields = ['teacher', 'subject', 'section', 'batch', 'semester', 'classroom']
    
    fieldsets = (
        ('Exam Information', {
            'fields': ('subject', 'exam_type', 'total_marks', 'duration_minutes')
        }),
        ('Schedule Information', {
            'fields': ('exam_date', 'start_time', 'end_time', 'classroom')
        }),
        ('Class Information', {
            'fields': ('section', 'batch', 'semester')
        }),
        ('Teacher Information', {
            'fields': ('teacher',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )
    
    actions = ['make_active', 'make_inactive']
    
    def make_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} exam entries marked as active.')
    make_active.short_description = "Mark selected exams as active"
    
    def make_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} exam entries marked as inactive.')
    make_inactive.short_description = "Mark selected exams as inactive"

# timetables/admin.py - Updated LaboratoryAdmin

from django.contrib import admin
from django.utils.html import format_html
from .models import Laboratory

class LaboratoryAdmin(admin.ModelAdmin):
    list_display = ['lab_code', 'lab_name', 'building', 'computer_count', 'primary_batch', 'primary_section', 'primary_semester', 'facilities_badges', 'is_active']
    list_filter = ['has_projector', 'has_ac', 'has_wifi', 'is_active', 'primary_discipline', 'primary_batch', 'primary_semester']
    search_fields = ['lab_code', 'lab_name', 'building', 'primary_section__name', 'primary_batch__name']
    list_editable = ['is_active']
    list_per_page = 20
    filter_horizontal = ['batches', 'sections', 'semesters', 'disciplines']
    autocomplete_fields = ['primary_batch', 'primary_section', 'primary_semester', 'primary_discipline']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('lab_code', 'lab_name', 'building', 'floor', 'capacity')
        }),
        ('Computer Details', {
            'fields': ('computer_count', 'computer_config', 'operating_system')
        }),
        ('Software', {
            'fields': ('software_installed',),
            'classes': ('collapse',)
        }),
        ('Facilities', {
            'fields': ('has_projector', 'has_smartboard', 'has_ac', 'has_generator', 'has_wifi', 'has_printer', 'has_whiteboard')
        }),
        ('Network Details', {
            'fields': ('internet_speed', 'network_type'),
            'classes': ('collapse',)
        }),
        ('Associations (All Batches, Sections, Semesters)', {
            'fields': ('batches', 'sections', 'semesters', 'disciplines'),
            'classes': ('collapse',),
            'description': 'Select all batches, sections, and semesters that can use this lab'
        }),
        ('Primary Assignment', {
            'fields': ('primary_batch', 'primary_section', 'primary_semester', 'primary_discipline'),
            'classes': ('collapse',),
            'description': 'Primary assignment for this lab'
        }),
        ('Maintenance', {
            'fields': ('is_active', 'last_maintenance', 'next_maintenance'),
            'classes': ('collapse',)
        }),
    )
    
    def facilities_badges(self, obj):
        facilities = obj.facilities_list
        if facilities:
            return ' '.join(facilities)
        return '-'
    facilities_badges.short_description = 'Facilities'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('primary_batch', 'primary_section', 'primary_semester', 'primary_discipline')

admin.site.register(Laboratory, LaboratoryAdmin)
# Register all models
admin.site.register(TimeSlot, TimeSlotAdmin)
admin.site.register(TeacherAvailability, TeacherAvailabilityAdmin)
admin.site.register(TimetableEntry, TimetableEntryAdmin)
admin.site.register(TimetableGenerationRequest, TimetableGenerationRequestAdmin)
admin.site.register(ExamTimetable, ExamTimetableAdmin)