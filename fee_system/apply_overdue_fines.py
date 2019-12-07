# fee_system/management/commands/apply_overdue_fines.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
from fee_system.models import UploadFee

class Command(BaseCommand):
    help = 'Apply 5000 fine to all overdue fees'

    def handle(self, *args, **kwargs):
        today = timezone.now().date()
        updated_count = 0
        
        # Get all unpaid fees with due dates in the past
        overdue_fees = UploadFee.objects.filter(
            is_fully_paid=False,
            due_date__lt=today
        ).exclude(fine=Decimal('5000.00'))
        
        for fee in overdue_fees:
            fee.fine = Decimal('5000.00')
            fee.is_overdue = True
            fee.save()
            updated_count += 1
            
            self.stdout.write(
                f"Applied 5000 fine to {fee.student.first_name} "
                f"{fee.student.last_name} - Semester {fee.semester.number}"
            )
        
        # Reset fines for fees that are no longer overdue or are paid
        # Remove fine for paid fees
        paid_fees_with_fine = UploadFee.objects.filter(
            is_fully_paid=True,
            fine__gt=Decimal('0')
        )
        
        for fee in paid_fees_with_fine:
            fee.fine = Decimal('0.00')
            fee.is_overdue = False
            fee.save()
            updated_count += 1
            
            self.stdout.write(
                f"Reset fine to 0 for {fee.student.first_name} "
                f"{fee.student.last_name} - Fee is fully paid"
            )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully updated {updated_count} fees')
        )