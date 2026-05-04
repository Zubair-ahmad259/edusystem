
# home_auth/views.py
import threading
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.contrib import messages
from django.utils.crypto import get_random_string
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.db import IntegrityError
import logging

from home_auth.models import CustomUser, PasswordResetRequest
from student.models import Student, Discipline, Batch, Semester, Section
from teachers.models import Teacher
from head.models import AdminProfile

logger = logging.getLogger(__name__)


# ============= ROLE CHECK FUNCTIONS =============

def is_office_clerk(user):
    """Check if user is office clerk"""
    if user.is_superuser:
        return True
    try:
        return hasattr(user, 'admin_profile') and user.admin_profile.role == 'Office Clerk'
    except:
        return False

def is_accounts_officer(user):
    """Check if user is accounts officer"""
    if user.is_superuser:
        return True
    try:
        return hasattr(user, 'admin_profile') and user.admin_profile.role == 'Accounts'
    except:
        return False

def is_librarian(user):
    """Check if user is librarian"""
    if user.is_superuser:
        return True
    try:
        return hasattr(user, 'admin_profile') and user.admin_profile.role == 'Librarian'
    except:
        return False

def get_user_role(user):
    """Get user role"""
    if user.is_superuser:
        return 'superuser'
    if user.is_admin:
        return 'admin'
    try:
        return user.admin_profile.role if hasattr(user, 'admin_profile') else None
    except:
        return None


# ============= ROLE-BASED DASHBOARD REDIRECT =============

@login_required
def role_based_dashboard(request):
    """Redirect to appropriate dashboard based on user role"""
    user = request.user
    
    if user.is_superuser or user.is_admin:
        return redirect('admin_dashboard')
    elif is_office_clerk(user):
        return redirect('office_clerk_dashboard')
    elif is_accounts_officer(user):
        return redirect('accounts_dashboard')
    elif is_librarian(user):
        return redirect('librarian_dashboard')
    elif user.is_teacher:
        return redirect('teacher_dashboard')
    elif user.is_student:
        return redirect('student_dashboard')
    else:
        return redirect('index')

# home_auth/context_processors.py

def user_role_context(request):
    """Add user role to all templates"""
    if request.user.is_authenticated:
        # Check for admin profile role
        if hasattr(request.user, 'admin_profile') and request.user.admin_profile:
            role = request.user.admin_profile.role
            return {'user_role': role}
        
        # Check for superuser or admin
        if request.user.is_superuser:
            return {'user_role': 'superuser'}
        if request.user.is_admin:
            return {'user_role': 'admin'}
        if request.user.is_teacher:
            return {'user_role': 'teacher'}
        if request.user.is_student:
            return {'user_role': 'student'}
    
    return {'user_role': None}
# ============= DASHBOARD VIEWS =============

@login_required
def admin_dashboard(request):
    """Full admin dashboard - Superuser and Admin only"""
    if not (request.user.is_superuser or request.user.is_admin):
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    
    from student.models import Student
    from teachers.models import Teacher
    from subject.models import Subject
    
    context = {
        'total_students': Student.objects.count(),
        'total_teachers': Teacher.objects.count(),
        'total_subjects': Subject.objects.count(),
        'user_role': 'Admin',
    }
    return render(request, 'Home/admin_dashboard.html', context)


@login_required
def office_clerk_dashboard(request):
    """Office Clerk Dashboard - Can view students and teachers, cannot edit"""
    from student.models import Student
    from teachers.models import Teacher
    
    context = {
        'total_students': Student.objects.count(),
        'total_teachers': Teacher.objects.count(),
        'recent_students': Student.objects.order_by('-id')[:10],
        'recent_teachers': Teacher.objects.order_by('-id')[:5],
        'can_edit': False,
        'can_delete': False,
        'can_add': False,
        'can_view': True,
        'user_role': 'Office Clerk',
    }
    return render(request, 'Home/office_clerk_dashboard.html', context)


@login_required
def accounts_dashboard(request):
    """Accounts Officer Dashboard - Financial access only"""
    from fee_system.models import UploadFee, ClearFee
    from django.db.models import Sum
    from decimal import Decimal
    
    # Calculate total fees (sum of amount + fine from UploadFee)
    total_fees = UploadFee.objects.aggregate(
        total=Sum('amount') + Sum('fine')
    )['total'] or Decimal('0.00')
    
    # Calculate total paid (sum of cleared_amount from ClearFee)
    total_paid = ClearFee.objects.aggregate(
        total=Sum('cleared_amount')
    )['total'] or Decimal('0.00')
    
    # Calculate pending fees
    pending_fees = total_fees - total_paid
    
    # Get recent payments
    recent_payments = ClearFee.objects.select_related('upload_fee__student').order_by('-cleared_date')[:10]
    
    context = {
        'total_fees': total_fees,
        'total_paid': total_paid,
        'pending_fees': pending_fees,
        'recent_payments': recent_payments,
        'can_edit': True,
        'can_delete': False,
        'user_role': 'Accounts Officer',
    }
    return render(request, 'Home/accounts_dashboard.html', context)

