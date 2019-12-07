# home_auth/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils import timezone
from django.contrib import messages
from django.utils.crypto import get_random_string
from django.db import connection
from .models import CustomUser, PasswordResetRequest


class CustomUserAdmin(UserAdmin):
    model = CustomUser
    
    list_display = (
        'username', 
        'email', 
        'first_name', 
        'last_name', 
        'is_authorized',
        'get_role',
        'password_generated',
        'get_password_deadline',
        'is_active',
        'date_joined'
    )
    
    list_filter = (
        'is_authorized',
        'is_student',
        'is_teacher',
        'is_admin',
        'password_generated',
        'is_active',
        'date_joined'
    )
    
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    date_hierarchy = 'date_joined'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('username', 'email', 'password', 'first_name', 'last_name')
        }),
        ('Authorization Status', {
            'fields': ('is_authorized', 'login_token')
        }),
        ('User Roles', {
            'fields': ('is_student', 'is_teacher', 'is_admin'),
        }),
        ('Password Management', {
            'fields': ('password_generated', 'temp_password', 'password_change_deadline'),
            'classes': ('collapse',)
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('Important Dates', {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'first_name', 'last_name', 
                      'is_student', 'is_teacher', 'is_admin'),
        }),
    )
    
    readonly_fields = ('date_joined', 'last_login', 'login_token', 'temp_password')
    
    actions = ['mark_as_authorized', 'reset_password', 'generate_new_password', 
               'force_delete_users', 'deactivate_users']
    
    list_per_page = 25
    
    def get_role(self, obj):
        if obj.is_admin:
            return "Admin"
        elif obj.is_teacher:
            return "Teacher"
        elif obj.is_student:
            return "Student"
        else:
            return "No Role"
    get_role.short_description = 'Role'
    get_role.admin_order_field = 'is_admin'
    
    def get_password_deadline(self, obj):
        if not obj.password_change_deadline:
            return "No deadline"
        
        if obj.password_change_deadline > timezone.now():
            time_left = obj.password_change_deadline - timezone.now()
            hours = int(time_left.total_seconds() // 3600)
            minutes = int((time_left.total_seconds() % 3600) // 60)
            return f"{hours}h {minutes}m left"
        else:
            return "Expired"
    get_password_deadline.short_description = 'Password Deadline'
    
    def reset_password(self, request, queryset):
        for user in queryset:
            new_password = get_random_string(length=10)
            user.set_password(new_password)
            user.temp_password = new_password
            user.password_generated = True
            user.password_change_deadline = timezone.now() + timezone.timedelta(hours=24)
            user.save()
            
            self.message_user(
                request,
                f'Password reset for {user.username}. New password: {new_password}',
                level=messages.WARNING
            )
    reset_password.short_description = "Reset password for selected users"
    
    def mark_as_authorized(self, request, queryset):
        updated = queryset.update(is_authorized=True)
        self.message_user(
            request,
            f'{updated} user(s) marked as authorized.',
            level=messages.SUCCESS
        )
    mark_as_authorized.short_description = "Mark selected users as authorized"
    
    def generate_new_password(self, request, queryset):
        count = 0
        for user in queryset:
            new_password = get_random_string(length=10)
            user.set_password(new_password)
            user.temp_password = new_password
            user.password_generated = True
            user.password_change_deadline = timezone.now() + timezone.timedelta(hours=24)
            user.save()
            count += 1
            
        self.message_user(
            request,
            f'Generated new passwords for {count} user(s).',
            level=messages.SUCCESS
        )
    generate_new_password.short_description = "Generate new temporary passwords"
    
    def deactivate_users(self, request, queryset):
        """Deactivate users instead of deleting"""
        updated = queryset.update(is_active=False, is_authorized=False)
        self.message_user(
            request,
            f'{updated} user(s) deactivated successfully.',
            level=messages.SUCCESS
        )
    deactivate_users.short_description = "Deactivate selected users"
    
    def force_delete_users(self, request, queryset):
        """Force delete users by disabling foreign key checks (SQLite only)"""
        deleted_count = 0
        failed_count = 0
        
        for user in queryset:
            try:
                # For SQLite: disable foreign key checks temporarily
                with connection.cursor() as cursor:
                    cursor.execute("PRAGMA foreign_keys = OFF")
                
                # Delete related PasswordResetRequest records
                PasswordResetRequest.objects.filter(user=user).delete()
                
                # Try to delete the user
                user.delete()
                deleted_count += 1
                
            except Exception as e:
                failed_count += 1
                self.message_user(
                    request,
                    f'Could not delete {user.username}: {str(e)}',
                    level=messages.ERROR
                )
            finally:
                # Re-enable foreign key checks
                with connection.cursor() as cursor:
                    cursor.execute("PRAGMA foreign_keys = ON")
        
        if deleted_count > 0:
            self.message_user(
                request,
                f'Successfully deleted {deleted_count} user(s).',
                level=messages.SUCCESS
            )
        if failed_count > 0:
            self.message_user(
                request,
                f'Failed to delete {failed_count} user(s).',
                level=messages.WARNING
            )
    force_delete_users.short_description = "Force delete selected users (SQLite)"
    
    def save_model(self, request, obj, form, change):
        if not change and not obj.password_generated:
            random_password = get_random_string(length=10)
            obj.set_password(random_password)
            obj.password_generated = True
            obj.temp_password = random_password
            obj.password_change_deadline = timezone.now() + timezone.timedelta(hours=24)
            
            super().save_model(request, obj, form, change)
            
            self.message_user(
                request,
                f'User created successfully. Temporary password: {random_password}',
                level=messages.INFO
            )
        else:
            super().save_model(request, obj, form, change)
    
    def delete_model(self, request, obj):
        """Override single object deletion"""
        try:
            # Delete related PasswordResetRequest records
            PasswordResetRequest.objects.filter(user=obj).delete()
            obj.delete()
        except Exception as e:
            self.message_user(
                request,
                f'Could not delete {obj.username}: {str(e)}',
                level=messages.ERROR
            )
    
    def delete_queryset(self, request, queryset):
        """Override bulk deletion"""
        for obj in queryset:
            try:
                PasswordResetRequest.objects.filter(user=obj).delete()
                obj.delete()
            except Exception as e:
                self.message_user(
                    request,
                    f'Could not delete {obj.username}: {str(e)}',
                    level=messages.ERROR
                )


@admin.register(PasswordResetRequest)
class PasswordResetRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'email', 'created_at', 'token_valid')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'user__email', 'email', 'token')
    readonly_fields = ('token', 'created_at', 'user', 'email')
    date_hierarchy = 'created_at'
    
    def token_valid(self, obj):
        if obj.is_valid():
            return "Valid"
        else:
            return "Expired"
    token_valid.short_description = 'Token Status'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


# Register the models
admin.site.register(CustomUser, CustomUserAdmin)