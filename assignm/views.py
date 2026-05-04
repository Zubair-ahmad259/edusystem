from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q
from django.core.paginator import Paginator
from .models import Assignment, AssignmentSubmission
from subject.models import SubjectAssign
from teachers.models import Teacher
from student.models import Student
from Academic.models import Section
from django.utils import timezone
from django.utils import timezone
from django.core.paginator import Paginator
    
@login_required
def assignment_dashboard(request):
    now = timezone.now()
    
    context = {
        'total_assignments': 0,
        'total_submitted': 0,
        'total_teachers': 0,
        'total_subjects': 0,
        'all_assignments': [],
        'now': now,
    }
    
    # ADMIN Dashboard - Show ALL assignments from ALL teachers
    # Get all assignments (no teacher filter)
    assignments = Assignment.objects.filter(is_active=True).order_by('-created_date')
    
    context['total_assignments'] = assignments.count()
    
    # Total submissions across all assignments
    total_submissions = AssignmentSubmission.objects.filter(
        assignment__in=assignments
    ).count()
    context['total_submitted'] = total_submissions
    
    # Total teachers who created assignments
    total_teachers = Teacher.objects.filter(
        assignments__is_active=True
    ).distinct().count()
    context['total_teachers'] = total_teachers
    
    # Total unique subjects with assignments
    total_subjects = SubjectAssign.objects.filter(
        assignments__is_active=True
    ).distinct().count()
    context['total_subjects'] = total_subjects
    
    # Pagination
    paginator = Paginator(assignments, 10)
    page_number = request.GET.get('page')
    context['all_assignments'] = paginator.get_page(page_number)
    
    return render(request, 'assignment/dashboard.html', context)
@login_required
def teacher_submit_assignment(request):
    """Allow teachers to submit assignments"""
    if request.method == 'POST':
        try:
            assignment_id = request.POST.get('assignment_id')
            section_id = request.POST.get('section_id')
            content = request.POST.get('content', '')
            attachment = request.FILES.get('attachment')
            
            assignment = get_object_or_404(Assignment, id=assignment_id)
            section = get_object_or_404(Section, id=section_id)
            
            # Create submission
            submission = AssignmentSubmission.objects.create(
                assignment=assignment,
                student=request.user,  # Teacher as student
                section=section,
                submission_text=content,
                submission_file=attachment,
                status='submitted'
            )
            
            messages.success(request, f'Successfully submitted "{assignment.title}"')
        except Exception as e:
            messages.error(request, f'Error submitting assignment: {str(e)}')
        
        return redirect('assignment:assignment_dashboard')
    
    return redirect('assignment:assignment_dashboard')
@login_required
def teacher_assignment_list(request):
    """Show only assignments for subjects assigned to the logged-in teacher"""
    try:
        teacher = request.user.teacher
    except:
        messages.error(request, "You are not registered as a teacher")
        return redirect('home')
    
    # Get all subject assignments for this teacher
    subject_assignments = SubjectAssign.objects.filter(teacher=teacher, is_active=True)
    
    # Get assignments for these subjects
    assignments = Assignment.objects.filter(
        subject_assign__in=subject_assignments,
        is_active=True
    ).order_by('-created_date')
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        assignments = assignments.filter(status=status_filter)
    
    paginator = Paginator(assignments, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'assignments': page_obj,
        'status_filter': status_filter,
        'teacher': teacher,
    }
    return render(request, 'assignment/teacher_assignment_list.html', context)

@login_required
def teacher_assignment_create(request):
    """Create assignment - only shows subjects assigned to teacher"""
    try:
        teacher = request.user.teacher
    except:
        messages.error(request, "You are not registered as a teacher")
        return redirect('home')
    
    # Get only subjects assigned to this teacher
    subject_assignments = SubjectAssign.objects.filter(teacher=teacher, is_active=True)
    
    # Create a dictionary of sections for each subject assignment
    sections_by_subject = {}
    sections_json = {}
    for assign in subject_assignments:
        sections_list = list(assign.sections.all())
        sections_by_subject[assign.id] = sections_list
        # Create JSON version for JavaScript
        sections_json[str(assign.id)] = [
            {'id': s.id, 'name': s.name} for s in sections_list
        ]
    
    if request.method == 'POST':
        try:
            subject_assign_id = request.POST.get('subject_assign')
            subject_assign = get_object_or_404(SubjectAssign, id=subject_assign_id, teacher=teacher)
            
            assignment = Assignment.objects.create(
                title=request.POST.get('title'),
                description=request.POST.get('description'),
                subject_assign=subject_assign,
                teacher=teacher,
                assignment_type=request.POST.get('assignment_type'),
                assignment_file=request.FILES.get('assignment_file'),
                due_date=request.POST.get('due_date'),
                total_marks=int(request.POST.get('total_marks', 100)),
            )
            
            # Add selected sections
            section_ids = request.POST.getlist('sections')
            assignment.sections.set(section_ids)
            
            messages.success(request, f'Assignment "{assignment.title}" created successfully!')
            return redirect('assignm:teacher_assignment_list')
        except Exception as e:
            messages.error(request, f'Error creating assignment: {str(e)}')
    
    import json
    context = {
        'subject_assignments': subject_assignments,
        'sections_by_subject': sections_by_subject,
        'sections_json': json.dumps(sections_json),  # Pass as JSON string
        'assignment_types': Assignment.ASSIGNMENT_TYPES,
    }
    return render(request, 'assignment/teacher_assignment_create.html', context)
