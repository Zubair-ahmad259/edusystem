from django.contrib import admin
from .models import Cases


@admin.register(Cases)
class CasesAdmin(admin.ModelAdmin):
    list_display = ('student', 'case_type', 'teacher', 'subject', 'batch', 'semester', 'section', 'Disciplines','created_at','fine','status')
    list_filter = ('case_type', 'batch', 'semester', 'section')
    search_fields = ('student__first_name', 'student__last_name', 'teacher__first_name', 'teacher__last_name', 'subject__name')
    ordering = ('-created_at',)
