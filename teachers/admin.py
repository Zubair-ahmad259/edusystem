from django.contrib import admin
from django.utils.html import format_html
from .models import Teacher

@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    # Fields to display in the admin list view
    list_display = (
        'full_name',
        'teacher_id',
        'gender',
        'email',
        'mobile_number',
        'field',
        'is_active',
        'teacher_image_preview',
    )

    # Clickable fields for easy editing
    list_display_links = ('full_name', 'teacher_id')

    # Filter options (sidebar)
    list_filter = ('gender', 'field', 'is_active', 'joining_date')

    # Search functionality
    search_fields = ('first_name', 'last_name', 'teacher_id', 'email')

    # Fields to edit directly from the list view
    list_editable = ('is_active',)

    # Pagination
    list_per_page = 20

    # Preview image in admin list
    def teacher_image_preview(self, obj):
        if obj.teacher_image:
            return format_html(
                '<img src="{}" style="max-height: 50px; max-width: 50px;" />',
                obj.teacher_image.url
            )
        return "No Image"
    teacher_image_preview.short_description = 'Image Preview'

    # Custom method to display full name
    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    full_name.short_description = 'Full Name'

    # Customize the add/edit form layout
    fieldsets = (
        ('Personal Info', {
            'fields': (
                ('first_name', 'last_name', 'father_name'),
                ('gender', 'date_of_birth'),
                ('teacher_image', 'teacher_image_preview'),
            ),
        }),
        ('Professional Info', {
            'fields': (
                'teacher_id',
                'field',
                'experience',
                'salary',
                'joining_date',
            ),
        }),
        ('Contact Info', {
            'fields': (
                'email',
                'mobile_number',
                'religion',
            ),
        }),
        ('Status', {
            'fields': ('is_active',),
        }),
    )

    # Make image preview read-only
    readonly_fields = ('teacher_image_preview',)