# token_app/views.py - COMPLETE FIXED VERSION

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
    
    status = request.GET.get('status', '')
    batch_id = request.GET.get('batch', '')
    semester_id = request.GET.get('semester', '')
    
    if status:
        tokens = tokens.filter(status=status)
    if batch_id:
        tokens = tokens.filter(batch_id=batch_id)
    if semester_id:
        tokens = tokens.filter(semester_id=semester_id)
    
    search = request.GET.get('search', '')
    if search:
        tokens = tokens.filter(
            Q(token_number__icontains=search) |
            Q(student__student_id__icontains=search) |
            Q(student__first_name__icontains=search) |
            Q(student__last_name__icontains=search)
        )
    
    paginator = Paginator(tokens, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
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


# ========== ELIGIBILITY CHECK FUNCTIONS ==========

def check_student_eligibility(student, semester_id):
    """
    Check if student is eligible for exam token
    Returns: dict with 'eligible', 'reasons', 'has_token'
    """
    reasons = []
    eligible = True
    has_token = False
    
    try:
        # 1. Check if student already has a token for this semester
        has_token = ExamToken.objects.filter(
            student=student,
            semester_id=semester_id,
            status__in=['generated', 'printed', 'verified']
        ).exists()
        
        if has_token:
            eligible = False
            reasons.append("Already has a token for this semester")
        
        # 2. Check if student has any eligible subjects
        eligible_subjects = get_eligible_subjects_for_bulk(student, semester_id)
        if not eligible_subjects:
            eligible = False
            reasons.append("No eligible subjects found")
        
        # 3. Check overall attendance
        overall_attendance = get_student_overall_attendance(student)
        if overall_attendance is not None and overall_attendance < 75:
            eligible = False
            reasons.append(f"Overall attendance below 75% ({overall_attendance:.1f}%)")
            
    except Exception as e:
        print(f"Error in check_student_eligibility: {str(e)}")
        eligible = False
        reasons.append(f"System error: {str(e)[:50]}")
    
    # If no issues, add a default message
    if eligible and not reasons:
        reasons.append(f"✅ Eligible for {len(eligible_subjects)} subjects")
    
    return {
        'eligible': eligible,
        'reasons': reasons,
        'has_token': has_token
    }


def get_student_overall_attendance(student):
    """Get student's overall attendance percentage"""
    try:
        from attendance.models import Attendance
        
        attendance_records = Attendance.objects.filter(student=student)
        total_classes = attendance_records.count()
        
        if total_classes == 0:
            return None
        
        present_classes = attendance_records.filter(status='P').count()
        return (present_classes / total_classes) * 100
        
    except ImportError:
        return None
    except Exception as e:
        print(f"Error getting overall attendance: {str(e)}")
        return None


def get_eligible_subjects_for_bulk(student, semester_id):
    """
    Get subjects student is eligible for based on:
    1. Subject is assigned to student's semester
    2. Attendance ≥ 75% in that subject
    3. All prerequisites passed
    4. Fee cleared for that subject
    """
    eligible_subjects = []
    
    try:
        from exam_manag.models import SubjectMarkComponents
        
        print(f"\n===== Checking eligibility for student {student.student_id} =====")
        
        # Get subject IDs for this semester
        subject_ids = SubjectMarkComponents.objects.filter(
            semester_id=semester_id,
            discipline=student.discipline,
            batch=student.batch
        ).values_list('subject_id', flat=True).distinct()
        
        # If no subjects found, try without discipline and batch
        if not subject_ids:
            subject_ids = SubjectMarkComponents.objects.filter(
                semester_id=semester_id
            ).values_list('subject_id', flat=True).distinct()
        
        print(f"Found {len(subject_ids)} subjects for semester {semester_id}")
        
        subjects = Subject.objects.filter(id__in=subject_ids, is_active=True)
        
        for subject in subjects:
            print(f"\n  Checking: {subject.code} - {subject.name}")
            
            is_eligible = True
            reasons = []
            
            # 1. Check attendance for this subject
            attendance_ok, attendance_pct = check_attendance_for_subject(student, subject)
            if not attendance_ok:
                is_eligible = False
                reasons.append(f"Attendance {attendance_pct:.1f}% < 75%")
            
            # 2. Check prerequisites for this subject
            prerequisites_ok, prereq_failures = check_prerequisites_for_subject(student, subject)
            if not prerequisites_ok:
                is_eligible = False
                reasons.append(f"Prerequisite(s) not passed: {', '.join(prereq_failures)}")
            
            # 3. Check fee status for this subject (if fee_system exists)
            fee_ok, fee_details = check_fee_status_for_subject(student, subject)
            if not fee_ok:
                is_eligible = False
                reasons.append(f"Fee pending: {fee_details}")
            
            if is_eligible:
                eligible_subjects.append(subject)
                print(f"    ✅ ELIGIBLE")
            else:
                print(f"    ❌ NOT ELIGIBLE: {', '.join(reasons)}")
        
        print(f"\nTotal eligible subjects: {len(eligible_subjects)}")
        return eligible_subjects
        
    except ImportError as e:
        print(f"Error importing SubjectMarkComponents: {e}")
        # Fallback: Get subjects directly from Subject model
        subjects = Subject.objects.filter(is_active=True)
        return list(subjects)
    except Exception as e:
        print(f"Error in get_eligible_subjects_for_bulk: {str(e)}")
        import traceback
        traceback.print_exc()
        return []


def check_attendance_for_subject(student, subject):
    """Check if student has ≥75% attendance in a subject"""
    try:
        from attendance.models import Attendance
        
        # Get attendance records for this student and subject
        attendance_records = Attendance.objects.filter(
            student=student,
            subject=subject
        )
        
        total_classes = attendance_records.count()
        if total_classes == 0:
            return False, 0.0
        
        present_classes = attendance_records.filter(status='P').count()
        percentage = (present_classes / total_classes) * 100
        
        # Minimum attendance requirement
        min_attendance = 75
        
        return percentage >= min_attendance, percentage
        
    except ImportError:
        # Attendance app not available - assume eligible
        return True, 100.0
    except Exception as e:
        print(f"Attendance check error for {subject.code}: {str(e)}")
        return True, 100.0


def check_prerequisites_for_subject(student, subject):
    """Check if student has passed all prerequisites for a subject"""
    try:
        from exam_manag.models import SubjectComprehensiveResult
        
        # Get prerequisites for this subject
        if hasattr(subject, 'prerequisites'):
            prerequisites = subject.prerequisites.all()
            
            if not prerequisites.exists():
                return True, []  # No prerequisites, so eligible
            
            failures = []
            for prereq in prerequisites:
                try:
                    # Check if student passed this prerequisite
                    comp_result = SubjectComprehensiveResult.objects.get(
                        student=student,
                        subject_mark_component__subject=prereq
                    )
                    
                    if hasattr(comp_result, 'grade') and comp_result.grade == 'F':
                        failures.append(prereq.code)
                        
                except SubjectComprehensiveResult.DoesNotExist:
                    # No result found - assume failed
                    failures.append(prereq.code)
            
            return len(failures) == 0, failures
        
        return True, []  # No prerequisites field
        
    except ImportError:
        # exam_manag app not available - assume eligible
        return True, []
    except Exception as e:
        print(f"Prerequisite check error for {subject.code}: {str(e)}")
        return True, []


def check_fee_status_for_subject(student, subject):
    """Check if student has cleared fee for a specific subject"""
    try:
        from fee_system.models import UploadFee
        
        # Check if there are any pending fees for this student
        pending_fees = UploadFee.objects.filter(
            student=student,
            is_fully_paid=False
        )
        
        if pending_fees.exists():
            total_due = sum(float(fee.remaining_amount if hasattr(fee, 'remaining_amount') else 0) 
                           for fee in pending_fees)
            return False, f"₹{total_due:.2f} pending"
        
        return True, "Fee cleared"
        
    except ImportError:
        # Fee system not available - assume cleared
        return True, "Fee system not available"
    except Exception as e:
        print(f"Fee check error for {subject.code}: {str(e)}")
        return True, "Fee check skipped"


# ========== BULK CREATE TOKENS ==========

def bulk_create_tokens(request):
    """Create tokens for multiple students with eligibility checks"""
    
    # Handle AJAX request to get students
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
                    eligible_subjects = get_eligible_subjects_for_bulk(student, semester_id)
                    
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
                        'reasons_display': ', '.join(eligibility['reasons']) if eligibility['reasons'] else '✅ Eligible',
                        'eligible_subjects_count': len(eligible_subjects),
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
                        'reasons': [f"Error: {str(e)[:50]}"],
                        'has_token': False,
                        'reasons_display': f"Error: {str(e)[:50]}",
                        'eligible_subjects_count': 0,
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
            
            from datetime import datetime
            valid_until = datetime.strptime(valid_until_str, '%Y-%m-%d').date()
            
            selected_students = request.POST.getlist('selected_students')
            
            if not selected_students:
                messages.error(request, "No students selected")
                return redirect('token_app:bulk_create_tokens')
            
            created_count = 0
            skipped_count = 0
            not_eligible_students = []
            
            for student_id in selected_students:
                student = get_object_or_404(Student, id=student_id)
                
                # Check if student is eligible for a token
                eligibility = check_student_eligibility(student, semester_id)
                
                if not eligibility['eligible']:
                    # Student is NOT eligible - skip creating token
                    not_eligible_students.append({
                        'name': f"{student.first_name} {student.last_name}",
                        'reasons': eligibility['reasons']
                    })
                    skipped_count += 1
                    continue
                
                # Get eligible subjects for this student
                eligible_subjects = get_eligible_subjects_for_bulk(student, semester_id)
                
                # If no eligible subjects, skip
                if not eligible_subjects:
                    not_eligible_students.append({
                        'name': f"{student.first_name} {student.last_name}",
                        'reasons': ['No eligible subjects found']
                    })
                    skipped_count += 1
                    continue
                
                # Create token
                token = ExamToken.objects.create(
                    student=student,
                    semester_id=semester_id,
                    batch_id=batch_id,
                    section_id=section_id,
                    discipline_id=discipline_id,
                    issue_date=date.today(),
                    valid_until=valid_until,
                    status='generated'
                )
                
                # Add ONLY eligible subjects to token
                token.eligible_subjects.set(eligible_subjects)
                token.save()
                created_count += 1
                
                print(f"✅ Token created for {student.student_id} with {len(eligible_subjects)} eligible subjects")
            
            # Show success/error messages
            if created_count > 0:
                messages.success(request, f'{created_count} tokens created successfully!')
            
            if skipped_count > 0:
                msg = f"{skipped_count} students were not eligible: "
                for student in not_eligible_students[:3]:
                    msg += f"{student['name']} ({', '.join(student['reasons'])}); "
                if len(not_eligible_students) > 3:
                    msg += f"... and {len(not_eligible_students) - 3} more"
                messages.warning(request, msg)
            
            if created_count == 0 and skipped_count > 0:
                messages.error(request, "No tokens were created. All selected students are not eligible.")
            
            return redirect('token_app:all_tokens')
            
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            print(f"Error in bulk_create_tokens POST: {str(e)}")
            import traceback
            traceback.print_exc()
            return redirect('token_app:bulk_create_tokens')
    
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
        'discipline': str(student.discipline) if student.discipline else '',
    }
    return JsonResponse(data)


