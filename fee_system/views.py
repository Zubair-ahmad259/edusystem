from urllib import request
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from .models import ClearFee, UploadFee
from student.models import Student, Batch, Semester, Section, Discipline
from django.utils import timezone
from datetime import datetime, date,timedelta
from decimal import Decimal, InvalidOperation
from django.db.models import Sum
import json
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from .models import UploadFee, Batch, Semester, Section, Discipline, Student
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from datetime import date, datetime, timedelta
from decimal import Decimal
from .models import UploadFee, Student, Batch, Semester, Section, Discipline
from decimal import Decimal

import pandas as pd
from django.http import HttpResponse
from django.utils import timezone
import io
from decimal import Decimal
from datetime import date

# Helper function to check permissions
def can_edit_fee(user):
    """Check if user has permission to edit fees"""
    # Superusers and staff can always edit
    if user.is_superuser or user.is_staff:
        return True
    
    # Check for specific permission
    if user.has_perm('fees.change_uploadfee'):
        return True
    
    # Check for group membership (if using groups)
    if user.groups.filter(name__in=['Fee Managers', 'Accountants', 'Administrators']).exists():
        return True
    
    return False


def can_delete_fee(user):
    """Check if user has permission to delete fees"""
    # Superusers and staff can always delete
    if user.is_superuser or user.is_staff:
        return True
    
    # Check for specific permission
    if user.has_perm('fees.delete_uploadfee'):
        return True
    
    # Check for group membership
    if user.groups.filter(name__in=['Fee Managers', 'Administrators']).exists():
        return True
    
    return False



def upload_fee(request):
    # Get all necessary data
    batches = Batch.objects.all().select_related('discipline')
    semesters = Semester.objects.all()
    sections = Section.objects.all()  # Removed select_related that was causing error
    disciplines = Discipline.objects.all()

    students = None
    selected_discipline = None
    selected_batch = None
    selected_section = None
    selected_semester = None
    today = date.today()

    if request.method == "POST":
        # Get form data
        discipline_id = request.POST.get("discipline")
        batch_id = request.POST.get("batch")
        section_id = request.POST.get("section")
        semester_id = request.POST.get("semester")
        amount_default = request.POST.get("amount", "0")
        due_date_str = request.POST.get("due_date")
        grace_period = int(request.POST.get("grace_period", "5"))

        # Convert due date
        if due_date_str:
            due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
        else:
            due_date = today + timedelta(days=30)

        # Store selections for template
        selected_discipline = discipline_id
        selected_batch = batch_id
        selected_section = section_id
        selected_semester = semester_id

        # Handle "Load Students" action
        if "load_students" in request.POST:
            if all([discipline_id, batch_id, section_id, semester_id]):
                try:
                    # REMOVED: is_active filter since Student model doesn't have this field
                    students = Student.objects.filter(
                        discipline_id=discipline_id,
                        batch_id=batch_id,
                        section_id=section_id,
                        semester_id=semester_id
                    ).order_by("student_id")
                    
                    if not students.exists():
                        messages.warning(request, "No students found for the selected criteria")
                    else:
                        messages.info(request, f"Found {students.count()} student(s)")
                        
                except Exception as e:
                    messages.error(request, f"Error loading students: {str(e)}")
            else:
                messages.warning(request, "Please select all fields: Discipline, Batch, Semester, and Section")

        # Handle "Upload Fees" action
        elif "submit_all" in request.POST:
            if not all([discipline_id, batch_id, section_id, semester_id]):
                messages.error(request, "Missing required data. Please reload students.")
                return redirect("upload_fee")

            try:
                # REMOVED: is_active filter
                students = Student.objects.filter(
                    discipline_id=discipline_id,
                    batch_id=batch_id,
                    section_id=section_id,
                    semester_id=semester_id
                )
                
                if not students.exists():
                    messages.error(request, "No students found to upload fees")
                    return redirect("upload_fee")

                success_count = 0
                error_count = 0
                
                with transaction.atomic():
                    for student in students:
                        try:
                            # Get the specific amount for this student or use default
                            base_amount_key = f"base_amount_{student.id}"
                            base_amount = request.POST.get(base_amount_key, amount_default)
                            
                            # Convert to Decimal
                            amount = Decimal(str(base_amount))
                            
                            # Check if fee already exists for this student and semester
                            existing_fee = UploadFee.objects.filter(
                                student=student,
                                semester_id=semester_id
                            ).first()
                            
                            if existing_fee:
                                # Update existing fee
                                existing_fee.amount = amount
                                existing_fee.due_date = due_date
                                existing_fee.grace_period = grace_period
                                existing_fee.save()
                                messages.info(request, f"Updated fee for {student.first_name} {student.last_name}")
                            else:
                                # Create new fee record
                                fee_record = UploadFee.objects.create(
                                    student=student,
                                    semester_id=semester_id,
                                    batch_id=batch_id,
                                    section_id=section_id,
                                    discipline_id=discipline_id,
                                    amount=amount,
                                    fine=Decimal("0.00"),
                                    paid_amount=Decimal("0.00"),
                                    remaining_amount=amount,
                                    due_date=due_date,
                                    grace_period=grace_period,
                                    is_fully_paid=False,
                                    is_overdue=False,
                                    upload_date=today,
                                )
                            
                            success_count += 1
                            
                        except Exception as e:
                            error_count += 1
                            messages.error(request, f"Error uploading fee for {student.first_name} {student.last_name}: {str(e)}")
                            print(f"Error uploading fee for student {student.id}: {e}")
                
                if success_count > 0:
                    messages.success(request, f"Successfully uploaded/updated fees for {success_count} student(s)")
                if error_count > 0:
                    messages.warning(request, f"Failed to upload fees for {error_count} student(s)")
                    
                return redirect("fee_list")
                
            except Exception as e:
                messages.error(request, f"Error uploading fees: {str(e)}")
                return redirect("upload_fee")

    context = {
        "batches": batches,
        "semesters": semesters,
        "sections": sections,
        "disciplines": disciplines,
        "students": students,
        "selected_discipline": selected_discipline,
        "selected_batch": selected_batch,
        "selected_section": selected_section,
        "selected_semester": selected_semester,
        "today": today,
        "default_due_date": (today + timedelta(days=30)).strftime("%Y-%m-%d"),
    }

    return render(request, "fees/upload_fee.html", context)

