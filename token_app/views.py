from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Q, Count
from datetime import date, timedelta
from django.http import JsonResponse
from django.core.paginator import Paginator

from .models import ExamToken
from student.models import Student
from teachers.models import Teacher
from subject.models import Subject
from Academic.models import Batch, Semester, Section, Discipline

# ========== HOME VIEW ==========

def index(request):
    """Home page"""
    total_tokens = ExamToken.objects.count()
    active_tokens = ExamToken.objects.filter(status__in=['generated', 'printed', 'verified']).count()
    expired_tokens = ExamToken.objects.filter(status='expired').count()
    students_with_tokens = ExamToken.objects.values('student').distinct().count()
    
    context = {
        'total_tokens': total_tokens,
        'active_tokens': active_tokens,
        'expired_tokens': expired_tokens,
        'students_with_tokens': students_with_tokens,
        'recent_tokens': ExamToken.objects.order_by('-issue_date')[:5],
    }
    return render(request, 'token_app/index.html', context)

# ========== TOKEN LISTING VIEWS ==========

def all_tokens(request):
    """View all tokens with filters"""
    tokens = ExamToken.objects.all().order_by('-issue_date')
    
    # Filtering
    status = request.GET.get('status', '')
    batch_id = request.GET.get('batch', '')
    semester_id = request.GET.get('semester', '')
    
    if status:
        tokens = tokens.filter(status=status)
    if batch_id:
        tokens = tokens.filter(batch_id=batch_id)
    if semester_id:
        tokens = tokens.filter(semester_id=semester_id)
    
    # Search
    search = request.GET.get('search', '')
    if search:
        tokens = tokens.filter(
            Q(token_number__icontains=search) |
            Q(student__student_id__icontains=search) |
            Q(student__first_name__icontains=search) |
            Q(student__last_name__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(tokens, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get filter data
    batches = Batch.objects.all()
    semesters = Semester.objects.all()
    
    context = {
        'page_obj': page_obj,
        'tokens': page_obj,
        'batches': batches,
        'semesters': semesters,
        'status_choices': ExamToken.TokenStatus.choices,
        'selected_status': status,
        'selected_batch': batch_id,
        'selected_semester': semester_id,
        'search': search,
    }
    return render(request, 'token_app/all_tokens.html', context)

def student_tokens(request, student_id=None):
    """View tokens for a specific student"""
    students = Student.objects.all().order_by('student_id')[:50]
    
    if student_id:
        student = get_object_or_404(Student, id=student_id)
    elif request.GET.get('student'):
        student_id = request.GET.get('student')
        student = get_object_or_404(Student, id=student_id)
    else:
        student = Student.objects.first()
        if not student:
            messages.error(request, "No students found")
            return redirect('token_app:index')
    
    tokens = ExamToken.objects.filter(student=student).order_by('-issue_date')
    
    # Calculate expired tokens count
    expired_tokens = tokens.filter(
        Q(valid_until__lt=date.today()) | Q(status='expired')
    ).count()
    
    context = {
        'student': student,
        'tokens': tokens,
        'students': students,
        'total_tokens': tokens.count(),
        'active_tokens': tokens.filter(status__in=['generated', 'printed', 'verified']).count(),
        'expired_tokens': expired_tokens,
    }
    return render(request, 'token_app/student_tokens.html', context)

def token_detail(request, token_id):
    """View single token details"""
    token = get_object_or_404(ExamToken, id=token_id)
    
    context = {
        'token': token,
        'eligible_subjects': token.eligible_subjects.all(),
        'status_choices': ExamToken.TokenStatus.choices,
        'teachers': Teacher.objects.all()[:10],
    }
    return render(request, 'token_app/token_detail.html', context)

# ========== CREATE TOKEN VIEWS ==========

def create_token(request):
    """Create a new exam token"""
    if request.method == 'POST':
        try:
            student_id = request.POST.get('student')
            valid_until = request.POST.get('valid_until')
            subject_ids = request.POST.getlist('subjects')
            
            student = get_object_or_404(Student, id=student_id)
            
            # Create token
            token = ExamToken.objects.create(
                student=student,
                semester=student.semester,
                batch=student.batch,
                section=student.section,
                discipline=student.discipline,
                issue_date=date.today(),
                valid_until=valid_until,
                status='generated'
            )
            
            # Add eligible subjects
            if subject_ids:
                token.eligible_subjects.set(subject_ids)
            
            messages.success(request, f'Token #{token.token_number} created successfully!')
            return redirect('token_app:token_detail', token_id=token.id)
            
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
    
    # GET request
    students = Student.objects.all().order_by('student_id')[:50]
    subjects = Subject.objects.all()[:100]
    batches = Batch.objects.all()
    semesters = Semester.objects.all()
    
    context = {
        'students': students,
        'subjects': subjects,
        'batches': batches,
        'semesters': semesters,
        'today': date.today(),
        'default_valid_until': date.today() + timedelta(days=30),
    }
    return render(request, 'token_app/create_token.html', context)

def create_token_for_student(request, student_id):
    """Create token for a specific student"""
    student = get_object_or_404(Student, id=student_id)
    
    if request.method == 'POST':
        try:
            valid_until = request.POST.get('valid_until')
            subject_ids = request.POST.getlist('subjects')
            
            # Create token
            token = ExamToken.objects.create(
                student=student,
                semester=student.semester,
                batch=student.batch,
                section=student.section,
                discipline=student.discipline,
                issue_date=date.today(),
                valid_until=valid_until,
                status='generated'
            )
            
            # Add eligible subjects
            if subject_ids:
                token.eligible_subjects.set(subject_ids)
            
            messages.success(request, f'Token #{token.token_number} created for {student}!')
            return redirect('token_app:token_detail', token_id=token.id)
            
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
    
    # GET request
    subjects = Subject.objects.filter(
        semester=student.semester,
        desciplain=student.discipline
    )
    
    context = {
        'student': student,
        'subjects': subjects,
        'today': date.today(),
        'default_valid_until': date.today() + timedelta(days=30),
    }
    return render(request, 'token_app/create_token_for_student.html', context)

# ========== TOKEN ACTION VIEWS ==========

def update_token_status(request, token_id):
    """Update token status"""
    token = get_object_or_404(ExamToken, id=token_id)
    
    if request.method == 'POST':
        status = request.POST.get('status')
        notes = request.POST.get('notes', '')
        teacher_id = request.POST.get('teacher')
        
        if status == 'verified' and teacher_id:
            teacher = get_object_or_404(Teacher, id=teacher_id)
            token.verify_token(teacher, notes)
            messages.success(request, f'Token #{token.token_number} verified successfully!')
        
        elif status == 'used':
            token.mark_as_used()
            messages.success(request, f'Token #{token.token_number} marked as used!')
        
        elif status == 'cancelled' and teacher_id:
            teacher = get_object_or_404(Teacher, id=teacher_id)
            token.cancel_token(teacher, notes)
            messages.success(request, f'Token #{token.token_number} cancelled!')
        
        else:
            token.status = status
            token.save()
            messages.success(request, f'Token status updated to {token.get_status_display()}')
        
        return redirect('token_app:token_detail', token_id=token.id)
    
    return redirect('token_app:token_detail', token_id=token.id)

def verify_token(request, token_id):
    """Quick verify token"""
    token = get_object_or_404(ExamToken, id=token_id)
    
    # For demo, use first teacher
    teacher = Teacher.objects.first()
    if teacher:
        token.verify_token(teacher, "Verified via quick action")
        messages.success(request, f'Token #{token.token_number} verified!')
    else:
        messages.error(request, "No teacher found for verification")
    
    return redirect('token_app:token_detail', token_id=token.id)

def print_token(request, token_id):
    """Print token view"""
    token = get_object_or_404(ExamToken, id=token_id)
    
    # Update status to printed if it's generated
    if token.status == 'generated':
        token.status = 'printed'
        token.save()
    
    context = {
        'token': token,
        'eligible_subjects': token.eligible_subjects.all(),
    }
    return render(request, 'token_app/print_token.html', context)

# ========== API/JSON VIEWS ==========

def get_student_info(request, student_id):
    """Get student info for AJAX"""
    student = get_object_or_404(Student, id=student_id)
    
    data = {
        'id': student.id,
        'student_id': student.student_id,
        'name': f"{student.first_name} {student.last_name}",
        'batch': student.batch.name if student.batch else '',
        'semester': student.semester.number if student.semester else '',
        'section': student.section.name if student.section else '',
        'discipline': student.discipline.name if student.discipline else '',
    }
    return JsonResponse(data)

def get_student_subjects(request, student_id):
    """Get subjects for a student"""
    student = get_object_or_404(Student, id=student_id)
    
    subjects = Subject.objects.filter(
        semester=student.semester,
        desciplain=student.discipline
    ).values('id', 'code', 'name', 'credit_hours')
    
    return JsonResponse(list(subjects), safe=False)

def check_token_validity(request, token_number):
    """Check if token is valid (for scanning)"""
    try:
        token = ExamToken.objects.get(token_number=token_number)
        
        data = {
            'valid': token.is_valid,
            'token_number': token.token_number,
            'student': str(token.student),
            'status': token.get_status_display(),
            'expiry': token.valid_until.strftime('%Y-%m-%d'),
            'days_left': token.days_until_expiry,
        }
    except ExamToken.DoesNotExist:
        data = {
            'valid': False,
            'error': 'Token not found'
        }
    
    return JsonResponse(data)

# ========== DASHBOARD/STATISTICS VIEWS ==========

def dashboard(request):
    """Admin dashboard with statistics"""
    total_tokens = ExamToken.objects.count()
    
    # Status distribution
    status_counts = {}
    for status_code, status_name in ExamToken.TokenStatus.choices:
        status_counts[status_name] = ExamToken.objects.filter(status=status_code).count()
    
    # Recent tokens
    recent_tokens = ExamToken.objects.order_by('-issue_date')[:10]
    
    # Active tokens (not expired or cancelled)
    active_tokens = ExamToken.objects.filter(
        status__in=['generated', 'printed', 'verified']
    ).count()
    
    # Expiring soon (next 7 days)
    expiring_soon = ExamToken.objects.filter(
        valid_until__gte=date.today(),
        valid_until__lte=date.today() + timedelta(days=7),
        status__in=['generated', 'printed', 'verified']
    ).count()
    
    # Expired tokens
    expired = ExamToken.objects.filter(
        Q(valid_until__lt=date.today()) | Q(status='expired')
    ).exclude(
        status__in=['used', 'cancelled']
    ).count()
    
    # Students with tokens
    students_with_tokens = ExamToken.objects.values('student').distinct().count()
    
    context = {
        'total_tokens': total_tokens,
        'active_tokens': active_tokens,
        'expired_tokens': expired,
        'students_with_tokens': students_with_tokens,
        'status_counts': status_counts,
        'recent_tokens': recent_tokens,
        'expiring_soon': expiring_soon,
    }
    return render(request, 'token_app/dashboard.html', context)

def statistics(request):
    """Detailed statistics"""
    from django.db.models import Count, Avg
    from django.db.models.functions import Coalesce
    
    total_tokens = ExamToken.objects.count()
    
    # Tokens per batch with percentages
    batch_stats = ExamToken.objects.values('batch__name').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Add percentages
    for stat in batch_stats:
        stat['percentage'] = (stat['count'] / total_tokens * 100) if total_tokens > 0 else 0
    
    # Tokens per semester with percentages
    semester_stats = ExamToken.objects.values('semester__number').annotate(
        count=Count('id')
    ).order_by('semester__number')
    
    for stat in semester_stats:
        stat['percentage'] = (stat['count'] / total_tokens * 100) if total_tokens > 0 else 0
    
    # Tokens per status
    status_stats = ExamToken.objects.values('status').annotate(
        count=Count('id')
    )
    
    # Status counts dictionary
    status_counts = {}
    for status_code, status_name in ExamToken.TokenStatus.choices:
        count = ExamToken.objects.filter(status=status_code).count()
        status_counts[status_name] = count
    
    # Monthly trend (last 6 months)
    monthly_data = []
    for i in range(5, -1, -1):
        month_start = (date.today().replace(day=1) - timedelta(days=30*i)).replace(day=1)
        if i > 0:
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        else:
            month_end = date.today()
        
        count = ExamToken.objects.filter(
            issue_date__gte=month_start,
            issue_date__lte=month_end
        ).count()
        monthly_data.append({
            'month': month_start.strftime('%b %Y'),
            'count': count
        })
    
    # Additional statistics
    students_count = Student.objects.filter(exam_tokens__isnull=False).distinct().count()
    active_tokens = ExamToken.objects.filter(status__in=['generated', 'printed', 'verified']).count()
    avg_tokens_per_student = total_tokens / students_count if students_count > 0 else 0
    
    # Most active batch
    most_active_batch = batch_stats[0]['batch__name'] if batch_stats else "N/A"
    
    # Most common status
    most_common_status = max(status_counts, key=status_counts.get) if status_counts else "N/A"
    
    context = {
        'total_tokens': total_tokens,
        'active_tokens': active_tokens,
        'students_count': students_count,
        'batch_stats': batch_stats,
        'semester_stats': semester_stats,
        'status_stats': status_stats,
        'status_counts': status_counts,
        'monthly_data': monthly_data,
        'avg_tokens_per_student': avg_tokens_per_student,
        'most_active_batch': most_active_batch,
        'most_common_status': most_common_status,
    }
    return render(request, 'token_app/statistics.html', context)
def bulk_create_tokens(request):
    """Create tokens for multiple students with eligibility checks"""
    
    # Handle AJAX request to get students count/filtered list
    if request.method == 'GET' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            discipline_id = request.GET.get('discipline')
            batch_id = request.GET.get('batch')
            semester_id = request.GET.get('semester')
            section_id = request.GET.get('section')
            
            # Validate required parameters
            if not all([discipline_id, batch_id, semester_id, section_id]):
                return JsonResponse({
                    'error': 'Missing required parameters',
                    'count': 0,
                    'students': []
                }, status=400)
            
            students = Student.objects.all()
            
            if discipline_id:
                students = students.filter(discipline_id=discipline_id)
            if batch_id:
                students = students.filter(batch_id=batch_id)
            if semester_id:
                students = students.filter(semester_id=semester_id)
            if section_id:
                students = students.filter(section_id=section_id)
            
            # Get student data with eligibility info
            student_data = []
            for student in students[:100]:
                try:
                    eligibility = check_student_eligibility(student, semester_id)
                    
                    # Format discipline name correctly
                    discipline_name = ""
                    if student.discipline:
                        discipline_name = f"{student.discipline.program} in {student.discipline.field}"
                    
                    student_data.append({
                        'id': student.id,
                        'student_id': student.student_id,
                        'name': f"{student.first_name} {student.last_name}",
                        'batch': student.batch.name if student.batch else '',
                        'semester': student.semester.number if student.semester else '',
                        'section': student.section.name if student.section else '',
                        'discipline': discipline_name,
                        'eligible': eligibility['eligible'],
                        'reasons': eligibility['reasons'],
                        'has_token': eligibility['has_token'],
                    })
                except Exception as e:
                    print(f"Error processing student {student.id}: {str(e)}")
                    student_data.append({
                        'id': student.id,
                        'student_id': student.student_id,
                        'name': f"{student.first_name} {student.last_name}",
                        'batch': student.batch.name if student.batch else '',
                        'semester': student.semester.number if student.semester else '',
                        'section': student.section.name if student.section else '',
                        'discipline': '',
                        'eligible': False,
                        'reasons': [f"Error checking eligibility"],
                        'has_token': False,
                    })
            
            return JsonResponse({
                'count': students.count(),
                'students': student_data
            })
            
        except Exception as e:
            print(f"AJAX Error: {str(e)}")
            return JsonResponse({
                'error': str(e),
                'count': 0,
                'students': []
            }, status=500)
    
    # Handle POST request to create tokens
    if request.method == 'POST':
        try:
            discipline_id = request.POST.get('discipline')
            batch_id = request.POST.get('batch')
            semester_id = request.POST.get('semester')
            section_id = request.POST.get('section')
            valid_until_str = request.POST.get('valid_until')
            
            # Convert string date to date object
            from datetime import datetime
            valid_until = datetime.strptime(valid_until_str, '%Y-%m-%d').date()
            
            # Get selected student IDs from the form
            selected_students = request.POST.getlist('selected_students')
            
            if not selected_students:
                messages.error(request, "No students selected")
                return redirect('token_app:bulk_create_tokens')
            
            created_count = 0
            failed_students = []
            
            for student_id in selected_students:
                student = get_object_or_404(Student, id=student_id)
                
                # Check eligibility again before creating
                eligibility = check_student_eligibility(student, semester_id)
                
                if not eligibility['eligible']:
                    failed_students.append({
                        'name': str(student),
                        'reasons': eligibility['reasons']
                    })
                    continue
                
                # Check if token already exists
                existing = ExamToken.objects.filter(
                    student=student,
                    semester_id=semester_id,
                    issue_date__year=date.today().year
                ).exists()
                
                if existing:
                    failed_students.append({
                        'name': str(student),
                        'reasons': ['Token already exists for this semester']
                    })
                    continue
                
                # Get eligible subjects (excluding those with attendance shortage)
                eligible_subjects = get_eligible_subjects(student, semester_id)
                
                # Create token
                token = ExamToken.objects.create(
                    student=student,
                    semester_id=semester_id,
                    batch_id=batch_id,
                    section_id=section_id,
                    discipline_id=discipline_id,
                    issue_date=date.today(),
                    valid_until=valid_until,  # Now it's a date object, not a string
                    status='generated'
                )
                
                # Add eligible subjects to token
                if eligible_subjects.exists():
                    token.eligible_subjects.set(eligible_subjects)
                
                # Store eligibility data in JSON fields
                token.attendance_short = get_attendance_shortages(student, semester_id)
                token.fee_defaulters = check_fee_status(student)
                token.prerequisite_missing = get_prerequisite_failures(student, semester_id)
                token.save()
                
                print(f"DEBUG: Token created - ID: {token.id}, Number: {token.token_number}, Student: {student}")
                created_count += 1
            
            print(f"DEBUG: Total tokens created: {created_count}")
            print(f"DEBUG: Total tokens in database now: {ExamToken.objects.count()}")
            
            if created_count > 0:
                messages.success(request, f'{created_count} tokens created successfully!')
            
            if failed_students:
                error_msg = f"Failed for {len(failed_students)} students: "
                for fail in failed_students[:3]:
                    error_msg += f"{fail['name']} ({', '.join(fail['reasons'])}); "
                if len(failed_students) > 3:
                    error_msg += f"... and {len(failed_students) - 3} more"
                messages.warning(request, error_msg)
            
            return redirect('token_app:all_tokens')
            
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            print(f"Error in bulk_create_tokens POST: {str(e)}")
            import traceback
            traceback.print_exc()
    
    # GET request - show form
    disciplines = Discipline.objects.all()
    batches = Batch.objects.all()
    semesters = Semester.objects.all()
    sections = Section.objects.all()
    
    context = {
        'disciplines': disciplines,
        'batches': batches,
        'semesters': semesters,
        'sections': sections,
        'today': date.today(),
        'default_valid_until': date.today() + timedelta(days=30),
    }
    return render(request, 'token_app/bulk_create_tokens.html', context)

# ====R FUNCTIONS FOR ELIGIBILITY CHECKS ==========

def check_student_eligibility(student, semester_id):
    """Check if student is eligible for exam token"""
    reasons = []
    eligible = True
    has_token = False
    
    try:
        # Check fee status
        fee_status = check_fee_status(student)
        if not fee_status['clear']:
            eligible = False
            reasons.append(f"Fee defaulter")
        
        # Check attendance shortages
        attendance_issues = get_attendance_shortages(student, semester_id)
        if attendance_issues:
            eligible = False
            reasons.append(f"Attendance shortage")
        
        # Check prerequisite failures
        prerequisite_issues = get_prerequisite_failures(student, semester_id)
        if prerequisite_issues:
            eligible = False
            reasons.append(f"Prerequisite failure")
        
        # Check if already has token
        has_token = ExamToken.objects.filter(
            student=student,
            semester_id=semester_id,
            issue_date__year=date.today().year
        ).exists()
        
        if has_token:
            eligible = False
            reasons.append("Token exists")
            
    except Exception as e:
        print(f"Error in check_student_eligibility: {str(e)}")
        eligible = False
        reasons.append(f"Error checking eligibility")
    
    return {
        'eligible': eligible,
        'reasons': reasons,
        'has_token': has_token
    }


def check_fee_status(student):
    """Check if student has cleared all fees"""
    try:
        # Try to import fee model - handle if app doesn't exist
        try:
            from fee_system.models import UploadFee
            
            # Get pending fees for the student
            pending_fees = UploadFee.objects.filter(
                student=student,
                is_fully_paid=False
            )
            
            if pending_fees.exists():
                total_due = 0
                for fee in pending_fees:
                    total_due += float(fee.remaining_amount if hasattr(fee, 'remaining_amount') else 0)
                return {
                    'clear': False,
                    'details': f"Pending fees: ₹{total_due}"
                }
            
            return {'clear': True, 'details': 'All fees cleared'}
            
        except ImportError:
            # If fee_system app doesn't exist, assume fees are cleared
            return {'clear': True, 'details': 'Fee system not available'}
            
    except Exception as e:
        print(f"Error checking fee status: {str(e)}")
        return {'clear': True, 'details': 'Fee check error'}


def get_attendance_shortages(student, semester_id):
    """Get subjects where student has attendance below minimum"""
    shortages = {}
    
    try:
        # Try to import attendance model
        try:
            from attendance.models import Attendance
            
            # Get minimum attendance percentage (default 75%)
            min_attendance = 75
            
            # Get all subjects for this semester
            subjects = Subject.objects.filter(semester_id=semester_id)
            
            for subject in subjects:
                # Get attendance records for this student and subject
                attendance_records = Attendance.objects.filter(
                    student=student,
                    subject=subject
                )
                
                total_classes = attendance_records.count()
                if total_classes > 0:
                    present_classes = attendance_records.filter(status='P').count()
                    percentage = (present_classes / total_classes) * 100
                    
                    if percentage < min_attendance:
                        shortages[subject.code] = round(percentage, 2)
            
            return shortages
            
        except ImportError:
            # If attendance app doesn't exist
            return {}
            
    except Exception as e:
        print(f"Error checking attendance: {str(e)}")
        return {}


def get_prerequisite_failures(student, semester_id):
    """Check if student has failed prerequisite subjects"""
    failures = []
    
    try:
        # Try to import exam models
        try:
            from exam_mang.models import ExamResult, SubjectComprehensiveResult
            
            # Get all subjects for this semester
            subjects = Subject.objects.filter(semester_id=semester_id)
            
            for subject in subjects:
                # Check prerequisites
                prerequisites = subject.prerequisites.all()
                
                for prereq in prerequisites:
                    # Check if student passed this prerequisite
                    try:
                        # Check in comprehensive results
                        comp_result = SubjectComprehensiveResult.objects.get(
                            student=student,
                            subject_mark_component__subject=prereq
                        )
                        
                        if hasattr(comp_result, 'grade') and comp_result.grade == 'F':
                            failures.append(f"{prereq.code}")
                            
                    except SubjectComprehensiveResult.DoesNotExist:
                        # Check in exam results
                        failed_results = ExamResult.objects.filter(
                            student=student,
                            exam__subject_mark_component__subject=prereq,
                            grade='F'
                        ).exists()
                        
                        if failed_results:
                            failures.append(f"{prereq.code}")
            
            return list(set(failures))  # Remove duplicates
            
        except ImportError:
            # If exam_mang app doesn't exist
            return []
            
    except Exception as e:
        print(f"Error checking prerequisites: {str(e)}")
        return []


def get_eligible_subjects(student, semester_id):
    """Get subjects student is eligible for (excluding those with attendance shortage)"""
    from subject.models import Subject
    
    # Get all subjects for this semester
    subjects = Subject.objects.filter(semester_id=semester_id)
    
    # Get attendance shortages
    attendance_issues = get_attendance_shortages(student, semester_id)
    
    # Filter out subjects with attendance issues
    eligible_subjects = []
    for subject in subjects:
        if subject.code not in attendance_issues:
            # Check prerequisites
            prerequisites_passed = check_prerequisites_passed(student, subject)
            if prerequisites_passed:
                eligible_subjects.append(subject.id)
    
    return Subject.objects.filter(id__in=eligible_subjects)


def check_prerequisites_passed(student, subject):
    """Check if student has passed all prerequisites for a subject"""
    try:
        from exam_mang.models import SubjectComprehensiveResult, ExamResult
        
        prerequisites = subject.prerequisites.all()
        
        for prereq in prerequisites:
            try:
                # Check comprehensive result
                comp_result = SubjectComprehensiveResult.objects.get(
                    student=student,
                    subject_mark_component__subject=prereq
                )
                if hasattr(comp_result, 'grade') and comp_result.grade == 'F':
                    return False
            except SubjectComprehensiveResult.DoesNotExist:
                # Check exam results
                failed = ExamResult.objects.filter(
                    student=student,
                    exam__subject_mark_component__subject=prereq,
                    grade='F'
                ).exists()
                
                if failed:
                    return False
                
                # No record means not attempted - consider as failed for eligibility
                return False
        
        return True
        
    except ImportError:
        # If exam_mang app doesn't exist, assume prerequisites are passed
        return True
    except Exception as e:
        print(f"Error checking prerequisites passed: {str(e)}")
        return False

    
def token_generated_students(request):
    """View all students who have generated tokens"""
    from django.db.models import Count, Q
    
    # Get all students with tokens
    students_with_tokens = Student.objects.filter(
        exam_tokens__isnull=False
    ).distinct().order_by('student_id')
    
    # Get filter parameters
    discipline_id = request.GET.get('discipline')
    batch_id = request.GET.get('batch')
    semester_id = request.GET.get('semester')
    section_id = request.GET.get('section')
    status = request.GET.get('status')
    
    # Apply filters
    if discipline_id:
        students_with_tokens = students_with_tokens.filter(discipline_id=discipline_id)
    if batch_id:
        students_with_tokens = students_with_tokens.filter(batch_id=batch_id)
    if semester_id:
        students_with_tokens = students_with_tokens.filter(semester_id=semester_id)
    if section_id:
        students_with_tokens = students_with_tokens.filter(section_id=section_id)
    
    # Search functionality
    search = request.GET.get('search', '')
    if search:
        students_with_tokens = students_with_tokens.filter(
            Q(student_id__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    
    # Get token statistics for each student
    student_data = []
    for student in students_with_tokens:
        tokens = ExamToken.objects.filter(student=student)
        
        # Get token counts by status
        total_tokens = tokens.count()
        active_tokens = tokens.filter(status__in=['generated', 'printed', 'verified']).count()
        expired_tokens = tokens.filter(status='expired').count()
        used_tokens = tokens.filter(status='used').count()
        
        # Get latest token
        latest_token = tokens.order_by('-issue_date').first()
        
        student_data.append({
            'student': student,
            'total_tokens': total_tokens,
            'active_tokens': active_tokens,
            'expired_tokens': expired_tokens,
            'used_tokens': used_tokens,
            'latest_token': latest_token,
            'latest_token_status': latest_token.get_status_display() if latest_token else 'No Token',
            'latest_token_date': latest_token.issue_date if latest_token else None,
            'latest_token_valid': latest_token.valid_until if latest_token else None,
            'token_numbers': [t.token_number for t in tokens[:5]],  # Last 5 token numbers
        })
    
    # Pagination
    paginator = Paginator(student_data, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get filter data
    disciplines = Discipline.objects.all()
    batches = Batch.objects.all()
    semesters = Semester.objects.all()
    sections = Section.objects.all()
    
    # Format discipline names
    formatted_disciplines = []
    for discipline in disciplines:
        formatted_disciplines.append({
            'id': discipline.id,
            'name': f"{discipline.program} in {discipline.field}"
        })
    
    context = {
        'page_obj': page_obj,
        'students_data': page_obj,
        'disciplines': disciplines,
        'formatted_disciplines': formatted_disciplines,
        'batches': batches,
        'semesters': semesters,
        'sections': sections,
        'selected_discipline': discipline_id,
        'selected_batch': batch_id,
        'selected_semester': semester_id,
        'selected_section': section_id,
        'selected_status': status,
        'search': search,
        'total_students': students_with_tokens.count(),
        'total_tokens': ExamToken.objects.count(),
        'active_tokens_count': ExamToken.objects.filter(status__in=['generated', 'printed', 'verified']).count(),
    }
    return render(request, 'token_app/token_generated_students.html', context)


def student_token_history(request, student_id):
    """View complete token history for a specific student"""
    student = get_object_or_404(Student, id=student_id)
    tokens = ExamToken.objects.filter(student=student).order_by('-issue_date')
    
    # Statistics
    total_tokens = tokens.count()
    active_tokens = tokens.filter(status__in=['generated', 'printed', 'verified']).count()
    expired_tokens = tokens.filter(status='expired').count()
    used_tokens = tokens.filter(status='used').count()
    
    # Token status distribution
    status_counts = {}
    for status_code, status_name in ExamToken.TokenStatus.choices:
        status_counts[status_name] = tokens.filter(status=status_code).count()
    
    context = {
        'student': student,
        'tokens': tokens,
        'total_tokens': total_tokens,
        'active_tokens': active_tokens,
        'expired_tokens': expired_tokens,
        'used_tokens': used_tokens,
        'status_counts': status_counts,
    }
    return render(request, 'token_app/student_token_history.html', context)
def debug_tokens(request):
    """Debug view to check tokens"""
    tokens = ExamToken.objects.all()
    token_list = []
    for token in tokens:
        token_list.append({
            'id': token.id,
            'number': token.token_number,
            'student': str(token.student),
            'status': token.status,
            'date': str(token.issue_date)
        })
    
    return JsonResponse({
        'total_tokens': tokens.count(),
        'tokens': token_list
    })

def student_token_detail(request, student_id, token_id):
    """View specific token details for a student"""
    student = get_object_or_404(Student, id=student_id)
    token = get_object_or_404(ExamToken, id=token_id, student=student)
    
    context = {
        'student': student,
        'token': token,
        'eligible_subjects': token.eligible_subjects.all(),
    }
    return render(request, 'token_app/token_detail.html', context)