def get_student_subjects_api(request, student_id):
    """Get eligible subjects for a student via AJAX"""
    try:
        student = get_object_or_404(Student, id=student_id)
        semester_id = request.GET.get('semester_id')
        
        if semester_id:
            eligible_subjects = get_eligible_subjects_for_bulk(student, semester_id)
        else:
            eligible_subjects = Subject.objects.filter(is_active=True)
        
        data = []
        for subject in eligible_subjects:
            data.append({
                'id': subject.id,
                'code': subject.code,
                'name': subject.name,
                'credit_hours': subject.credit_hours,
            })
        
        return JsonResponse(data, safe=False)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


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
    
    status_counts = {}
    for status_code, status_name in ExamToken.TokenStatus.choices:
        status_counts[status_name] = ExamToken.objects.filter(status=status_code).count()
    
    recent_tokens = ExamToken.objects.order_by('-issue_date')[:10]
    
    active_tokens = ExamToken.objects.filter(
        status__in=['generated', 'printed', 'verified']
    ).count()
    
    expiring_soon = ExamToken.objects.filter(
        valid_until__gte=date.today(),
        valid_until__lte=date.today() + timedelta(days=7),
        status__in=['generated', 'printed', 'verified']
    ).count()
    
    expired = ExamToken.objects.filter(
        Q(valid_until__lt=date.today()) | Q(status='expired')
    ).exclude(
        status__in=['used', 'cancelled']
    ).count()
    
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
    total_tokens = ExamToken.objects.count()
    
    batch_stats = ExamToken.objects.values('batch__name').annotate(
        count=Count('id')
    ).order_by('-count')
    
    for stat in batch_stats:
        stat['percentage'] = (stat['count'] / total_tokens * 100) if total_tokens > 0 else 0
    
    semester_stats = ExamToken.objects.values('semester__number').annotate(
        count=Count('id')
    ).order_by('semester__number')
    
    for stat in semester_stats:
        stat['percentage'] = (stat['count'] / total_tokens * 100) if total_tokens > 0 else 0
    
    status_counts = {}
    for status_code, status_name in ExamToken.TokenStatus.choices:
        count = ExamToken.objects.filter(status=status_code).count()
        status_counts[status_name] = count
    
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
    
    students_count = Student.objects.filter(exam_tokens__isnull=False).distinct().count()
    active_tokens = ExamToken.objects.filter(status__in=['generated', 'printed', 'verified']).count()
    avg_tokens_per_student = total_tokens / students_count if students_count > 0 else 0
    
    context = {
        'total_tokens': total_tokens,
        'active_tokens': active_tokens,
        'students_count': students_count,
        'batch_stats': batch_stats,
        'semester_stats': semester_stats,
        'status_counts': status_counts,
        'monthly_data': monthly_data,
        'avg_tokens_per_student': avg_tokens_per_student,
    }
    return render(request, 'token_app/statistics.html', context)