@login_required
def librarian_dashboard(request):
    """Librarian Dashboard - Library management access"""
    context = {
        'total_books': 0,
        'books_issued': 0,
        'can_edit': True,
        'can_delete': False,
        'user_role': 'Librarian',
    }
    return render(request, 'Home/librarian_dashboard.html', context)

# ============= TEST EMAIL FUNCTION =============

def test_email(request):
    """Test email sending"""
    try:
        send_mail(
            'Test Email from LMS',
            'If you receive this, email is working correctly!',
            settings.DEFAULT_FROM_EMAIL,
            ['zk7233103@gmail.com'],
            fail_silently=False,
        )
        return HttpResponse('✅ Email sent successfully! Check your inbox.')
    except Exception as e:
        return HttpResponse(f'❌ Error: {str(e)}')

# ============= HELPER FUNCTIONS =============

def generate_unique_username(email):
    """Generate a unique username from email"""
    base_username = email.split('@')[0]
    username = base_username
    counter = 1
    
    while CustomUser.objects.filter(username=username).exists():
        username = f"{base_username}{counter}"
        counter += 1
    
    return username


def send_account_creation_email(request, user, password, user_type, email, name=""):
    """Send account creation email"""
    try:
        subject = f"Your {user_type} Account Details - LMS Portal"
        
        # Get name safely
        if not name:
            if hasattr(user, 'first_name') and user.first_name:
                if hasattr(user, 'last_name') and user.last_name:
                    name = f"{user.first_name} {user.last_name}"
                else:
                    name = user.first_name
            else:
                name = user.username
        
        message = (
            f"Dear {name},\n\n"
            f"Welcome to the Learning Management System.\n\n"
            f"Your {user_type} account has been created successfully.\n\n"
            f"Login Credentials:\n"
            f"Username: {user.username}\n"
            f"Temporary Password: {password}\n\n"
            f"Important Information:\n"
            f"• Please change your password immediately after logging in\n"
            f"• Keep your credentials secure\n"
            f"• Do not share your password with anyone\n\n"
            f"Login URL: {request.build_absolute_uri('/login/')}\n\n"
            f"Best regards,\n"
            f"LMS Administration Team"
        )
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        return False


def send_password_reset_email(request, user, new_password, user_type):
    """Send password reset email"""
    try:
        subject = f"Your {user_type} Password Has Been Reset - LMS Portal"
        
        user_name = ""
        if hasattr(user, 'first_name') and user.first_name:
            if hasattr(user, 'last_name') and user.last_name:
                user_name = f"{user.first_name} {user.last_name}"
            else:
                user_name = user.first_name
        else:
            user_name = user.username
        
        message = (
            f"Dear {user_name},\n\n"
            f"Your {user_type} account password has been reset by the administrator.\n\n"
            f"New Login Credentials:\n"
            f"Username: {user.username}\n"
            f"New Temporary Password: {new_password}\n\n"
            f"Important Information:\n"
            f"• Please change your password immediately after logging in\n"
            f"• Keep your credentials secure\n\n"
            f"Login URL: {request.build_absolute_uri('/login/')}\n\n"
            f"If you did not request this change, please contact the administrator immediately.\n\n"
            f"Best regards,\n"
            f"LMS Administration Team"
        )
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        return False


def reset_user_password(user):
    """Reset a user's password to a random string and return the new password"""
    try:
        new_password = get_random_string(10)
        user.set_password(new_password)
        user.password_generated = True
        user.temp_password = new_password
        user.save()
        logger.info(f"Password reset for user: {user.username}")
        return new_password
    except Exception as e:
        logger.error(f"Error in reset_user_password: {str(e)}")
        raise e


# ============= AUTHENTICATION VIEWS =============
# Add this function before login_view
def get_user_role_and_redirect(user):
    """Get user role and return appropriate redirect URL name"""
    if user.is_superuser or user.is_admin:
        return 'admin_dashboard'
    elif hasattr(user, 'admin_profile') and user.admin_profile:
        role = user.admin_profile.role
        if role == 'Office Clerk':
            return 'office_clerk_dashboard'
        elif role == 'Accounts':
            return 'accounts_dashboard'
        elif role == 'Librarian':
            return 'librarian_dashboard'
        elif role == 'HOD':
            return 'hod_dashboard'
    elif user.is_teacher:
        return 'teacher_dashboard'
    elif user.is_student:
        return 'student_dashboard'
    else:
        return 'dashboard'
