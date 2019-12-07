# token_app/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import ExamToken

class ExamTokenAdmin(admin.ModelAdmin):
    list_display = ['token_number', 'student', 'colored_status', 'issue_date', 'valid_until']
    list_filter = ['status', 'semester', 'batch']
    search_fields = ['token_number', 'student__student_id', 'student__first_name']
    readonly_fields = ['token_number', 'created_at', 'updated_at']
    raw_id_fields = ['student', 'issued_by', 'verified_by']
    filter_horizontal = ['eligible_subjects']
    list_per_page = 25

    def colored_status(self, obj):
        colors = {
            'generated': 'gray',
            'printed': 'blue',
            'used': 'green',
            'expired': 'red',
            'cancelled': 'orange',
            'verified': 'purple',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color, obj.get_status_display()
        )
    colored_status.short_description = 'Status'

admin.site.register(ExamToken, ExamTokenAdmin)