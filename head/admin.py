from django.contrib import admin
from .models import AdminProfile

@admin.register(AdminProfile)
class AdminProfileAdmin(admin.ModelAdmin):
    list_display = (
        'first_name',
        'last_name',
        'father_name',
        'email',
        'contact_number',
        'discipline',
        'role',
        'created_at',
    )
    list_filter = ('role', 'discipline')
    search_fields = ('first_name', 'last_name', 'father_name', 'email')
    ordering = ('first_name',)
    readonly_fields = ('created_at',)

    fieldsets = (
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'father_name', 'email', 'contact_number', 'address')
        }),
        ('Academic Information', {
            'fields': ('discipline', 'role')
        }),
        ('System Information', {
            'fields': ('user', 'created_at')
        }),
    )