@login_required
def teacher_assignment_detail(request, assignment_id):
    """View assignment details and student submissions"""
    assignment = get_object_or_404(Assignment, id=assignment_id, is_active=True)
    
    # Check if user is admin or the teacher who owns this assignment
    is_admin = request.user.is_superuser or request.user.is_staff
    
    if not is_admin:
        # If not admin, check if user is the teacher who owns this assignment
        try:
            teacher = request.user.teacher
            if assignment.teacher != teacher:
                messages.error(request, "You don't have permission to view this assignment")
                return redirect('assignment:assignment_dashboard')
        except:
            messages.error(request, "You don't have permission to view this assignment")
            return redirect('assignment:assignment_dashboard')
    
    submissions = assignment.submissions.all().select_related('student')
    
    # Statistics
    total_submissions = submissions.count()
    graded_count = submissions.filter(status='graded').count()
    pending_count = submissions.filter(status__in=['submitted', 'late', 'resubmitted']).count()
    plagiarized_count = submissions.filter(is_plagiarized=True).count()
    
    context = {
        'assignment': assignment,
        'submissions': submissions,
        'total_submissions': total_submissions,
        'graded_count': graded_count,
        'pending_count': pending_count,
        'plagiarized_count': plagiarized_count,
        'is_admin': is_admin,
    }
    return render(request, 'assignment/teacher_assignment_detail.html', context)
@login_required
def teacher_grade_submission(request, submission_id):
    """Grade a student's submission"""
    try:
        teacher = request.user.teacher
    except:
        messages.error(request, "You are not registered as a teacher")
        return redirect('home')
    
    submission = get_object_or_404(AssignmentSubmission, id=submission_id)
    
    # Verify teacher owns this assignment
    if submission.assignment.teacher != teacher:
        messages.error(request, "You don't have permission to grade this submission")
        return redirect('assignment:teacher_assignment_list')
    
    if request.method == 'POST':
        marks = float(request.POST.get('marks_obtained', 0))
        feedback = request.POST.get('teacher_feedback', '')
        
        submission.marks_obtained = marks
        submission.teacher_feedback = feedback
        submission.status = 'graded'
        submission.save()
        
        messages.success(request, f'Submission graded successfully!')
        return redirect('assignment:teacher_assignment_detail', assignment_id=submission.assignment.id)
    
    context = {
        'submission': submission,
    }
    return render(request, 'assignment/teacher_grade_submission.html', context)


# ==================== STUDENT VIEWS ====================

@login_required
def student_assignment_list(request):
    """Show assignments for student's enrolled subjects"""
    try:
        student = request.user.student
    except:
        messages.error(request, "You are registered as a student")
        return redirect('home')
    
    # Get student's enrolled sections - Try different possible relationships
    student_sections = []
    
    # Method 1: Check if student has section field directly
    if hasattr(student, 'section') and student.section:
        student_sections = [student.section]
    # Method 2: Check if student has many-to-many relationship with sections
    elif hasattr(student, 'sections'):
        student_sections = list(student.sections.all())
    # Method 3: Check if student has section_set (reverse relation)
    elif hasattr(student, 'section_set'):
        student_sections = list(student.section_set.all())
    # Method 4: Check if student has enrollments relationship
    elif hasattr(student, 'enrollments'):
        student_sections = [e.section for e in student.enrollments.all() if e.section]
    
    if not student_sections:
        messages.warning(request, "No sections assigned to you. Please contact administrator.")
        # Return empty assignments instead of error
        context = {
            'assignments': [],
            'submitted_ids': [],
            'filter_type': 'all',
            'student': student,
            'now': timezone.now(),
        }
        return render(request, 'assignment/student_assignment_list.html', context)
    
    # Get assignments for these sections
    assignments = Assignment.objects.filter(
        sections__in=student_sections,
        is_active=True
    ).distinct().order_by('due_date')
    
    # Filter by status
    filter_type = request.GET.get('filter', 'all')
    current_time = timezone.now()
    
    if filter_type == 'active':
        assignments = assignments.filter(due_date__gt=current_time)
    elif filter_type == 'past':
        assignments = assignments.filter(due_date__lt=current_time)
    
    # Get student's submissions
    submitted_ids = AssignmentSubmission.objects.filter(
        student=student
    ).values_list('assignment_id', flat=True)
    
    paginator = Paginator(assignments, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'assignments': page_obj,
        'submitted_ids': list(submitted_ids),
        'filter_type': filter_type,
        'student': student,
        'now': current_time,
    }
    return render(request, 'assignment/student_assignment_list.html', context)
