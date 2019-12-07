# admin.py
from django.contrib import admin
from django import forms
from .models import Subject, SubjectAssign
from django.http import HttpResponse
import csv


class SubjectAdminForm(forms.ModelForm):
    prerequisites = forms.ModelMultipleChoiceField(
        queryset=Subject.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Select prerequisite subjects"
    )
    
    class Meta:
        model = Subject
        fields = '__all__'


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    form = SubjectAdminForm
    list_display = ('code', 'name', 'subject_type', 'credit_hours', 'prerequisite_count', 'is_active', 'created_at')
    list_filter = ('subject_type', 'is_active')
    search_fields = ('code', 'name', 'description')
    filter_horizontal = ('prerequisites',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('code', 'name', 'subject_type')
        }),
        ('Academic Details', {
            'fields': ('credit_hours',)
        }),
        ('Prerequisites', {
            'fields': ('prerequisites',),
        }),
        ('Additional Information', {
            'fields': ('description',),
        }),
        ('Status', {
            'fields': ('is_active', 'created_at', 'updated_at')
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    def prerequisite_count(self, obj):
        return obj.prerequisites.count()
    prerequisite_count.short_description = 'Prerequisites'
    
    actions = ['export_as_csv']
    
    def export_as_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=subjects.csv'
        writer = csv.writer(response)
        
        writer.writerow(['Code', 'Name', 'Subject Type', 'Credit Hours', 'Prerequisites', 'Description', 'Active'])
        
        for obj in queryset:
            prereqs = ", ".join([p.code for p in obj.prerequisites.all()])
            writer.writerow([
                obj.code,
                obj.name,
                obj.get_subject_type_display(),
                obj.credit_hours,
                prereqs,
                obj.description or '',
                'Yes' if obj.is_active else 'No'
            ])
        
        return response
    export_as_csv.short_description = "Export as CSV"


@admin.register(SubjectAssign)
class SubjectAssignAdmin(admin.ModelAdmin):
    list_display = ('subject', 'teacher', 'batch', 'semester', 'get_sections', 'discipline', 'assigned_date', 'is_active')
    list_filter = ('batch', 'semester', 'discipline', 'is_active')
    search_fields = ('subject__code', 'subject__name', 'teacher__first_name', 'teacher__last_name')
    filter_horizontal = ('sections',)
    
    fieldsets = (
        ('Assignment Details', {
            'fields': ('teacher', 'subject', 'batch', 'semester', 'sections', 'discipline')
        }),
        ('Status', {
            'fields': ('is_active', 'assigned_date')
        }),
    )
    
    readonly_fields = ('assigned_date',)
    
    def get_sections(self, obj):
        return ", ".join([s.name for s in obj.sections.all()])
    get_sections.short_description = 'Sections'
    
    actions = ['export_assignments_csv']
    
    def export_assignments_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=subject_assignments.csv'
        
        writer = csv.writer(response)
        writer.writerow(['Subject Code', 'Subject Name', 'Teacher', 'Batch', 'Semester', 'Sections', 'Discipline', 'Status'])
        
        for obj in queryset:
            sections = ", ".join([s.name for s in obj.sections.all()])
            writer.writerow([
                obj.subject.code,
                obj.subject.name,
                f"{obj.teacher.first_name} {obj.teacher.last_name}",
                obj.batch.name,
                f"Semester {obj.semester.number}",
                sections,
                obj.discipline.field if obj.discipline else '',
                'Active' if obj.is_active else 'Inactive'
            ])
        
        return response
    export_assignments_csv.short_description = "Export as CSV"