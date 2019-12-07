# attendance/admin.py
from django.contrib import admin
from .models import (
    Attendance, 
    DailyAttendanceSummary, 
    MonthlyAttendanceReport, 
    AttendanceConfiguration, 
    AttendanceNotification
)


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = [
        'student', 
        'subject', 
        'date', 
        'status', 
        'batch', 
        'semester', 
        'section',
        'teacher',
        'created_at'
    ]
    
    list_filter = [
        'date', 
        'status', 
        'batch', 
        'semester', 
        'section',
        'subject'
    ]
    
    search_fields = [
        'student__student_id', 
        'student__first_name', 
        'student__last_name',
        'subject__code',
        'subject__name'
    ]
    
    date_hierarchy = 'date'


@admin.register(DailyAttendanceSummary)
class DailyAttendanceSummaryAdmin(admin.ModelAdmin):
    list_display = [
        'date', 
        'batch', 
        'semester', 
        'section', 
        'subject',
        'total_students',
        'present_count',
        'absent_count',
        'attendance_percentage',
        'created_at'
    ]
    
    list_filter = [
        'date', 
        'batch', 
        'semester', 
        'section',
        'subject'
    ]
    
    search_fields = [
        'batch__name',
        'section__name',
        'subject__code',
        'subject__name'
    ]
    
    date_hierarchy = 'date'


@admin.register(MonthlyAttendanceReport)
class MonthlyAttendanceReportAdmin(admin.ModelAdmin):
    list_display = [
        'student', 
        'month', 
        'year', 
        'batch', 
        'semester',
        'section',
        'total_days',
        'present_days',
        'absent_days',
        'attendance_percentage',
        'created_at'
    ]
    
    list_filter = [
        'month', 
        'year', 
        'batch', 
        'semester',
        'section'
    ]
    
    search_fields = [
        'student__student_id', 
        'student__first_name', 
        'student__last_name'
    ]


@admin.register(AttendanceConfiguration)
class AttendanceConfigurationAdmin(admin.ModelAdmin):
    list_display = [
        'name', 
        'minimum_attendance_percentage',
        'auto_calculate_summary',
        'send_notifications',
        'notification_threshold',
        'created_at',
        'updated_at'
    ]


@admin.register(AttendanceNotification)
class AttendanceNotificationAdmin(admin.ModelAdmin):
    list_display = [
        'student', 
        'teacher',
        'notification_type',
        'title',
        'is_read',
        'created_at'
    ]
    
    list_filter = [
        'notification_type',
        'is_read',
        'created_at'
    ]
    
    search_fields = [
        'student__student_id', 
        'student__first_name', 
        'student__last_name',
        'teacher__teacher_id',
        'teacher__first_name',
        'teacher__last_name',
        'title',
        'message'
    ]
    
    date_hierarchy = 'created_at'