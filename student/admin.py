from django.contrib import admin
from .models import Parent, Student
from Academic.models import Discipline, Batch, Semester, Section

# Inline for Parent (optional - if you want to show parent in student admin)
class ParentInline(admin.StackedInline):
    model = Parent
    extra = 0
    can_delete = False

@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = ('father_name', 'mother_name', 'father_email', 'father_contact')
    search_fields = ('father_name', 'mother_name', 'father_email')
    list_filter = ('father_name',)

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = (
        'student_id', 
        'first_name', 
        'last_name', 
        'email', 
        'batch', 
        'semester', 
        'section', 
        'discipline',
        'gender'
    )
    list_filter = (
        'gender', 
        'batch', 
        'semester', 
        'section', 
        'discipline',
        'batch__discipline__program'
    )
    search_fields = (
        'student_id', 
        'first_name', 
        'last_name', 
        'email', 
        'admission_number',
        'contact_number'
    )
    autocomplete_fields = ['batch', 'semester', 'section', 'discipline', 'user', 'parent']
    readonly_fields = ('student_id', 'admission_number')
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'user',
                'student_id', 
                'admission_number',
                'first_name', 
                'last_name',
                'gender',
                'dob',
                'email',
                'contact_number',
                'image'
            )
        }),
        ('Academic Information', {
            'fields': (
                'discipline',
                'batch',
                'semester',
                'section',
            )
        }),
        ('Parent & Address Information', {
            'fields': (
                'parent',
                'address',
            ),
            'classes': ('collapse',)
        }),
    )
    
    # If you want to show parent inline in student admin (optional)
    # inlines = [ParentInline]
    
    def get_queryset(self, request):
        # Optimize database queries
        return super().get_queryset(request).select_related(
            'batch', 
            'semester', 
            'section', 
            'discipline',
            'parent',
            'user'
        )