def edit_fee(request, fee_id):
    """View to edit an existing fee record"""
    
    # Check permissions
    if not request.user.is_authenticated:
        messages.error(request, "Please login to edit fees.")
        return redirect('login')
    
    if not can_edit_fee(request.user):
        messages.error(request, "You don't have permission to edit fees.")
        return redirect('fee_list')
    
    fee = get_object_or_404(UploadFee, id=fee_id)
    
    # Check if fee is already cleared
    if ClearFee.objects.filter(upload_fee=fee).exists():
        messages.warning(request, "Cannot edit a fee that has already been cleared.")
        return redirect('fee_list')
    
    if request.method == "POST":
        try:
            # Get form data
            semester_option = request.POST.get("semester_option")
            amount_str = request.POST.get("amount")
            fine_str = request.POST.get("fine")
            due_date_str = request.POST.get("due_date")
            
            # Convert and validate amount
            try:
                amount = Decimal(amount_str) if amount_str and amount_str.strip() else Decimal('0')
            except (InvalidOperation, ValueError, TypeError):
                messages.error(request, "Invalid amount format. Please enter a valid number.")
                return render(request, "fees/edit_fee.html", {"fee": fee})
            
            # Convert and validate fine
            try:
                fine = Decimal(fine_str) if fine_str and fine_str.strip() else Decimal('0')
            except (InvalidOperation, ValueError, TypeError):
                messages.error(request, "Invalid fine format. Please enter a valid number.")
                return render(request, "fees/edit_fee.html", {"fee": fee})
            
            # Validate due date
            if due_date_str:
                try:
                    due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
                except:
                    due_date = fee.due_date
                    messages.warning(request, "Invalid date format. Using existing due date.")
            else:
                due_date = fee.due_date
            
            # Ensure non-negative values
            if amount < 0:
                amount = Decimal('0')
                messages.warning(request, "Amount cannot be negative. Set to 0.")
            if fine < 0:
                fine = Decimal('0')
                messages.warning(request, "Fine cannot be negative. Set to 0.")
            
            # Check if amount is too large
            if amount > Decimal('1000000'):
                messages.error(request, "Amount is too large. Maximum is 1,000,000.")
                return render(request, "fees/edit_fee.html", {"fee": fee})
            
            # Update the fee record
            fee.semester_option = semester_option
            fee.amount = amount
            fee.fine = fine
            fee.due_date = due_date
            fee.save()
            
            messages.success(request, f"Fee record for {fee.student.name} updated successfully.")
            return redirect('fee_list')
            
        except Exception as e:
            messages.error(request, f"Error updating fee: {str(e)}")
            return render(request, "fees/edit_fee.html", {
                "fee": fee,
                "error": str(e)
            })
    
    # GET request - show edit form
    return render(request, "fees/edit_fee.html", {
        "fee": fee,
        "user_can_delete": can_delete_fee(request.user),
    })