def login_view(request):
    """Handle user login"""
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        if not email or not password:
            messages.error(request, 'Both email and password are required.')
            return render(request, 'authentication/login.html')
        
        try:
            # Try to find user by email first
            user = CustomUser.objects.filter(email=email).first()
            if user:
                # Authenticate with username
                user = authenticate(request, username=user.username, password=password)
            else:
                # Try authenticating directly with email as username
                user = authenticate(request, username=email, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {user.username}!')
                
                # Check if password is temporary and needs change
                if user.password_generated and user.temp_password:
                    messages.warning(request, 'Please change your temporary password.')
                
                # Redirect based on role
                redirect_url = get_user_role_and_redirect(user)
                return redirect(redirect_url)
            else:
                messages.error(request, 'Invalid email or password.')
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            messages.error(request, 'An error occurred during login.')
    
    return render(request, 'authentication/login.html')
def logout_view(request):
    """Handle user logout"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('login')


from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth import get_user_model

User = get_user_model()
def forgot_password_view(request):
    """Handle forgot password request - sends reset link via email"""
    
    # Your live server URL
    LIVE_SERVER_URL = "https://edusphares.pythonanywhere.com"
    
    User = get_user_model()
    
    # If user is already on the reset password page (with token in URL)
    if 'token' in request.GET and 'uidb64' in request.GET:
        try:
            uid = force_str(urlsafe_base64_decode(request.GET.get('uidb64')))
            user = User.objects.get(pk=uid)
            token = request.GET.get('token')
            
            if default_token_generator.check_token(user, token):
                if request.method == 'POST':
                    new_password = request.POST.get('new_password')
                    confirm_password = request.POST.get('confirm_password')
                    
                    if new_password and new_password == confirm_password and len(new_password) >= 8:
                        user.set_password(new_password)
                        user.save()
                        messages.success(request, 'Password reset successfully! Please login.')
                        return redirect('login')
                    else:
                        messages.error(request, 'Invalid password. Please try again.')
                
                return render(request, 'authentication/reset_password.html', {
                    'validlink': True,
                    'user': user,
                    'token': token,
                    'uidb64': request.GET.get('uidb64'),
                    'user_email': user.email,
                    'user_name': user.first_name or user.username
                })
            else:
                messages.error(request, 'Invalid or expired reset link.')
                return redirect('forgot_password')
        except Exception as e:
            messages.error(request, 'Invalid reset link.')
            return redirect('forgot_password')
    
    # Handle email submission
    if request.method == 'POST':
        email = request.POST.get('email')
        
        if not email:
            messages.error(request, 'Please enter your email address.')
            return render(request, 'authentication/forgot_password.html')
        
        user = User.objects.filter(email=email).first()
        
        if user:
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # Create reset link
            reset_link = f"{LIVE_SERVER_URL}/home_auth/reset-password/{token}/?uidb64={uid}"
            
            # HTML Email with button
            html_message = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; background: #f9f9f9; border-radius: 10px; }}
                    .header {{ background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0; }}
                    .content {{ padding: 30px; background: white; border-radius: 0 0 10px 10px; }}
                    .button {{
                        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                        color: white;
                        padding: 12px 30px;
                        text-decoration: none;
                        border-radius: 25px;
                        display: inline-block;
                        margin: 20px 0;
                    }}
                    .footer {{ font-size: 12px; color: #666; text-align: center; margin-top: 20px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h2>Password Reset Request</h2>
                    </div>
                    <div class="content">
                        <p>Dear {user.first_name or user.username},</p>
                        
                        <p>We received a request to reset your password for your EduSphere account.</p>
                        
                        <p style="text-align: center;">
                            <a href="{reset_link}" class="button">Reset Password</a>
                        </p>
                        
                        <p>If the button doesn't work, copy and paste this link into your browser:</p>
                        <p style="background: #f0f0f0; padding: 10px; word-break: break-all;">{reset_link}</p>
                        
                        <p>This link will expire in 24 hours.</p>
                        
                        <p>If you didn't request this, please ignore this email.</p>
                    </div>
                    <div class="footer">
                        <p>EduSphere - Empowering Global Learning</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            plain_message = f"""
            Dear {user.first_name or user.username},
            
            We received a request to reset your password for your EduSphere account.
            
            Click the link below to reset your password:
            {reset_link}
            
            This link will expire in 24 hours.
            
            If you didn't request this, please ignore this email.
            
            EduSphere - Empowering Global Learning
            """
            
            try:
                send_mail(
                    'Reset Your Password - EduSphere',
                    plain_message,
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    html_message=html_message,
                    fail_silently=False,
                )
                messages.success(request, 'Password reset link has been sent to your email.')
            except Exception as e:
                logger.error(f"Email sending failed: {e}")
                messages.error(request, 'Failed to send email. Please try again.')
        else:
            messages.success(request, 'If an account exists with this email, you will receive a reset link.')
        
        return redirect('forgot_password')
    
    return render(request, 'authentication/forgot_password.html')
def reset_password_view(request, token):
    """Handle password reset with token - Show reset form"""
    uidb64 = request.GET.get('uidb64')
    
    if not uidb64:
        messages.error(request, 'Invalid reset link.')
        return redirect('forgot_password')
    
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = get_user_model().objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, get_user_model().DoesNotExist):
        user = None
    
    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            
            if new_password and new_password == confirm_password and len(new_password) >= 8:
                user.set_password(new_password)
                user.save()
                messages.success(request, 'Password reset successfully! Please login with your new password.')
                return redirect('login')
            else:
                messages.error(request, 'Please enter a valid password (minimum 8 characters).')
        
        return render(request, 'authentication/reset_password.html', {
            'validlink': True,
            'user': user,
            'token': token,
            'uidb64': uidb64
        })
    else:
        messages.error(request, 'The password reset link is invalid or has expired.')
        return redirect('forgot_password')
def reset_password_confirm_view(request, token):
    """Handle password reset confirmation - Process new password"""
    if request.method != 'POST':
        return redirect('forgot_password')
    
    reset_request = get_object_or_404(PasswordResetRequest, token=token)
    
    if not reset_request.is_valid():
        messages.error(request, 'This reset link has expired. Please request a new one.')
        return redirect('forgot_password')
    
    new_password = request.POST.get('new_password')
    confirm_password = request.POST.get('confirm_password')
    
    # Validate passwords
    if not new_password or not confirm_password:
        messages.error(request, 'Both password fields are required.')
        return redirect('reset_password', token=token)
    
    if new_password != confirm_password:
        messages.error(request, 'Passwords do not match.')
        return redirect('reset_password', token=token)
    
    if len(new_password) < 8:
        messages.error(request, 'Password must be at least 8 characters long.')
        return redirect('reset_password', token=token)
    
    # Check password strength
    if not any(char.isdigit() for char in new_password):
        messages.error(request, 'Password must contain at least one number.')
        return redirect('reset_password', token=token)
    
    if not any(char.isupper() for char in new_password):
        messages.error(request, 'Password must contain at least one uppercase letter.')
        return redirect('reset_password', token=token)
    
    try:
        # Update password
        user = reset_request.user
        user.set_password(new_password)
        user.password_generated = False
        user.temp_password = None
        user.password_change_deadline = None
        user.save()
        
        # Delete the reset request
        reset_request.delete()
        
        # Send confirmation email
        try:
            subject = "Your Password Has Been Changed - LMS Portal"
            message = f"""
Dear {user.first_name or user.username},

Your password has been successfully changed.

If you did not make this change, please contact support immediately.

Best regards,
LMS Administration Team
            """
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=True,
            )
        except Exception as e:
            logger.error(f"Confirmation email failed: {e}")
        
        messages.success(request, 'Password has been reset successfully. Please login with your new password.')
        return redirect('login')
        
    except Exception as e:
        logger.error(f"Password reset error: {str(e)}")
        messages.error(request, 'An error occurred. Please try again.')
        return redirect('reset_password', token=token)


def reset_password_success_view(request):
    """Show success message after reset link is sent"""
    return render(request, 'authentication/forgot_password.html')

@login_required
def reset_own_password(request):
    """Allow users to change their own password - No expiration"""
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        
        user = request.user
        
        # Validate inputs
        if not current_password or not new_password or not confirm_password:
            messages.error(request, 'All fields are required.')
        elif not user.check_password(current_password):
            messages.error(request, 'Current password is incorrect.')
        elif new_password != confirm_password:
            messages.error(request, 'New passwords do not match.')
        elif len(new_password) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
        else:
            try:
                # Update password
                user.set_password(new_password)
                user.password_generated = False
                user.temp_password = None
                user.password_change_deadline = None  # Clear any existing deadline
                user.save()
                
                # Keep user logged in
                update_session_auth_hash(request, user)
                
                messages.success(request, 'Your password has been changed successfully!')
                
                # Redirect based on role
                if user.is_student:
                    return redirect('student_dashboard')
                elif user.is_teacher:
                    return redirect('teacher_dashboard')
                elif user.is_admin:
                    return redirect('admin_dashboard')
                else:
                    return redirect('dashboard')
            except Exception as e:
                logger.error(f"Password change error: {str(e)}")
                messages.error(request, 'An error occurred. Please try again.')
    
    return render(request, 'authentication/reset_own_password.html')
# ============= STUDENT MANAGEMENT =============
@login_required
def manage_students_view(request):
    """Manage student accounts - Optimized for speed with email threading"""
    if not (request.user.is_admin or request.user.is_superuser):
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    
    # Get filter parameters
    discipline_id = request.GET.get('discipline')
    batch_id = request.GET.get('batch')
    semester_id = request.GET.get('semester')
    section_id = request.GET.get('section')
    status_filter = request.GET.get('status')

    # Base queryset
    students = Student.objects.select_related('discipline', 'batch', 'semester', 'section', 'user').all()

    # Apply filters
    if discipline_id:
        students = students.filter(discipline_id=discipline_id)
    if batch_id:
        students = students.filter(batch_id=batch_id)
    if semester_id:
        students = students.filter(semester_id=semester_id)
    if section_id:
        students = students.filter(section_id=section_id)
    
    if status_filter == 'has_account':
        students = students.filter(user__isnull=False)
    elif status_filter == 'no_account':
        students = students.filter(user__isnull=True)
    elif status_filter == 'temp_password':
        students = students.filter(user__password_generated=True)

    # Handle POST requests
    if request.method == "POST":
        action = request.POST.get("action")
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        # Handle single account creation
        if action == "create_account":
            student_id = request.POST.get("student_id")
            if student_id:
                student = get_object_or_404(Student, id=student_id)
                if not student.user:
                    try:
                        # Generate unique username
                        username = generate_unique_username(student.email)
                        random_password = get_random_string(10)
                        
                        # Create user
                        user = CustomUser.objects.create_user(
                            username=username,
                            email=student.email,
                            password=random_password,
                            first_name=getattr(student, 'first_name', ''),
                            last_name=getattr(student, 'last_name', ''),
                            is_student=True,
                            temp_password=random_password,
                            password_generated=True
                        )
                        
                        student.user = user
                        student.save()
                        
                        student_name = f"{getattr(student, 'first_name', '')} {getattr(student, 'last_name', '')}".strip() or student.email
                        
                        # Send email in background thread
                        def send_email_thread():
                            try:
                                email_sent = send_account_creation_email(
                                    request, user, random_password, "Student", 
                                    student.email, student_name
                                )
                                if email_sent:
                                    print(f"✅ Email sent to {student.email}")
                                else:
                                    print(f"❌ Failed to send email to {student.email}")
                            except Exception as e:
                                print(f"❌ Email thread error: {str(e)}")
                        
                        thread = threading.Thread(target=send_email_thread, daemon=True)
                        thread.start()
                        
                        if is_ajax:
                            return JsonResponse({
                                'success': True,
                                'message': 'Account created successfully',
                                'password': random_password,
                                'username': username,
                                'email': student.email,
                                'student_name': student_name,
                                'student_id': student.id
                            })
                        messages.success(request, f"Account created successfully for {student.email}")
                        
                    except IntegrityError as e:
                        logger.error(f"Integrity error: {str(e)}")
                        if is_ajax:
                            return JsonResponse({
                                'success': False,
                                'message': 'A user with this email already exists'
                            })
                        messages.error(request, 'A user with this email already exists')
                    except Exception as e:
                        logger.error(f"Error creating account: {str(e)}")
                        if is_ajax:
                            return JsonResponse({
                                'success': False,
                                'message': f'Error creating account: {str(e)}'
                            })
                        messages.error(request, f'Error creating account: {str(e)}')
                else:
                    if is_ajax:
                        return JsonResponse({
                            'success': False,
                            'message': f'User already exists for {student.email}'
                        })
                    messages.info(request, f'User already exists for {student.email}')
            
            if not is_ajax:
                return redirect('manage_students_view')
        
        # Handle password reset
        elif action == "reset_password":
            student_id = request.POST.get("student_id")
            if student_id:
                student = get_object_or_404(Student, id=student_id)
                if student.user:
                    try:
                        new_password = reset_user_password(student.user)
                        
                        # Send email in background thread
                        def send_reset_email_thread():
                            try:
                                email_sent = send_password_reset_email(request, student.user, new_password, "Student")
                                if email_sent:
                                    print(f"✅ Reset email sent to {student.email}")
                                else:
                                    print(f"❌ Failed to send reset email to {student.email}")
                            except Exception as e:
                                print(f"❌ Reset email thread error: {str(e)}")
                        
                        thread = threading.Thread(target=send_reset_email_thread, daemon=True)
                        thread.start()
                        
                        if is_ajax:
                            return JsonResponse({
                                'success': True,
                                'message': 'Password reset successfully',
                                'password': new_password,
                                'username': student.user.username,
                                'email': student.email,
                                'student_name': getattr(student, 'name', student.user.username),
                                'action': 'reset'
                            })
                        messages.success(request, f'Password reset successfully for {student.email}')
                        
                    except Exception as e:
                        logger.error(f"Error resetting password: {str(e)}")
                        if is_ajax:
                            return JsonResponse({
                                'success': False,
                                'message': f'Error resetting password: {str(e)}'
                            })
                        messages.error(request, f'Error resetting password: {str(e)}')
                else:
                    if is_ajax:
                        return JsonResponse({
                            'success': False,
                            'message': f'No user account exists for {student.email}. Create account first.'
                        })
                    messages.error(request, f'No user account exists for {student.email}. Create account first.')
            
            if not is_ajax:
                return redirect('manage_students_view')
    
    # Calculate statistics
    total_students = students.count()
    students_with_account = students.filter(user__isnull=False).count()
    students_without_account = students.filter(user__isnull=True).count()
    students_with_temp_password = students.filter(user__password_generated=True).count()
    
    # Pagination
    paginator = Paginator(students, 20)
    page_number = request.GET.get('page')
    students_page = paginator.get_page(page_number)
    
    context = {
        "disciplines": Discipline.objects.all(),
        "batches": Batch.objects.all(),
        "semesters": Semester.objects.all(),
        "sections": Section.objects.all(),
        "students": students_page,
        "total_students": total_students,
        "students_with_account": students_with_account,
        "students_without_account": students_without_account,
        "students_with_temp_password": students_with_temp_password,
        "user_type": "student"
    }
    
    return render(request, "authentication/register.html", context)

# ============= TEACHER MANAGEMENT =============
@login_required
def manage_teachers_view(request):
    """Manage teacher accounts - Optimized with threading"""
    if not (request.user.is_admin or request.user.is_superuser):
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    
    # Get filter parameters
    status_filter = request.GET.get('status')
    
    # Base queryset
    teachers = Teacher.objects.select_related('user').all()
    
    # Apply status filter
    if status_filter == 'has_account':
        teachers = teachers.filter(user__isnull=False)
    elif status_filter == 'no_account':
        teachers = teachers.filter(user__isnull=True)
    elif status_filter == 'temp_password':
        teachers = teachers.filter(user__password_generated=True)

    # Handle POST requests
    if request.method == "POST":
        action = request.POST.get("action")
        teacher_id = request.POST.get("teacher_id")
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        if action == "create_account" and teacher_id:
            teacher = get_object_or_404(Teacher, id=teacher_id)
            if not teacher.user:
                try:
                    username = generate_unique_username(teacher.email)
                    random_password = get_random_string(10)
                    
                    user = CustomUser.objects.create_user(
                        username=username,
                        email=teacher.email,
                        password=random_password,
                        first_name=teacher.first_name if hasattr(teacher, 'first_name') else "",
                        last_name=teacher.last_name if hasattr(teacher, 'last_name') else "",
                        is_teacher=True,
                        temp_password=random_password,
                        password_generated=True
                    )
                    
                    teacher.user = user
                    teacher.save()
                    
                    teacher_name = f"{teacher.first_name} {teacher.last_name}" if hasattr(teacher, 'first_name') else teacher.email
                    
                    # Send email in background thread (non-blocking)
                    def send_email():
                        try:
                            send_account_creation_email(request, user, random_password, "Teacher", teacher.email, teacher_name)
                        except Exception as e:
                            logger.error(f"Email error for {teacher.email}: {str(e)}")
                    
                    thread = threading.Thread(target=send_email, daemon=True)
                    thread.start()
                    
                    if is_ajax:
                        return JsonResponse({
                            'success': True,
                            'message': 'Account created successfully',
                            'password': random_password,
                            'username': username,
                            'email': teacher.email,
                            'teacher_name': teacher_name,
                            'teacher_id': teacher.id
                        })
                    messages.success(request, f'Account created successfully for {teacher.email}')
                    
                except IntegrityError as e:
                    if is_ajax:
                        return JsonResponse({'success': False, 'message': 'User with this email already exists'})
                    messages.error(request, 'User with this email already exists')
                except Exception as e:
                    logger.error(f"Error creating teacher account: {str(e)}")
                    if is_ajax:
                        return JsonResponse({'success': False, 'message': str(e)})
                    messages.error(request, f'Error creating account: {str(e)}')
            else:
                if is_ajax:
                    return JsonResponse({'success': False, 'message': f'User already exists for {teacher.email}'})
                messages.info(request, f'User already exists for {teacher.email}')
        
        elif action == "reset_password" and teacher_id:
            teacher = get_object_or_404(Teacher, id=teacher_id)
            if teacher.user:
                try:
                    new_password = reset_user_password(teacher.user)
                    teacher_name = f"{teacher.first_name} {teacher.last_name}" if hasattr(teacher, 'first_name') else teacher.email
                    
                    # Send email in background thread
                    def send_reset_email():
                        try:
                            send_password_reset_email(request, teacher.user, new_password, "Teacher")
                        except Exception as e:
                            logger.error(f"Reset email error for {teacher.email}: {str(e)}")
                    
                    thread = threading.Thread(target=send_reset_email, daemon=True)
                    thread.start()
                    
                    if is_ajax:
                        return JsonResponse({
                            'success': True,
                            'message': 'Password reset successfully',
                            'password': new_password,
                            'username': teacher.user.username,
                            'email': teacher.email,
                            'teacher_name': teacher_name,
                            'action': 'reset'
                        })
                    messages.success(request, f'Password reset successfully for {teacher.email}')
                    
                except Exception as e:
                    if is_ajax:
                        return JsonResponse({'success': False, 'message': str(e)})
                    messages.error(request, f'Error resetting password: {str(e)}')
            else:
                if is_ajax:
                    return JsonResponse({'success': False, 'message': 'No account exists. Create account first.'})
                messages.error(request, 'No account exists. Create account first.')
        
        if not is_ajax:
            return redirect('manage_teachers')
    
    # Calculate statistics
    total_teachers = teachers.count()
    teachers_with_account = teachers.filter(user__isnull=False).count()
    teachers_without_account = teachers.filter(user__isnull=True).count()
    teachers_with_temp_password = teachers.filter(user__password_generated=True).count()
    
    # Pagination
    paginator = Paginator(teachers, 20)
    page_number = request.GET.get('page')
    teachers_page = paginator.get_page(page_number)
    
    context = {
        "teachers": teachers_page,
        "total_teachers": total_teachers,
        "teachers_with_account": teachers_with_account,
        "teachers_without_account": teachers_without_account,
        "teachers_with_temp_password": teachers_with_temp_password,
        "user_type": "teacher"
    }
    
    return render(request, "authentication/register_teacher.html", context)
# ============= ADMIN MANAGEMENT =============

# ============= ADMIN MANAGEMENT =============

@login_required
def manage_admins_view(request):
    """Manage admin accounts - Optimized with threading"""
    if not (request.user.is_superuser):
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    
    discipline_id = request.GET.get('discipline')
    role_filter = request.GET.get('role')
    
    # Get all admin profiles with user relation
    admins = AdminProfile.objects.select_related('user', 'discipline').all()
    
    # Apply filters
    if discipline_id:
        admins = admins.filter(discipline_id=discipline_id)
    if role_filter:
        admins = admins.filter(role=role_filter)

    # Handle POST requests for account creation
    if request.method == "POST":
        action = request.POST.get("action")
        admin_id = request.POST.get("admin_id")
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        if admin_id:
            admin = get_object_or_404(AdminProfile, id=admin_id)

            if action == "create_account":
                # Double-check if user already exists (prevent duplicate on refresh)
                if admin.user:
                    if is_ajax:
                        return JsonResponse({
                            'success': False, 
                            'message': f'Account already exists for {admin.email}',
                            'already_exists': True
                        })
                    messages.info(request, f'Account already exists for {admin.email}')
                else:
                    try:
                        username = generate_unique_username(admin.email)
                        random_password = get_random_string(10)

                        user = CustomUser.objects.create_user(
                            username=username,
                            email=admin.email,
                            password=random_password,
                            first_name=admin.first_name,
                            last_name=admin.last_name,
                            is_staff=True,
                            is_admin=True,
                            temp_password=random_password,
                            password_generated=True
                        )
                        
                        admin.user = user
                        admin.save()
                        
                        admin_name = f"{admin.first_name} {admin.last_name}"
                        
                        # Send email in background thread
                        def send_email():
                            try:
                                send_account_creation_email(request, user, random_password, "Admin", admin.email, admin_name)
                            except Exception as e:
                                logger.error(f"Email error for {admin.email}: {str(e)}")
                        
                        thread = threading.Thread(target=send_email, daemon=True)
                        thread.start()

                        if is_ajax:
                            return JsonResponse({
                                'success': True,
                                'message': 'Account created successfully',
                                'password': random_password,
                                'username': username,
                                'email': admin.email,
                                'admin_name': admin_name,
                                'admin_id': admin.id
                            })
                        
                        messages.success(request, f'Admin account created successfully for {admin.email}')
                    except Exception as e:
                        logger.error(f"Error creating admin account: {str(e)}")
                        if is_ajax:
                            return JsonResponse({'success': False, 'message': str(e)})
                        messages.error(request, f'Error creating account: {str(e)}')

            elif action == "reset_password":
                if admin.user:
                    try:
                        new_password = reset_user_password(admin.user)
                        admin_name = f"{admin.first_name} {admin.last_name}"
                        
                        # Send email in background
                        def send_reset_email():
                            try:
                                send_password_reset_email(request, admin.user, new_password, "Admin")
                            except Exception as e:
                                logger.error(f"Reset email error for {admin.email}: {str(e)}")
                        
                        thread = threading.Thread(target=send_reset_email, daemon=True)
                        thread.start()
                        
                        if is_ajax:
                            return JsonResponse({
                                'success': True,
                                'message': 'Password reset successfully',
                                'password': new_password,
                                'username': admin.user.username,
                                'email': admin.email,
                                'admin_name': admin_name
                            })
                        messages.success(request, f'Password reset successfully for {admin.email}')
                    except Exception as e:
                        logger.error(f"Error resetting password: {str(e)}")
                        if is_ajax:
                            return JsonResponse({'success': False, 'message': str(e)})
                        messages.error(request, f'Error resetting password: {str(e)}')
                else:
                    if is_ajax:
                        return JsonResponse({'success': False, 'message': 'No account exists. Create account first.'})
                    messages.error(request, 'No account exists. Create account first.')

        if not is_ajax:
            return redirect('manage_admins')

    # Calculate statistics
    total_admins = admins.count()
    admins_with_account = admins.filter(user__isnull=False).count()
    admins_without_account = admins.filter(user__isnull=True).count()
    admins_with_temp_password = admins.filter(user__password_generated=True).count()
    
    # Pagination
    paginator = Paginator(admins, 20)
    admins_page = paginator.get_page(request.GET.get('page'))
    
    context = {
        "admins": admins_page,
        "disciplines": Discipline.objects.all(),
        "role_choices": AdminProfile._meta.get_field('role').choices,
        "admins_with_account": admins_with_account,
        "admins_without_account": admins_without_account,
        "admins_with_temp_password": admins_with_temp_password,
        "total_admins": total_admins,
        "user_type": "admin"
    }

    return render(request, "authentication/register_admin.html", context)
@login_required
def process_password_reset(request, user_type, user_id):
    """Process password reset with custom password"""
    if request.method != 'POST':
        return redirect('manage_students_view')
    
    try:
        # Get the appropriate user object
        if user_type == 'student':
            user_obj = get_object_or_404(Student, id=user_id)
            redirect_url = 'manage_students_view'
            user_type_name = 'Student'
        elif user_type == 'teacher':
            user_obj = get_object_or_404(Teacher, id=user_id)
            redirect_url = 'manage_teachers_view'
            user_type_name = 'Teacher'
        elif user_type == 'admin':
            user_obj = get_object_or_404(AdminProfile, id=user_id)
            redirect_url = 'manage_admins'
            user_type_name = 'Admin'
        else:
            messages.error(request, 'Invalid user type.')
            return redirect('manage_students_view')
        
        # Find user by email
        user = CustomUser.objects.filter(email=user_obj.email).first()
        
        # Check if user exists
        if not user:
            messages.error(request, f"No user account exists for {user_obj.email}.")
            return redirect(redirect_url)
        
        # Get passwords from form
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        # Validate passwords
        if not new_password or not confirm_password:
            messages.error(request, 'Both password fields are required.')
            return redirect(request.META.get('HTTP_REFERER', redirect_url))
        
        if new_password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return redirect(request.META.get('HTTP_REFERER', redirect_url))
        
        if len(new_password) < 6:
            messages.error(request, 'Password must be at least 6 characters long.')
            return redirect(request.META.get('HTTP_REFERER', redirect_url))
        
        # Update password
        user.set_password(new_password)
        user.password_generated = False
        user.temp_password = None
        user.save()
        
        # Get name for display
        if hasattr(user_obj, 'first_name') and hasattr(user_obj, 'last_name'):
            display_name = f"{user_obj.first_name} {user_obj.last_name}"
        else:
            display_name = user.username
        
        # Send email notification
        try:
            send_mail(
                'Your Password Has Been Reset - LMS Portal',
                f'Hello {display_name},\n\n'
                f'Your {user_type_name} account password has been reset by an administrator.\n\n'
                f'Your new password is: {new_password}\n\n'
                f'Please login at: {request.build_absolute_uri("/login/")}\n\n'
                f'Best regards,\nLMS Administration Team',
                settings.DEFAULT_FROM_EMAIL,
                [user_obj.email],
                fail_silently=True,
            )
        except Exception as e:
            logger.error(f"Email sending failed: {e}")
        
        # Check if AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Password has been reset successfully',
                'user_name': display_name,
                'email': user_obj.email
            })
        
        messages.success(request, f'Password has been reset successfully for {user_obj.email}')
        return redirect(redirect_url)
        
    except Exception as e:
        logger.error(f"Error in process_password_reset: {str(e)}")
        messages.error(request, f'An error occurred: {str(e)}')
        return redirect('manage_students_view')


        from django.http import JsonResponse

def validate_student_email(request):
    email = request.GET.get('email')
    # Check if email exists in Student model
    from student.models import Student
    is_valid = Student.objects.filter(email=email).exists()
    return JsonResponse({'is_valid': is_valid})