def token_generated_students(request):
    """View all students who have generated tokens"""
    students_with_tokens = Student.objects.filter(
        exam_tokens__isnull=False
    ).distinct().order_by('student_id')
    
    discipline_id = request.GET.get('discipline')
    batch_id = request.GET.get('batch')
    semester_id = request.GET.get('semester')
    section_id = request.GET.get('section')
    status = request.GET.get('status')
    
    if discipline_id:
        students_with_tokens = students_with_tokens.filter(discipline_id=discipline_id)
    if batch_id:
        students_with_tokens = students_with_tokens.filter(batch_id=batch_id)
    if semester_id:
        students_with_tokens = students_with_tokens.filter(semester_id=semester_id)
    if section_id:
        students_with_tokens = students_with_tokens.filter(section_id=section_id)
    
    search = request.GET.get('search', '')
    if search:
        students_with_tokens = students_with_tokens.filter(
            Q(student_id__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    
    student_data = []
    for student in students_with_tokens:
        tokens = ExamToken.objects.filter(student=student)
        
        total_tokens = tokens.count()
        active_tokens = tokens.filter(status__in=['generated', 'printed', 'verified']).count()
        expired_tokens = tokens.filter(status='expired').count()
        used_tokens = tokens.filter(status='used').count()
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
            'token_numbers': [t.token_number for t in tokens[:5]],
        })
    
    paginator = Paginator(student_data, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'students_data': page_obj,
        'disciplines': Discipline.objects.all(),
        'batches': Batch.objects.all(),
        'semesters': Semester.objects.all(),
        'sections': Section.objects.all(),
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
    
    total_tokens = tokens.count()
    active_tokens = tokens.filter(status__in=['generated', 'printed', 'verified']).count()
    expired_tokens = tokens.filter(status='expired').count()
    used_tokens = tokens.filter(status='used').count()
    
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