def delete_fee(request, fee_id):
    """View to delete a fee record"""
    
    if not request.user.is_authenticated:
        messages.error(request, "Please login to delete fees.")
        return redirect('login')
    
    if not can_delete_fee(request.user):
        messages.error(request, "You don't have permission to delete fees.")
        return redirect('fee_list')
    
    fee = get_object_or_404(UploadFee, id=fee_id)
    
    # Check if fee is already cleared
    if ClearFee.objects.filter(upload_fee=fee).exists():
        messages.warning(request, "Cannot delete a fee that has already been cleared.")
        return redirect('fee_list')
    
    try:
        student_name = fee.student.name
        fee.delete()
        messages.success(request, f"Fee record for {student_name} deleted successfully.")
    except Exception as e:
        messages.error(request, f"Error deleting fee: {str(e)}")
    
    return redirect('fee_list')


def delete_fee_ajax(request, fee_id):
    """AJAX endpoint for deleting fee records"""
    
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'message': 'Please login to delete fees.',
            'redirect': '/login/'
        }, status=401)
    
    if not can_delete_fee(request.user):
        return JsonResponse({
            'success': False,
            'message': 'You do not have permission to delete fees.',
            'redirect': '/fees/list/'
        }, status=403)
    
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'message': 'Invalid request method.'
        }, status=400)
    
    fee = get_object_or_404(UploadFee, id=fee_id)
    
    # Check if fee is already cleared
    if ClearFee.objects.filter(upload_fee=fee).exists():
        return JsonResponse({
            'success': False,
            'message': 'Cannot delete a fee that has already been cleared.'
        })
    
    try:
        student_name = fee.student.name
        fee_amount = fee.amount
        fee.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Fee record for {student_name} (Rs. {fee_amount}) deleted successfully.',
            'fee_id': fee_id,
            'student_name': student_name
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error deleting fee: {str(e)}'
        }, status=500)


def bulk_delete_fees(request):
    """View to delete multiple fee records at once"""
    
    if not request.user.is_authenticated:
        messages.error(request, "Please login to delete fees.")
        return redirect('login')
    
    if not can_delete_fee(request.user):
        messages.error(request, "You don't have permission to delete fees.")
        return redirect('fee_list')
    
    if request.method != 'POST':
        messages.error(request, "Invalid request method.")
        return redirect('fee_list')
    
    fee_ids = request.POST.getlist('fee_ids[]')
    
    if not fee_ids:
        messages.warning(request, "No fees selected for deletion.")
        return redirect('fee_list')
    
    deleted_count = 0
    error_count = 0
    cleared_count = 0
    
    with transaction.atomic():
        for fee_id in fee_ids:
            try:
                fee = UploadFee.objects.get(id=fee_id)
                
                # Skip if fee is cleared
                if ClearFee.objects.filter(upload_fee=fee).exists():
                    cleared_count += 1
                    continue
                
                fee.delete()
                deleted_count += 1
            except UploadFee.DoesNotExist:
                error_count += 1
            except Exception as e:
                error_count += 1
                print(f"Error deleting fee {fee_id}: {e}")
    
    if deleted_count > 0:
        messages.success(request, f"Successfully deleted {deleted_count} fee record(s).")
    
    if cleared_count > 0:
        messages.warning(request, f"Skipped {cleared_count} fee record(s) that were already cleared.")
    
    if error_count > 0:
        messages.error(request, f"Could not delete {error_count} fee record(s).")
    
    return redirect('fee_list')


def toggle_fee_status(request, fee_id):
    """Toggle fee clearance status"""
    
    if not request.user.is_authenticated:
        messages.error(request, "Please login to modify fees.")
        return redirect('login')
    
    if not can_edit_fee(request.user):
        messages.error(request, "You don't have permission to modify fees.")
        return redirect('fee_list')
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method.'})
    
    fee = get_object_or_404(UploadFee, id=fee_id)
    
    try:
        is_cleared = ClearFee.objects.filter(upload_fee=fee).exists()
        
        if is_cleared:
            # Clear the clearance record
            ClearFee.objects.filter(upload_fee=fee).delete()
            status = "pending"
            message = f"Fee for {fee.student.name} marked as pending."
        else:
            # Create clearance record
            ClearFee.objects.create(
                upload_fee=fee,
                receipt_number=f"AUTO-{fee.id}",
                cleared_amount=fee.amount,
                payment_method="Manual",
                collector_name=request.user.get_full_name() or request.user.username,
                remarks="Status toggled manually"
            )
            status = "cleared"
            message = f"Fee for {fee.student.name} marked as cleared."
        
        return JsonResponse({
            'success': True,
            'message': message,
            'status': status,
            'fee_id': fee_id
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error toggling fee status: {str(e)}'
        }, status=500)


