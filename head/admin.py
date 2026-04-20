from django.contrib import admin
from .models import AdminProfile


@admin.register(AdminProfile)
class AdminProfileAdmin(admin.ModelAdmin):
    list_display = ('employee_id', 'first_name', 'last_name', 'email', 'role', 'discipline', 'contact_number', 'is_active', 'created_at')
    list_filter = ('role', 'discipline', 'is_active')
    search_fields = ('first_name', 'last_name', 'email', 'employee_id', 'contact_number')
    list_per_page = 25
    ordering = ('-created_at',)