@login_required
def student_assignment_detail(request, assignment_id):
    """View assignment details and submit"""
    try:
        student = request.user.student
    except:
        messages.error(request, "You are not registered as a student")
        return redirect('home')
    
    assignment = get_object_or_404(Assignment, id=assignment_id, is_active=True)
    
    # Get student's enrolled sections
    student_sections = []
    
    if hasattr(student, 'section') and student.section:
        student_sections = [student.section]
    elif hasattr(student, 'sections'):
        student_sections = list(student.sections.all())
    elif hasattr(student, 'section_set'):
        student_sections = list(student.section_set.all())
    elif hasattr(student, 'enrollments'):
        student_sections = [e.section for e in student.enrollments.all() if e.section]
    
    # Check if student is enrolled in any section for this assignment
    is_enrolled = False
    if student_sections:
        is_enrolled = assignment.sections.filter(id__in=[s.id for s in student_sections]).exists()
    
    if not is_enrolled:
        messages.error(request, "You are not enrolled in this assignment")
        return redirect('assignm:student_assignment_list')
    
    # Check if student already submitted
    submission = AssignmentSubmission.objects.filter(
        assignment=assignment,
        student=student
    ).first()
    
    is_late = timezone.now() > assignment.due_date
    can_submit = not submission and not is_late
    
    if request.method == 'POST' and can_submit:
        submission_file = request.FILES.get('submission_file')
        
        if submission_file:
            # Check file size (max 10MB)
            if submission_file.size > 10 * 1024 * 1024:
                messages.error(request, "File size too large. Maximum 10MB allowed")
            else:
                submission = AssignmentSubmission.objects.create(
                    assignment=assignment,
                    student=student,
                    submission_file=submission_file,
                )
                messages.success(request, 'Assignment submitted successfully!')
                return redirect('assignment:student_assignment_detail', assignment_id=assignment.id)
    
    context = {
        'assignment': assignment,
        'submission': submission,
        'is_late': is_late,
        'can_submit': can_submit,
        'student': student,
        'now': timezone.now(),
    }
    return render(request, 'assignment/student_assignment_detail.html', context)

@login_required
def student_submission_status(request):
    """View all student submissions with grades"""
    try:
        student = request.user.student
    except:
        messages.error(request, "You are not registered as a student")
        return redirect('home')
    
    submissions = AssignmentSubmission.objects.filter(
        student=student
    ).select_related('assignment').order_by('-submitted_date')
    
    context = {
        'submissions': submissions,
    }
    return render(request, 'assignment/student_submission_status.html', context)

from django.http import JsonResponse
from subject.models import SubjectAssign
import json

def get_sections_by_subject(request):
    """API endpoint to get sections for a subject assignment"""
    if request.method == 'GET':
        subject_assign_id = request.GET.get('subject_assign_id')
        
        print(f"Received subject_assign_id: {subject_assign_id}")  # Debug print
        
        if subject_assign_id:
            try:
                subject_assign = SubjectAssign.objects.get(id=subject_assign_id)
                sections = subject_assign.sections.all()
                
                sections_data = []
                for section in sections:
                    sections_data.append({
                        'id': section.id,
                        'name': section.name,
                    })
                
                print(f"Sections found: {sections_data}")  # Debug print
                
                return JsonResponse({'sections': sections_data})
                
            except SubjectAssign.DoesNotExist:
                print(f"SubjectAssign with id {subject_assign_id} not found")
                return JsonResponse({'sections': [], 'error': 'Subject not found'})
            except Exception as e:
                print(f"Error: {str(e)}")
                return JsonResponse({'sections': [], 'error': str(e)})
    
    return JsonResponse({'sections': [], 'error': 'Invalid request method'})


    