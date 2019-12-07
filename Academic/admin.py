from django.contrib import admin
from .models import Discipline, Batch, Semester, Section, Department

@admin.register(Discipline)
class DisciplineAdmin(admin.ModelAdmin):
    list_display = ('program', 'field', 'get_full_name')
    list_filter = ('program', 'field')
    search_fields = ('program', 'field')
    
    def get_full_name(self, obj):
        return f"{obj.program} in {obj.field}"
    get_full_name.short_description = 'Discipline'

@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_session', 'end_session', 'discipline')
    list_filter = ('discipline', 'start_session')
    search_fields = ('name', 'discipline__field', 'discipline__program')
    autocomplete_fields = ['discipline']

@admin.register(Semester)
class SemesterAdmin(admin.ModelAdmin):
    list_display = ('number',)
    list_filter = ('number',)
    search_fields = ('number',)

@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'batch', 'discipline')
    list_filter = ('batch', 'discipline')
    search_fields = ('name', 'batch__name', 'discipline__field')
    autocomplete_fields = ['batch', 'discipline']

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)