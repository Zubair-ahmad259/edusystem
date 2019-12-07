from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from student.models import Batch, Semester, Section, Student, Discipline
from decimal import Decimal


class UploadFee(models.Model):
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE)
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE)  # Current semester only
    section = models.ForeignKey(Section, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    discipline = models.ForeignKey(Discipline, on_delete=models.CASCADE)
    due_date = models.DateField()
    
    # Fee fields
    amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        default=0.00,
        verbose_name="Tuition Fee"
    )
    fine = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        verbose_name="Late Fine"
    )
    upload_date = models.DateField(auto_now_add=True)
    
    # Payment status
    is_fully_paid = models.BooleanField(default=False)
    paid_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Amount Paid"
    )
    remaining_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Balance Due"
    )
    
    # Status tracking
    is_overdue = models.BooleanField(default=False)
    grace_period = models.PositiveIntegerField(default=5, help_text="Grace period in days")
    
    class Meta:
        ordering = ['-due_date']
        unique_together = ('student', 'semester')
        verbose_name = "Student Fee"
        verbose_name_plural = "Student Fees"

    def save(self, *args, **kwargs):
        """Calculate remaining amount and check overdue status"""
        from django.utils import timezone
        
        # Ensure Decimal values
        if not isinstance(self.paid_amount, Decimal):
            self.paid_amount = Decimal(str(self.paid_amount))
        if not isinstance(self.amount, Decimal):
            self.amount = Decimal(str(self.amount))
        if not isinstance(self.fine, Decimal):
            self.fine = Decimal(str(self.fine))
        
        # Calculate remaining amount
        self.remaining_amount = self.total_fee() - self.paid_amount
        
        # Check if fully paid
        self.is_fully_paid = self.remaining_amount <= Decimal('0.00')
        
        # Check if overdue
        today = timezone.now().date()
        if self.due_date and not self.is_fully_paid:
            self.is_overdue = today > self.due_date
        else:
            self.is_overdue = False
        
        super().save(*args, **kwargs)

    def total_fee(self):
        """Return fee + fine"""
        return self.amount + self.fine

    def get_status_display(self):
        """Get human-readable status"""
        if self.is_fully_paid:
            return "Paid"
        elif self.is_overdue:
            return "Overdue"
        elif self.due_date:
            return "Pending"
        return "Unknown"

    def get_status_color(self):
        """Get Bootstrap color class for status"""
        if self.is_fully_paid:
            return "success"
        elif self.is_overdue:
            return "danger"
        elif self.due_date:
            return "warning"
        return "secondary"
    

    def __str__(self):
        return f"{self.student.first_name} - {self.semester.number} - {self.total_fee()}"
    
class ClearFee(models.Model):
    PAYMENT_METHODS = [
        ('Cash', 'Cash'),
        ('Bank Transfer', 'Bank Transfer'),
        ('Online', 'Online Payment'),
    ]
    COLLECTOR_NAMES = [
        ('name1', 'name1'),
        ('name2', 'name2'),
        ('name3', 'name3'),
    ]

    # Changed from OneToOneField to ForeignKey
    upload_fee = models.ForeignKey(
        UploadFee,
        on_delete=models.CASCADE,
        related_name="clear_records"  # Changed to plural
    )
    receipt_number = models.CharField(max_length=50, blank=True)  # Made blank=True
    cleared_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='Cash')
    collector_name = models.CharField(max_length=50, choices=COLLECTOR_NAMES, default=None)  
    cleared_date = models.DateField(auto_now_add=True)
    remarks = models.TextField(blank=True, null=True)
    
    # Add installment number for tracking multiple payments
    installment_number = models.PositiveIntegerField(
        default=1,
        help_text="Installment number for this payment"
    )

    class Meta:
        ordering = ['cleared_date']
        # Allow multiple receipts for the same upload_fee but different installments
        unique_together = ('upload_fee', 'installment_number')

    def save(self, *args, **kwargs):
        """Update parent UploadFee when payment is saved"""
        is_new = self.pk is None
        
        # Ensure cleared_amount is Decimal
        if not isinstance(self.cleared_amount, Decimal):
            self.cleared_amount = Decimal(str(self.cleared_amount))
        
        # If this is a new payment, calculate the next installment number
        if is_new:
            # Get the highest installment number for this upload_fee
            last_payment = ClearFee.objects.filter(
                upload_fee=self.upload_fee
            ).order_by('-installment_number').first()
            
            if last_payment:
                self.installment_number = last_payment.installment_number + 1
            else:
                self.installment_number = 1
        
        # Generate receipt number if not provided
        if is_new and not self.receipt_number:
            self.receipt_number = f"RCPT-{self.upload_fee.student.student_id}-{self.installment_number}"
        
        super().save(*args, **kwargs)
        
        # Update parent UploadFee's paid amount
        if is_new:
            upload_fee = self.upload_fee
            # Get all payments for this upload_fee
            all_payments = ClearFee.objects.filter(upload_fee=upload_fee)
            total_paid = sum(p.cleared_amount for p in all_payments)
            
            # Convert to Decimal if needed
            if not isinstance(total_paid, Decimal):
                total_paid = Decimal(str(total_paid))
            
            upload_fee.paid_amount = total_paid
            upload_fee.save()

    def delete(self, *args, **kwargs):
        """Update parent UploadFee when payment is deleted"""
        upload_fee = self.upload_fee
        
        super().delete(*args, **kwargs)
        
        # Recalculate paid amount
        all_payments = ClearFee.objects.filter(upload_fee=upload_fee)
        total_paid = sum(p.cleared_amount for p in all_payments)
        
        # Convert to Decimal if needed
        if not isinstance(total_paid, Decimal):
            total_paid = Decimal(str(total_paid))
        
        upload_fee.paid_amount = total_paid
        upload_fee.save()

    def __str__(self):
        return f"Receipt {self.receipt_number} - {self.upload_fee.student} - Installment {self.installment_number}"