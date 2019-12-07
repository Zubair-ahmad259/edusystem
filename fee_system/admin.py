from django.contrib import admin
from .models import UploadFee, ClearFee
from django.contrib import admin
from .models import UploadFee

from django.contrib import admin
from .models import UploadFee




@admin.register(UploadFee)
class UploadFeeAdmin(admin.ModelAdmin):
    # Show these fields in list
    list_display = [
        'student',
        'batch',
        'semester',
        'amount',
        'fine',
        'total_fee_display',
        'paid_amount',
        'remaining_amount',
        'due_date',
        'status_display',
        'is_overdue'
    ]
    
    # Filter by these fields
    list_filter = [
        'batch',
        'semester',
        'section',
        'discipline',
        'is_fully_paid',
        'is_overdue'
    ]
    
    # Search by student info
    search_fields = [
        'student__name',
        'student__student_id',
        'student__roll_number',
        'semester__name'
    ]
    
    # Group fields in edit form
    fieldsets = (
        ('Student Information', {
            'fields': ('student', 'batch', 'semester', 'section', 'discipline')
        }),
        ('Fee Information', {
            'fields': ('amount', 'fine', 'due_date', 'grace_period')
        }),
        ('Payment Status', {
            'fields': ('paid_amount', 'remaining_amount', 'is_fully_paid', 'is_overdue')
        }),
    )
    
    # Read-only fields
    readonly_fields = ['remaining_amount', 'is_fully_paid', 'is_overdue', 'upload_date']
    
    # Custom display methods
    def total_fee_display(self, obj):
        return f"Rs. {obj.total_fee():,.2f}"
    total_fee_display.short_description = 'Total Fee'
    total_fee_display.admin_order_field = 'amount'
    
    def status_display(self, obj):
        if obj.is_fully_paid:
            return "✅ Paid"
        elif obj.is_overdue:
            return "❌ Overdue"
        else:
            return "⏳ Pending"
    status_display.short_description = 'Status'
    
    # Date hierarchy for easy navigation
    date_hierarchy = 'due_date'
    
    # Follow the model's ordering
    ordering = ['-due_date']  # Same as model's Meta.ordering
@admin.register(ClearFee)
class ClearFeeAdmin(admin.ModelAdmin):
    list_display = ('receipt_number', 'upload_fee', 'cleared_amount', 'payment_method', 'cleared_date')
    list_filter = ('payment_method', 'collector_name')
    search_fields = ('receipt_number', 'upload_fee__student__name')