# Helper view to check permissions (for debugging)
def check_permissions(request):
    """Debug view to check user permissions"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'})
    
    permissions = {
        'username': request.user.username,
        'is_superuser': request.user.is_superuser,
        'is_staff': request.user.is_staff,
        'groups': list(request.user.groups.values_list('name', flat=True)),
        'all_permissions': list(request.user.get_all_permissions()),
        'can_edit_fee': can_edit_fee(request.user),
        'can_delete_fee': can_delete_fee(request.user),
        'has_fees.change_uploadfee': request.user.has_perm('fees.change_uploadfee'),
        'has_fees.delete_uploadfee': request.user.has_perm('fees.delete_uploadfee'),
    }
    
    return JsonResponse(permissions)


# Add this to automatically create permissions for testing
def setup_permissions(request):

    """Create test users and permissions (for development only)"""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Superuser required'})
    
    from django.contrib.auth.models import User, Group, Permission
    from django.contrib.contenttypes.models import ContentType
    from .models import UploadFee
    
    # Create groups
    fee_manager_group, created = Group.objects.get_or_create(name='Fee Managers')
    accountant_group, created = Group.objects.get_or_create(name='Accountants')
    
    # Get permissions
    content_type = ContentType.objects.get_for_model(UploadFee)
    
    change_permission = Permission.objects.get(
        codename='change_uploadfee',
        content_type=content_type
    )
    delete_permission = Permission.objects.get(
        codename='delete_uploadfee',
        content_type=content_type
    )
    
    # Add permissions to groups
    fee_manager_group.permissions.add(change_permission, delete_permission)
    accountant_group.permissions.add(change_permission)
    
    # Create test users
    test_users = [
        {'username': 'fee_manager', 'password': 'test123', 'groups': ['Fee Managers']},
        {'username': 'accountant', 'password': 'test123', 'groups': ['Accountants']},
        {'username': 'regular', 'password': 'test123', 'groups': []},
    ]
    
    for user_data in test_users:
        user, created = User.objects.get_or_create(
            username=user_data['username'],
            defaults={'is_staff': True}
        )
        user.set_password(user_data['password'])
        user.save()
        
        for group_name in user_data['groups']:
            group = Group.objects.get(name=group_name)
            user.groups.add(group)
    
    return JsonResponse({
        'message': 'Permissions setup complete',
        'test_users': test_users
    })



def fee_list(request):
    batches = Batch.objects.all()
    semesters = Semester.objects.all()
    disciplines = Discipline.objects.all()

    batch_filter = request.GET.get("batch")
    semester_filter = request.GET.get("semester")
    section_filter = request.GET.get("section")
    discipline_filter = request.GET.get("discipline")

    all_sections = Section.objects.select_related('batch').all()
    all_batches = Batch.objects.select_related('discipline').all()

    fees = UploadFee.objects.select_related(
        "student", "batch", "semester", "section", "discipline"
    )

    if batch_filter:
        fees = fees.filter(batch_id=batch_filter)
    if semester_filter:
        fees = fees.filter(semester_id=semester_filter)
    if section_filter:
        fees = fees.filter(section_id=section_filter)
    if discipline_filter:
        fees = fees.filter(discipline_id=discipline_filter)

    # Calculate totals for cards
    total_fee_all = Decimal('0')
    total_cleared_all = Decimal('0')
    total_pending_all = Decimal('0')
    
    student_fees = {}
    today = date.today()
    
    for fee in fees:
        student_id = fee.student.id
        if student_id not in student_fees:
            student_fees[student_id] = {
                'student': fee.student,
                'batch': fee.batch,
                'semester': fee.semester,
                'section': fee.section,
                'fees': [],
                'total_all': Decimal('0'),
                'total_pending': Decimal('0'),
                'total_cleared': Decimal('0'),
                'discipline': fee.discipline,
            }
        
        # AUTOMATICALLY APPLY 5000 FINE IF OVERDUE
        if fee.due_date and today > fee.due_date and not fee.is_fully_paid:
            # Check if fine needs to be applied
            if fee.fine != Decimal('5000.00'):
                fee.fine = Decimal('5000.00')
                fee.is_overdue = True
                fee.save()
        elif fee.is_fully_paid and fee.fine > Decimal('0'):
            # Reset fine if fully paid
            fee.fine = Decimal('0.00')
            fee.is_overdue = False
            fee.save()
        elif not fee.is_overdue and fee.fine == Decimal('5000.00'):
            # Reset fine if not overdue
            fee.fine = Decimal('0.00')
            fee.save()
        
        # Calculate total fee (including fine)
        fee_total = fee.total_fee()
        paid_amount = fee.paid_amount
        remaining_amount = fee.remaining_amount
        
        # For display in template
        fee.display_total = fee_total
        fee.paid_amount_display = paid_amount
        fee.remaining_amount_display = remaining_amount
        fee.is_cleared = fee.is_fully_paid
        fee.is_overdue = fee.is_overdue
        fee.overdue_fine = fee.fine  # Store fine separately for display
        
        # Add semester number for template
        fee.semester_option = fee.semester.number
        
        student_fees[student_id]['fees'].append(fee)
        
        # Update student totals
        student_fees[student_id]['total_all'] += fee_total
        student_fees[student_id]['total_cleared'] += paid_amount
        student_fees[student_id]['total_pending'] += remaining_amount
        
        # Update overall totals
        total_fee_all += fee_total
        total_cleared_all += paid_amount
        total_pending_all += remaining_amount

    selected_batch_name = ""
    selected_section_name = ""
    selected_discipline_name = ""
    selected_semester_name = ""

    if batch_filter:
        batch = Batch.objects.filter(id=batch_filter).first()
        selected_batch_name = batch.name if batch else ""
    
    if section_filter:
        section = Section.objects.filter(id=section_filter).first()
        selected_section_name = section.name if section else ""
    
    if discipline_filter:
        discipline = Discipline.objects.filter(id=discipline_filter).first()
        selected_discipline_name = f"{discipline.field} ({discipline.program})" if discipline else ""
    
    if semester_filter:
        semester = Semester.objects.filter(id=semester_filter).first()
        selected_semester_name = f"Semester {semester.number}" if semester else ""

    # Check user permissions (you need to define these functions)
    user_can_edit = request.user.is_authenticated and request.user.is_staff  # Example
    user_can_delete = request.user.is_authenticated and request.user.is_staff  # Example

    return render(request, "fees/fee_list.html", {
        "student_fees": student_fees.values(),
        "batches": all_batches,
        "semesters": semesters,
        "sections": all_sections,
        "disciplines": disciplines,
        "selected_batch": batch_filter,
        "selected_semester": semester_filter,
        "selected_section": section_filter,
        "selected_discipline": discipline_filter,
        "selected_batch_name": selected_batch_name,
        "selected_section_name": selected_section_name,
        "selected_discipline_name": selected_discipline_name,
        "selected_semester_name": selected_semester_name,
        "user_can_edit": user_can_edit,
        "user_can_delete": user_can_delete,
        "total_fee_all": total_fee_all,
        "total_cleared_all": total_cleared_all,
        "total_pending_all": total_pending_all,
    })

def clear_fee(request, fee_id):
    fee = get_object_or_404(UploadFee, id=fee_id)
    
    # Calculate total fee correctly - amount + fine
    total_fee_value = fee.amount + fee.fine
    
    # Calculate total already paid
    total_paid = ClearFee.objects.filter(upload_fee=fee).aggregate(
        total=Sum('cleared_amount')
    )['total'] or Decimal('0')
    
    # Calculate remaining amount
    remaining_amount = total_fee_value - total_paid
    
    # If fee is already fully paid
    if remaining_amount <= Decimal('0'):
        messages.info(request, f"Fee is already fully paid. Total paid: PKR {total_paid:.2f}")
        return redirect("fee_list")

    if request.method == "POST":
        receipt_number = request.POST.get("receipt_number", "").strip()
        cleared_amount_str = request.POST.get("cleared_amount", "0")
        payment_method = request.POST.get("payment_method")
        collector_name = request.POST.get("collector_name")
        remarks = request.POST.get("remarks", "").strip()
        
        # Convert cleared_amount to Decimal
        try:
            cleared_amount = Decimal(cleared_amount_str)
        except (InvalidOperation, ValueError, TypeError):
            messages.error(request, "Invalid payment amount. Please enter a valid number.")
            return redirect('clear_fees', fee_id=fee_id)
        
        # Validate
        if cleared_amount <= Decimal('0'):
            messages.error(request, "Payment amount must be greater than 0.")
        elif cleared_amount > remaining_amount:
            messages.error(request, f"Payment amount cannot exceed remaining amount: PKR {remaining_amount:.2f}")
        else:
            try:
                with transaction.atomic():
                    # Create payment record
                    ClearFee.objects.create(
                        upload_fee=fee,
                        receipt_number=receipt_number if receipt_number else None,
                        cleared_amount=cleared_amount,
                        payment_method=payment_method,
                        collector_name=collector_name,
                        remarks=remarks if remarks else None
                    )
                    
                    # Update fee status (this happens automatically in ClearFee.save())
                    
                    # Get updated totals
                    new_total_paid = total_paid + cleared_amount
                    new_remaining = total_fee_value - new_total_paid
                    
                    if new_total_paid >= total_fee_value:
                        messages.success(request, f"✅ Fee fully cleared! Total paid: PKR {new_total_paid:.2f}")
                    else:
                        messages.success(request, f"✅ Partial payment of PKR {cleared_amount:.2f} received. Remaining: PKR {new_remaining:.2f}")
                    
                    return redirect('clear_fees', fee_id=fee_id)
                    
            except Exception as e:
                messages.error(request, f"Error processing payment: {str(e)}")
                return redirect('clear_fees', fee_id=fee_id)
    
    # Get payment history with installment numbers
    payment_history = ClearFee.objects.filter(upload_fee=fee).order_by('installment_number')
    
    return render(request, "fees/clear_fee.html", {
        "fee": fee,
        "total_fee": total_fee_value,
        "total_paid": total_paid,
        "remaining_amount": remaining_amount,
        "payment_history": payment_history
    })

import csv
from django.http import HttpResponse
from django.utils import timezone
from datetime import date
from decimal import Decimal

def defaulter_student(request):
    batches = Batch.objects.all()
    semesters = Semester.objects.all()
    sections = Section.objects.all()
    disciplines = Discipline.objects.all()  # Add this

    fees = UploadFee.objects.select_related("student", "batch", "semester", "section", "discipline")  # Add discipline

    batch_filter = request.GET.get("batch")
    semester_filter = request.GET.get("semester")
    section_filter = request.GET.get("section")
    discipline_filter = request.GET.get("discipline")  # Add this

    if batch_filter:
        fees = fees.filter(batch_id=batch_filter)
    if semester_filter:
        fees = fees.filter(semester_id=semester_filter)
    if section_filter:
        fees = fees.filter(section_id=section_filter)
    if discipline_filter:
        fees = fees.filter(discipline_id=discipline_filter)  # Add this

    pending_fees = []
    today = date.today()
    
    for fee in fees:
        # Apply 5000 fine if overdue
        if fee.due_date and today > fee.due_date and not fee.is_fully_paid:
            if fee.fine != Decimal('5000.00'):
                fee.fine = Decimal('5000.00')
                fee.is_overdue = True
                fee.save()
        
        if not fee.is_fully_paid:
            pending_fees.append(fee)

    # For selected values display
    selected_batch_name = ""
    selected_section_name = ""
    selected_discipline_name = ""
    selected_semester_name = ""

    if batch_filter:
        batch = Batch.objects.filter(id=batch_filter).first()
        selected_batch_name = batch.name if batch else ""
    
    if section_filter:
        section = Section.objects.filter(id=section_filter).first()
        selected_section_name = section.name if section else ""
    
    if discipline_filter:
        discipline = Discipline.objects.filter(id=discipline_filter).first()
        selected_discipline_name = f"{discipline.field} ({discipline.program})" if discipline else ""
    
    if semester_filter:
        semester = Semester.objects.filter(id=semester_filter).first()
        selected_semester_name = f"Semester {semester.number}" if semester else ""

    return render(request, "fees/defaulter_student.html", {
        "fees": pending_fees,
        "batches": batches,
        "semesters": semesters,
        "sections": sections,
        "disciplines": disciplines,  # Add this
        "selected_batch": batch_filter,
        "selected_semester": semester_filter,
        "selected_section": section_filter,
        "selected_discipline": discipline_filter,  # Add this
        "selected_batch_name": selected_batch_name,
        "selected_section_name": selected_section_name,
        "selected_discipline_name": selected_discipline_name,
        "selected_semester_name": selected_semester_name,
    })

def export_defaulter_excel(request):
    """Export defaulter students to Excel"""
    
    # Get filter parameters
    batch_filter = request.GET.get("batch", "")
    semester_filter = request.GET.get("semester", "")
    section_filter = request.GET.get("section", "")
    discipline_filter = request.GET.get("discipline", "")
    
    # Get fees with filters
    fees = UploadFee.objects.select_related(
        "student", "batch", "semester", "section", "discipline"
    ).all()
    
    if batch_filter:
        fees = fees.filter(batch_id=batch_filter)
    if semester_filter:
        fees = fees.filter(semester_id=semester_filter)
    if section_filter:
        fees = fees.filter(section_id=section_filter)
    if discipline_filter:
        fees = fees.filter(discipline_id=discipline_filter)
    
    # Filter for defaulters only
    pending_fees = []
    today = date.today()
    
    for fee in fees:
        if fee.due_date and today > fee.due_date and not fee.is_fully_paid:
            if fee.fine != Decimal('5000.00'):
                fee.fine = Decimal('5000.00')
                fee.is_overdue = True
        
        if not fee.is_fully_paid:
            pending_fees.append(fee)
    
    # Group by student
    students_dict = {}
    for fee in pending_fees:
        student_id = fee.student.id
        if student_id not in students_dict:
            students_dict[student_id] = {
                'student': fee.student,
                'batch': fee.batch,
                'semester': fee.semester,
                'section': fee.section,
                'discipline': fee.discipline,
                'fees': [],
                'total_pending': Decimal('0'),
            }
        
        students_dict[student_id]['fees'].append(fee)
        students_dict[student_id]['total_pending'] += fee.total_fee()
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    filename = f'defaulter_students_{timestamp}.csv'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    writer = csv.writer(response)
    
    # Write headers
    writer.writerow([
        'Defaulter Student Report',
        '',
        '',
        '',
        '',
        '',
        'Generated: ' + timezone.now().strftime("%Y-%m-%d %H:%M:%S")
    ])
    writer.writerow([])
    
    # Write filter info
    filter_info = []
    if discipline_filter:
        discipline = Discipline.objects.filter(id=discipline_filter).first()
        if discipline:
            filter_info.append(f"Discipline: {discipline.field} ({discipline.program})")
    if batch_filter:
        batch = Batch.objects.filter(id=batch_filter).first()
        if batch:
            filter_info.append(f"Batch: {batch.name}")
    if semester_filter:
        semester = Semester.objects.filter(id=semester_filter).first()
        if semester:
            filter_info.append(f"Semester: {semester.number}")
    if section_filter:
        section = Section.objects.filter(id=section_filter).first()
        if section:
            filter_info.append(f"Section: {section.name}")
    
    if filter_info:
        writer.writerow(['Filters Applied:'] + filter_info)
        writer.writerow([])
    
    # Write column headers
    writer.writerow([
        'Student ID', 
        'Student Name', 
        'Discipline',
        'Batch', 
        'Section',
        'Semester',
        'Pending Semesters', 
        'Pending Amount (PKR)',
        'Due Date',
        'Overdue Fine (PKR)',
        'Total Due (PKR)',
        'Contact'
    ])
    
    # Write data rows
    for student_id, student_data in students_dict.items():
        # Get pending semesters
        pending_semesters = []
        for fee in student_data['fees']:
            if fee.is_overdue:
                pending_semesters.append(f"Sem {fee.semester.number} ⚠️")
            else:
                pending_semesters.append(f"Sem {fee.semester.number}")
        
        # Calculate totals
        total_fine = sum(fee.fine for fee in student_data['fees'])
        
        # Get latest due date
        due_dates = [fee.due_date for fee in student_data['fees'] if fee.due_date]
        latest_due_date = max(due_dates) if due_dates else None
        
        writer.writerow([
            student_data['student'].student_id,
            f"{student_data['student'].first_name} {student_data['student'].last_name}",
            f"{student_data['discipline'].field} ({student_data['discipline'].program})",
            student_data['batch'].name,
            student_data['section'].name,
            f"Sem {student_data['semester'].number}",
            ', '.join(pending_semesters),
            f"{student_data['total_pending'] - total_fine:,.2f}",
            latest_due_date.strftime('%d-%m-%Y') if latest_due_date else 'N/A',
            f"{total_fine:,.2f}",
            f"{student_data['total_pending']:,.2f}",
            # student_data['student'].phone or student_data['student'].email or 'N/A'
        ])
    
    # Write summary
    writer.writerow([])
    writer.writerow([
        'SUMMARY',
        '',
        '',
        '',
        '',
        '',
        f"Total Defaulters: {len(students_dict)}",
        f"Total Amount Due: PKR {sum(s['total_pending'] for s in students_dict.values()):,.2f}",
        f"Total Overdue Fine: PKR {sum(sum(fee.fine for fee in s['fees']) for s in students_dict.values()):,.2f}",
        '',
        '',
        ''
    ])
    
    return response
def student_fee_detail(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    today = date.today()
    
    # Order by semester number
    fees = UploadFee.objects.filter(student=student).select_related(
        'batch', 'section', 'semester', 'discipline'
    ).prefetch_related('clear_records').order_by('semester__number')
    
    # Apply 5000 fine for overdue fees
    for fee in fees:
        if fee.due_date and today > fee.due_date and not fee.is_fully_paid:
            if fee.fine != Decimal('5000.00'):
                fee.fine = Decimal('5000.00')
                fee.is_overdue = True
                fee.save()
        elif fee.is_fully_paid and fee.fine > Decimal('0'):
            fee.fine = Decimal('0.00')
            fee.is_overdue = False
            fee.save()
    
    totals = fees.aggregate(
        total_amount=Sum('amount'),
        total_fine=Sum('fine')
    )
    
    total_amount = totals['total_amount'] or Decimal('0')
    total_fine = totals['total_fine'] or Decimal('0')
    total_fee_due = total_amount + total_fine
    
    # Calculate total paid from all clear records
    cleared_fees = ClearFee.objects.filter(upload_fee__student=student)
    total_paid = cleared_fees.aggregate(
        total_paid=Sum('cleared_amount')
    )['total_paid'] or Decimal('0')
    
    remaining_fee = total_fee_due - total_paid
    
    payment_percentage = Decimal('0')
    if total_fee_due > Decimal('0'):
        payment_percentage = (total_paid / total_fee_due) * Decimal('100')
    
    fee_list = []
    pending_semesters = []
    
    for fee in fees:
        fee_total = fee.amount + fee.fine
        
        # Get all payment records for this fee
        clear_records = fee.clear_records.all()
        paid_amount = sum(record.cleared_amount for record in clear_records)
        
        # Get the latest payment record for display
        latest_payment = clear_records.order_by('-cleared_date').first()
        
        is_cleared = paid_amount >= fee_total
        balance = fee_total - paid_amount
        
        # Get payment info from latest payment if exists
        receipt_number = None
        payment_date = None
        payment_method = None
        
        if latest_payment:
            receipt_number = latest_payment.receipt_number
            payment_date = latest_payment.cleared_date
            payment_method = latest_payment.payment_method
        
        is_overdue = fee.is_overdue
        
        if not is_cleared and balance > 0:
            pending_semesters.append(f"Semester {fee.semester.number}")
        
        fee_data = {
            'id': fee.id,
            'semester': fee.semester,
            'semester_number': fee.semester.number,  # This is what template expects
            'amount': fee.amount,
            'fine': fee.fine,
            'total_fee': fee_total,
            'paid_amount': paid_amount,
            'balance': balance,
            'is_cleared': is_cleared,
            'is_overdue': is_overdue,
            'due_date': fee.due_date,
            'payment_date': payment_date,
            'receipt_number': receipt_number,
            'payment_method': payment_method,
            'batch': fee.batch,
            'section': fee.section,
            'discipline': fee.discipline,
            'upload_date': fee.upload_date,
            'installments': clear_records.count(),
        }
        
        fee_list.append(fee_data)
    
    context = {
        'student': student,
        'fees': fee_list,
        'total_fee_payable': total_fee_due,
        'total_paid': total_paid,
        'total_fine': total_fine,
        'balance_due': remaining_fee,
        'payment_percentage': round(payment_percentage, 2),
        'pending_semesters': list(set(pending_semesters)),
        'current_date': today,
    }
    
    return render(request, 'fees/student_fee_detail.html', context)

# Add these helper functions if they don't exist
def can_edit_fee(user):
    """Check if user can edit fees"""
    return user.is_authenticated and (user.is_staff or user.is_superuser)

def can_delete_fee(user):
    """Check if user can delete fees"""
    return user.is_authenticated and user.is_superuser

def export_fees_excel(request):
    """Export filtered fee records to Excel using pandas"""
    
    # Get filter parameters
    batch_filter = request.GET.get("batch", "")
    semester_filter = request.GET.get("semester", "")
    section_filter = request.GET.get("section", "")
    discipline_filter = request.GET.get("discipline", "")
    
    # Apply filtering
    fees = UploadFee.objects.select_related(
        "student", "batch", "semester", "section", "discipline"
    ).all()
    
    if discipline_filter:
        fees = fees.filter(discipline_id=discipline_filter)
    if batch_filter:
        fees = fees.filter(batch_id=batch_filter)
    if section_filter:
        fees = fees.filter(section_id=section_filter)
    if semester_filter:
        fees = fees.filter(semester_id=semester_filter)
    
    # Prepare data
    data = []
    today = date.today()
    
    for fee in fees:
        # Apply fine logic
        if fee.due_date and today > fee.due_date and not fee.is_fully_paid:
            if fee.fine != Decimal('5000.00'):
                fee.fine = Decimal('5000.00')
                fee.is_overdue = True
        elif fee.is_fully_paid and fee.fine > Decimal('0'):
            fee.fine = Decimal('0.00')
            fee.is_overdue = False
        
        fee_total = fee.total_fee()
        paid_amount = fee.paid_amount
        remaining_amount = fee.remaining_amount
        
        data.append({
            'Student_ID': fee.student.student_id,
            'Student_Name': f"{fee.student.first_name} {fee.student.last_name}",
            'Email': fee.student.email or '',
            # 'Phone': fee.student.phone or '',
            'Discipline': f"{fee.discipline.field} ({fee.discipline.program})",
            'Batch': fee.batch.name,
            'Section': fee.section.name,
            'Semester': f"Semester {fee.semester.number}",
            'Base_Fee': float(fee.amount),
            'Late_Fine': float(fee.fine),
            'Total_Fee': float(fee_total),
            'Paid_Amount': float(paid_amount),
            'Pending_Amount': float(remaining_amount),
            'Payment_Status': 'Fully Paid' if fee.is_fully_paid else ('Partially Paid' if paid_amount > 0 else 'Unpaid'),
            'Due_Date': fee.due_date.strftime('%Y-%m-%d') if fee.due_date else '',
            'Overdue': 'Yes' if fee.is_overdue else 'No',
            # 'Remarks': fee.remarks or '',
        })
    
    if not data:
        # Return empty file
        response = HttpResponse("No data to export", content_type="text/plain")
        response['Content-Disposition'] = 'attachment; filename="no_data.txt"'
        return response
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    # Create Excel in memory
    output = io.BytesIO()
    
    # Write to Excel
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Fee Records', index=False)
    
    output.seek(0)
    
    # Prepare response
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    filename = f'fee_records_{timestamp}.xlsx'
    
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response