from decimal import Decimal
from django.http import JsonResponse
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from datetime import datetime
from decimal import Decimal

from pyexpat.errors import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.db.models import Avg, Sum, Q, Count
from django.views.decorators.http import require_POST
from datetime import datetime, timedelta
from django.contrib.auth import get_user_model

from .models import (
    SubjectMarkComponents, Exam, ExamResult, 
    SubjectComprehensiveResult, Transcript
)
from student.models import Student
from Academic.models import Batch, Semester, Section, Discipline
from subject.models import Subject
from teachers.models import Teacher


from django.db.models import Q, Sum, Avg, Count
from django.core.paginator import Paginator
# dashjboard


def dashboard(request):
    """Main dashboard page"""
    # Get statistics
    total_exams = Exam.objects.count()
    published_exams = Exam.objects.filter(is_published=True).count()
    
    exams_with_results = Exam.objects.annotate(
        result_count=Count('results')
    ).filter(result_count__gt=0).count()
    
    exams_without_results = total_exams - exams_with_results
    
    # Get upcoming exams (next 7 days)
    upcoming_date = datetime.now() + timedelta(days=7)
    upcoming_exams = Exam.objects.filter(
        exam_date__gte=datetime.now().date(),
        exam_date__lte=upcoming_date.date()
    ).order_by('exam_date')[:5]
    
    # Get recent exams
    exams = Exam.objects.all().select_related(
        'subject_mark_component', 'subject_mark_component__subject'
    ).order_by('-created_at')[:10]
    
    # Get active users
    User = get_user_model()
    active_users = User.objects.filter(is_active=True).count()
    
    # Get recent transcripts
    recent_transcripts = Transcript.objects.filter(
        is_issued=True
    ).select_related('student').order_by('-created_at')[:5]
    
    # Get comprehensive results count
    comprehensive_results_count = SubjectComprehensiveResult.objects.count()
    
    # Get student comprehensive stats if logged in
    student_comprehensive_stats = None
    if request.user.is_authenticated:
        try:
            student = Student.objects.get(user=request.user)
            # Get comprehensive results
            comp_results = SubjectComprehensiveResult.objects.filter(student=student)
            
            if comp_results.exists():
                # Calculate statistics
                total_subjects = comp_results.count()
                passed_subjects = comp_results.exclude(grade='F').count()
                failed_subjects = comp_results.filter(grade='F').count()
                
                # Calculate cumulative GPA
                cumulative_gpa = calculate_cumulative_gpa(student)
                
                student_comprehensive_stats = {
                    'total_subjects': total_subjects,
                    'passed_subjects': passed_subjects,
                    'failed_subjects': failed_subjects,
                    'cumulative_gpa': cumulative_gpa,
                    'student': student,
                }
        except Student.DoesNotExist:
            pass
    
    context = {
        'exams': exams,
        'total_exams': total_exams,
        'published_exams': published_exams,
        'exams_with_results': exams_with_results,
        'exams_without_results': exams_without_results,
        'upcoming_exams': upcoming_exams,
        'active_users': active_users,
        'student_comprehensive_stats': student_comprehensive_stats,
        'recent_transcripts': recent_transcripts,
        'comprehensive_results_count': comprehensive_results_count,
    }
    return render(request, 'exam/dashboard.html', context)

def exam_dashboard(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    
    # Use the get_students() method
    students = exam.get_students()
    results = exam.results.all()  # Using related_name='results'
    
    # Get summary using the model method
    summary = exam.get_exam_summary()
    
    # Grade distribution
    grade_distribution = {}
    for grade_value, grade_label in ExamResult.GRADE_CHOICES:
        grade_distribution[grade_value] = results.filter(grade=grade_value).count()
    
    context = {
        'exam': exam,
        'students': students,
        'results': results,
        'total_students': summary['total_students'],
        'results_entered': summary['results_entered'],
        'absent_count': summary['absent_count'],
        'passed_count': summary['passed_count'],
        'failed_count': summary['failed_count'],
        'avg_marks': summary['avg_marks'],
        'avg_percentage': summary['avg_percentage'],
        'grade_distribution': grade_distribution,
        'is_ready_for_results': exam.is_ready_for_results,
    }
    return render(request, 'exam/exam_dashboard.html', context)

def exam_dashboard(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    students = exam.get_students()
    results = ExamResult.objects.filter(exam=exam)
    
    # Statistics
    total_students = students.count()
    results_entered = results.count()
    absent_count = results.filter(is_absent=True).count()
    passed_count = results.exclude(grade='F').exclude(grade__isnull=True).count()
    failed_count = results.filter(grade='F').count()
    
    # Grade distribution
    grade_distribution = {}
    for grade_value, grade_label in ExamResult.GRADE_CHOICES:
        grade_distribution[grade_value] = results.filter(grade=grade_value).count()
    
    # Average marks
    avg_marks = 0
    avg_percentage = 0
    marks_results = results.filter(marks_obtained__isnull=False).exclude(is_absent=True)
    if marks_results.exists():
        avg_marks_result = marks_results.aggregate(avg=Avg('marks_obtained'))
        avg_percentage_result = marks_results.aggregate(avg=Avg('percentage'))
        avg_marks = avg_marks_result['avg'] or Decimal('0.00')
        avg_percentage = avg_percentage_result['avg'] or Decimal('0.00')
    
    context = {
        'exam': exam,
        'students': students,
        'results': results,
        'total_students': total_students,
        'results_entered': results_entered,
        'absent_count': absent_count,
        'passed_count': passed_count,
        'failed_count': failed_count,
        'grade_distribution': grade_distribution,
        'avg_marks': avg_marks,
        'avg_percentage': avg_percentage,
    }
    return render(request, 'exam/exam_dashboard.html', context)
def create_exam(request):
    """Create a new exam - Teacher specific, only assigned subjects"""
    from teachers.models import Teacher
    from subject.models import SubjectAssign
    
    if request.method == 'GET':
        try:
            today = datetime.now()
            
            try:
                teacher = Teacher.objects.get(user=request.user)
            except Teacher.DoesNotExist:
                messages.error(request, 'Teacher profile not found!')
                return redirect('dashboard')
            
            # Get subjects assigned to this teacher
            assigned_subject_ids = SubjectAssign.objects.filter(
                teacher=teacher,
                is_active=True
            ).values_list('subject_id', flat=True).distinct()
            
            # Get subject mark components only for assigned subjects
            subject_mark_components = SubjectMarkComponents.objects.filter(
                subject_id__in=assigned_subject_ids,
                teacher=teacher
            ).select_related('subject', 'semester', 'batch')
            
            # Calculate valid configurations count
            valid_configs = subject_mark_components.filter(total_percentage=100).count()
            
            exam_types = Exam.EXAM_TYPE_CHOICES
            
            recent_exams = Exam.objects.filter(
                subject_mark_component__teacher=teacher
            ).select_related(
                'subject_mark_component__subject'
            ).order_by('-created_at')[:5]
            
            context = {
                'subject_mark_components': subject_mark_components,
                'exam_types': exam_types,
                'today': today,
                'exams': recent_exams,
                'valid_configs': valid_configs,
            }
            
            return render(request, 'exam/create_exam.html', context)
            
        except Exception as e:
            print(f"Error: {str(e)}")
            context = {
                'error': f'Error loading form: {str(e)}',
                'subject_mark_components': [],
                'exam_types': Exam.EXAM_TYPE_CHOICES,
                'today': datetime.now(),
                'exams': [],
                'valid_configs': 0,
            }
            return render(request, 'exam/create_exam.html', context)
    

def delete_exam(request, exam_id):
    """Delete confirmation page for an exam"""
    try:
        # Get the exam or return 404
        exam = get_object_or_404(Exam, id=exam_id)
        
        if request.method == 'POST':
            # If user confirms deletion
            subject_code = exam.subject_mark_component.subject.code
            exam_type = exam.get_exam_type_display()
            exam.delete()
            
            messages.success(request, f'{exam_type} exam for {subject_code} has been deleted successfully!')
            # Redirect to main dashboard or exam list, NOT specific exam dashboard
            return redirect('dashboard')  # Redirect to main system dashboard
        
        # If GET request, show confirmation page
        return render(request, 'exam/delete_exam_confirmation.html', {
            'exam': exam,
            'title': 'Delete Exam'
        })
        
    except Exception as e:
        messages.error(request, f'Error deleting exam: {str(e)}')
        return redirect('dashboard')  # Redirect to main system dashboard
def get_available_exam_types(request):
    """Get available exam types for a subject configuration"""
    try:
        component_id = request.GET.get('component_id')
        
        if not component_id:
            return JsonResponse({'available_types': [], 'error': 'No component ID provided'})
        
        # Get the component
        component = SubjectMarkComponents.objects.get(id=component_id)
        
        # Get available exam types
        available_types = []
        
        # Check each exam type if it has percentage > 0
        exam_type_mapping = {
            'mid_term': ('Mid Term', component.mid_term_percentage),
            'final': ('Final', component.final_term_percentage),
            'quiz': ('Quiz', component.quiz_percentage),
            'assignment': ('Assignment', component.assignment_percentage),
            'presentation': ('Presentation', component.presentation_percentage),
            'lab': ('Lab', component.lab_percentage),
            'viva': ('Viva', component.viva_percentage),
            'attendance': ('Attendance', component.attendance_percentage),
        }
        
        for type_code, (display_name, percentage) in exam_type_mapping.items():
            if percentage > Decimal('0.00'):
                available_types.append([type_code, display_name])
        
        # Component details
        component_details = {
            'subject': f"{component.subject.code} - {component.subject.name}",
            'semester': str(component.semester),
            'batch': str(component.batch),
            'credit_hours': float(component.subject.credit_hours),
        }
        
        return JsonResponse({
            'success': True,
            'available_types': available_types,
            'component_details': component_details,
        })
        
    except SubjectMarkComponents.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Subject configuration not found'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
def exam_list(request):
    """List all exams"""
    exams = Exam.objects.all().select_related(
        'subject_mark_component', 'subject_mark_component__subject'
    ).order_by('-created_at')
    
    return render(request, 'exam/exam_list.html', {'exams': exams})

def publish_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    exam.is_published = True
    exam.published_at = timezone.now()
    exam.save()
    
    # Update comprehensive results for all students
    students = exam.get_students()
    for student in students:
        update_comprehensive_result(student, exam.subject_mark_component)
    
    return redirect('exam_dashboard', exam_id=exam.id)

# resultdd
def comprehensive_result_view(request):
    """View comprehensive results with filtering options - Simplified View"""
    
    # Initialize filters
    batch_id = request.GET.get('batch')
    semester_id = request.GET.get('semester')
    student_id = request.GET.get('student')
    subject_id = request.GET.get('subject')
    search_query = request.GET.get('search', '')
    
    # Get all filter options
    batches = Batch.objects.all().order_by('-start_session')
    semesters = Semester.objects.all().order_by('number')
    students = Student.objects.all().select_related('user', 'batch')
    subjects = Subject.objects.all().order_by('code')
    
    # Start with all comprehensive results
    comp_results = SubjectComprehensiveResult.objects.all().select_related(
        'student__user',
        'student__batch',
        'subject_mark_component__subject',
        'subject_mark_component__semester'
    )
    
    # Apply filters
    if batch_id:
        comp_results = comp_results.filter(student__batch_id=batch_id)
    
    if semester_id:
        comp_results = comp_results.filter(subject_mark_component__semester_id=semester_id)
    
    if student_id:
        comp_results = comp_results.filter(student_id=student_id)
    
    if subject_id:
        comp_results = comp_results.filter(subject_mark_component__subject_id=subject_id)
    
    if search_query:
        comp_results = comp_results.filter(
            Q(student__user__first_name__icontains=search_query) |
            Q(student__user__last_name__icontains=search_query) |
            Q(student__student_id__icontains=search_query) |
            Q(subject_mark_component__subject__name__icontains=search_query) |
            Q(subject_mark_component__subject__code__icontains=search_query)
        )
    
    # Check if there are any results
    if not comp_results.exists():
        context = {
            'page_obj': None,
            'batches': batches,
            'semesters': semesters,
            'students': students,
            'subjects': subjects,
            'selected_batch': batch_id,
            'selected_semester': semester_id,
            'selected_student': student_id,
            'selected_subject': subject_id,
            'search_query': search_query,
            'total_students': 0,
            'total_subjects': 0,
        }
        return render(request, 'exam/comprehensive_result.html', context)
    
    # Organize data by student and semester
    student_semester_data = {}
    
    for result in comp_results.order_by(
        'student__student_id', 
        'subject_mark_component__semester__number',
        'subject_mark_component__subject__code'
    ):
        student = result.student
        semester = result.subject_mark_component.semester
        key = f"{student.id}_{semester.id}"
        
        if key not in student_semester_data:
            student_semester_data[key] = {
                'student': student,
                'semester': semester,
                'subjects': [],
                'total_obtained_marks': 0,
                'total_max_marks': 0,
                'total_credits': 0,
                'total_quality_points': 0,
                'total_subjects': 0,
                'passed_subjects': 0,
                'failed_subjects': 0,
                'cgpa': 0,
            }
        
        # Calculate if subject is passed
        is_passed = result.grade and result.grade != 'F'
        
        subject_data = {
            'id': result.id,
            'subject_code': result.subject_mark_component.subject.code,
            'subject_name': result.subject_mark_component.subject.name,
            'credit_hours': float(result.subject.credit_hours),
            'obtained_marks': float(result.total_marks),
            'max_marks': 100,  # Assuming max 100 marks
            'percentage': float(result.percentage),
            'grade': result.grade,
            'grade_point': float(result.grade_point),
            'quality_points': float(result.quality_points),
            'is_passed': is_passed,
            'detail_url': f"/exam_mang/subject-result/{result.id}/",  # Customize this URL as needed
        }
        
        student_semester_data[key]['subjects'].append(subject_data)
        student_semester_data[key]['total_obtained_marks'] += subject_data['obtained_marks']
        student_semester_data[key]['total_max_marks'] += subject_data['max_marks']
        student_semester_data[key]['total_credits'] += subject_data['credit_hours']
        student_semester_data[key]['total_quality_points'] += subject_data['quality_points']
        student_semester_data[key]['total_subjects'] += 1
        
        if is_passed:
            student_semester_data[key]['passed_subjects'] += 1
        else:
            student_semester_data[key]['failed_subjects'] += 1
    
    # Calculate GPA and CGPA for each student semester
    for key, data in student_semester_data.items():
        if data['total_credits'] > 0:
            data['gpa'] = data['total_quality_points'] / data['total_credits']
        else:
            data['gpa'] = 0
        
        # Calculate overall percentage
        if data['total_max_marks'] > 0:
            data['overall_percentage'] = (data['total_obtained_marks'] / data['total_max_marks']) * 100
        else:
            data['overall_percentage'] = 0
        
        # Calculate CGPA (you might need to modify this based on your CGPA calculation)
        # For now, using GPA as CGPA for the semester
        data['cgpa'] = data['gpa']
    
    # Prepare data for template
    table_data = []
    for key, data in student_semester_data.items():
        table_data.append(data)
    
    # Pagination
    paginator = Paginator(table_data, 25)  # 25 students per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'batches': batches,
        'semesters': semesters,
        'students': students,
        'subjects': subjects,
        'selected_batch': batch_id,
        'selected_semester': semester_id,
        'selected_student': student_id,
        'selected_subject': subject_id,
        'search_query': search_query,
        'total_students': len(table_data),
        'total_subjects': comp_results.count(),
    }
    
    return render(request, 'exam/comprehensive_result.html', context)

def upload_results(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    default_teacher = Teacher.objects.filter(teacher_id='DEFAULT_TEACHER').first()
    
    if request.method == 'POST':
        for key, value in request.POST.items():
            if key.startswith('marks_'):
                student_id = key.replace('marks_', '')
                
                try:
                    student = Student.objects.get(id=student_id)
                    marks_obtained = value if value else None
                    is_absent = request.POST.get(f'absent_{student_id}') == 'on'
                    remarks = request.POST.get(f'remarks_{student_id}', '')
                    
                    # Create or update result
                    result, created = ExamResult.objects.update_or_create(
                        exam=exam,
                        student=student,
                        defaults={
                            'marks_obtained': Decimal(marks_obtained) if marks_obtained else None,
                            'is_absent': is_absent,
                            'remarks': remarks,
                            'entered_by': default_teacher
                        }
                    )
                    
                    # Update comprehensive result for this subject
                    update_comprehensive_result(student, exam.subject_mark_component)
                    
                except (Student.DoesNotExist, ValueError):
                    continue
        
        return redirect('exam_dashboard', exam_id=exam.id)
    
    # GET request
    students = exam.get_students()
    results = {}
    for student in students:
        try:
            result = ExamResult.objects.get(exam=exam, student=student)
            results[student.id] = result
        except ExamResult.DoesNotExist:
            results[student.id] = None
    
    context = {
        'exam': exam,
        'students': students,
        'results': results,
    }
    return render(request, 'exam/upload_results.html', context)


def update_comprehensive_result(student, subject_mark_component):
    """Update comprehensive result for a student in a subject"""
    try:
        # Get all exam results for this student in this subject
        exams = Exam.objects.filter(
            subject_mark_component=subject_mark_component,
            is_published=True
        )
        
        # Get or create comprehensive result
        comp_result, created = SubjectComprehensiveResult.objects.get_or_create(
            student=student,
            subject_mark_component=subject_mark_component
        )
        
        # Reset all marks
        comp_result.mid_term_marks = Decimal('0.00')
        comp_result.final_marks = Decimal('0.00')
        comp_result.quiz_marks = Decimal('0.00')
        comp_result.assignment_marks = Decimal('0.00')
        comp_result.presentation_marks = Decimal('0.00')
        comp_result.lab_marks = Decimal('0.00')
        comp_result.viva_marks = Decimal('0.00')
        comp_result.attendance_marks = Decimal('0.00')
        
        # Update marks from each exam
        for exam in exams:
            try:
                result = ExamResult.objects.get(exam=exam, student=student)
                if result.weighted_marks:
                    if exam.exam_type == 'mid_term':
                        comp_result.mid_term_marks = result.weighted_marks
                    elif exam.exam_type == 'final':
                        comp_result.final_marks = result.weighted_marks
                    elif exam.exam_type == 'quiz':
                        comp_result.quiz_marks = result.weighted_marks
                    elif exam.exam_type == 'assignment':
                        comp_result.assignment_marks = result.weighted_marks
                    elif exam.exam_type == 'presentation':
                        comp_result.presentation_marks = result.weighted_marks
                    elif exam.exam_type == 'lab':
                        comp_result.lab_marks = result.weighted_marks
                    elif exam.exam_type == 'viva':
                        comp_result.viva_marks = result.weighted_marks
                    elif exam.exam_type == 'attendance':
                        comp_result.attendance_marks = result.weighted_marks
            except ExamResult.DoesNotExist:
                continue
        
        # Save will trigger calculation of total marks, grade, etc.
        comp_result.save()
        
    except Exception as e:
        print(f"Error updating comprehensive result: {e}")


def subject_result_detail(request, result_id):
    """Detailed view for a specific subject result"""
    result = get_object_or_404(SubjectComprehensiveResult, id=result_id)
    
    context = {
        'result': result,
        'student': result.student,
        'subject': result.subject,
        'semester': result.semester,
        'batch': result.batch,
    }
    
    return render(request, 'exam/subject_result_detail.html', context)

def calculate_semester_gpa_for_results(results):
    """Calculate GPA for a list of subject results"""
    total_grade_points = 0
    total_credits = 0
    
    for result in results:
        # Assuming each subject has 3 credits (adjust as needed)
        subject_credits = 3
        total_grade_points += result['grade_point'] * subject_credits
        total_credits += subject_credits
    
    return total_grade_points / total_credits if total_credits > 0 else 0

def student_detailed_result(request, student_id, semester_id=None):
    """Detailed result view for a specific student"""
    student = get_object_or_404(Student, id=student_id)
    
    # Get all semesters for this student
    semesters = Semester.objects.filter(
        subjectmarkcomponent__subjectcomprehensiveresult__student=student
    ).distinct().order_by('number')
    
    # Get selected semester or first available
    if semester_id:
        current_semester = get_object_or_404(Semester, id=semester_id)
    elif semesters.exists():
        current_semester = semesters.first()
    else:
        current_semester = None
    
    # Get comprehensive results for selected semester
    comp_results = []
    semester_gpa = 0
    if current_semester:
        comp_results = SubjectComprehensiveResult.objects.filter(
            student=student,
            subject_mark_component__semester=current_semester
        ).select_related(
            'subject_mark_component__subject',
            'subject_mark_component__semester'
        ).prefetch_related(
            'subject_mark_component__exams',
            'subject_mark_component__exams__examresult_set'
        ).order_by('subject_mark_component__subject__code')
        
        # Calculate semester GPA
        semester_gpa = calculate_semester_gpa(comp_results) if comp_results.exists() else Decimal('0.00')
    
    # Calculate cumulative GPA
    cumulative_gpa = calculate_cumulative_gpa(student)
    
    context = {
        'student': student,
        'current_semester': current_semester,
        'semesters': semesters,
        'comp_results': comp_results,
        'semester_gpa': semester_gpa,
        'cumulative_gpa': cumulative_gpa,
        'student_stats': {
            'total_subjects': comp_results.count(),
            'passed_subjects': comp_results.filter(status='passed').count(),
            'failed_subjects': comp_results.filter(status='failed').count(),
        }
    }
    
    return render(request, 'exam/student_detailed_result.html', context)

def calculate_cumulative_gpa(student):
    """Calculate cumulative GPA for a student"""
    all_results = SubjectComprehensiveResult.objects.filter(student=student)
    
    total_quality_points = Decimal('0.00')
    total_credits = Decimal('0.00')
    
    for result in all_results:
        if result.grade != 'F':  # Only include passed subjects
            total_quality_points += result.quality_points
            total_credits += result.credit_hours  # Using the property
    
    if total_credits > Decimal('0.00'):
        return total_quality_points / total_credits
    else:
        return Decimal('0.00')




from datetime import datetime

from decimal import Decimal
def subject_mark_components(request):
    """Configure mark distribution for subjects - Teacher specific with sections"""
    from teachers.models import Teacher
    from subject.models import SubjectAssign, Subject
    from .models import Exam, ExamResult
    from django.contrib import messages
    from decimal import Decimal
    
    # Get logged-in teacher
    try:
        teacher = Teacher.objects.get(user=request.user)
    except Teacher.DoesNotExist:
        messages.error(request, 'Teacher profile not found!')
        return redirect('dashboard')
    
    # Exam types list for template
    exam_type_list = [
        ('mid_term', 'Mid Term'),
        ('final', 'Final'),
        ('quiz', 'Quiz'),
        ('assignment', 'Assignment'),
        ('presentation', 'Presentation'),
        ('lab', 'Lab'),
        ('viva', 'Viva'),
        ('attendance', 'Attendance'),
    ]
    
    # Get subjects assigned to this teacher with their sections
    subject_assignments = SubjectAssign.objects.filter(
        teacher=teacher,
        is_active=True
    ).select_related('subject', 'batch', 'semester', 'discipline').prefetch_related('sections')
    
    # Organize data by subject with sections
    subjects_with_sections = {}
    for assignment in subject_assignments:
        subject = assignment.subject
        if subject.id not in subjects_with_sections:
            subjects_with_sections[subject.id] = {
                'subject': subject,
                'assignments': []
            }
        
        # Get sections for this assignment
        sections_list = list(assignment.sections.all())
        
        # Try to get existing mark component (use filter().first() instead of get_or_create)
        mark_component = SubjectMarkComponents.objects.filter(
            subject=subject,
            teacher=teacher,
            semester=assignment.semester,
            batch=assignment.batch,
            discipline=assignment.discipline
        ).first()
        
        # If no component exists, create one with defaults
        if not mark_component:
            mark_component = SubjectMarkComponents.objects.create(
                subject=subject,
                teacher=teacher,
                semester=assignment.semester,
                batch=assignment.batch,
                discipline=assignment.discipline,
                mid_term_percentage=Decimal('20.00'),
                final_term_percentage=Decimal('65.00'),
                quiz_percentage=Decimal('5.00'),
                assignment_percentage=Decimal('5.00'),
                presentation_percentage=Decimal('0.00'),
                lab_percentage=Decimal('0.00'),
                viva_percentage=Decimal('0.00'),
                attendance_percentage=Decimal('5.00'),
                section=sections_list[0] if sections_list else None,
                academic_year=get_current_academic_year(),
            )
        
        # Check which components have marks uploaded
        locked_components = []
        has_any_marks = False
        
        for exam_type, _ in exam_type_list:
            exam = Exam.objects.filter(
                subject_mark_component=mark_component,
                exam_type=exam_type
            ).first()
            
            if exam:
                has_results = ExamResult.objects.filter(exam=exam).exists()
                if has_results:
                    locked_components.append(exam_type)
                    has_any_marks = True
        
        subjects_with_sections[subject.id]['assignments'].append({
            'assignment_id': assignment.id,
            'batch': assignment.batch,
            'semester': assignment.semester,
            'discipline': assignment.discipline,
            'sections': sections_list,
            'section_names': ', '.join([s.name for s in sections_list]),
            'student_count': Student.objects.filter(section__in=sections_list).count(),
            'locked_components': locked_components,
            'has_any_marks': has_any_marks,
            'all_components_locked': len(locked_components) >= 8,
            'config': mark_component,  # Pass the config object
            'config_exists': True,
        })
    
    if request.method == 'POST':
        try:
            subject_id = request.POST.get('subject')
            assignment_id = request.POST.get('assignment_id')
            
            if not subject_id:
                messages.error(request, 'Please select a subject!')
                return redirect('subject_mark_components')
            
            subject = Subject.objects.get(id=subject_id)
            assignment = SubjectAssign.objects.get(id=assignment_id, teacher=teacher)
            
            # Get existing mark component
            mark_component = SubjectMarkComponents.objects.filter(
                subject=subject,
                teacher=teacher,
                semester=assignment.semester,
                batch=assignment.batch,
                discipline=assignment.discipline
            ).first()
            
            if not mark_component:
                # Create new component if it doesn't exist
                first_section = assignment.sections.first()
                mark_component = SubjectMarkComponents.objects.create(
                    subject=subject,
                    teacher=teacher,
                    semester=assignment.semester,
                    batch=assignment.batch,
                    discipline=assignment.discipline,
                    section=first_section,
                    academic_year=get_current_academic_year(),
                )
            
            # Parse percentage values
            updates = {}
            for exam_type, _ in exam_type_list:
                value = Decimal(request.POST.get(exam_type, '0.00'))
                
                # Check if this exam type is locked (has existing results)
                exam = Exam.objects.filter(
                    subject_mark_component=mark_component,
                    exam_type=exam_type
                ).first()
                if exam and ExamResult.objects.filter(exam=exam).exists():
                    # Skip updating locked components
                    continue
                
                updates[f'{exam_type}_percentage'] = value
            
            # Calculate total
            total = sum(updates.values())
            
            if abs(total - Decimal('100.00')) > Decimal('0.01'):
                messages.warning(request, f'Total percentage is {total}%, not 100%.')
            
            # Update the component
            for key, value in updates.items():
                setattr(mark_component, key, value)
            mark_component.save()
            
            section_names = ', '.join([s.name for s in assignment.sections.all()])
            messages.success(request, f'Mark distribution for {subject.code} ({assignment.batch.name} - Sections: {section_names}) saved successfully!')
            
        except Exception as e:
            messages.error(request, f'Error saving configuration: {str(e)}')
        
        return redirect('subject_mark_components')
    
    context = {
        'subjects_with_sections': subjects_with_sections,
        'teacher': teacher,
        'total_subjects': len(subjects_with_sections),
        'total_assignments': sum(len(s['assignments']) for s in subjects_with_sections.values()),
        'exam_type_list': exam_type_list,
    }
    
    return render(request, 'exam/subject_mark_components.html', context)
def get_default_teacher():
    """Get or create a default teacher"""
    from teachers.models import Teacher
    default_teacher, created = Teacher.objects.get_or_create(
        teacher_id='DEFAULT_TEACHER',
        defaults={
            'first_name': 'Default',
            'last_name': 'Teacher',
            'father_name': 'N/A',
            'mobile_number': '0000000000',
            'email': 'default@system.com'
        }
    )
    return default_teacher.id


def get_default_semester():
    """Get the first semester or create default"""
    from Academic.models import Semester
    semester = Semester.objects.first()
    if not semester:
        semester = Semester.objects.create(number=1)
    return semester.id


def get_default_batch():
    """Get the first batch or create default"""
    from Academic.models import Batch
    from Academic.models import Discipline
    batch = Batch.objects.first()
    if not batch:
        # Create a default discipline first
        discipline, _ = Discipline.objects.get_or_create(
            program='BS',
            field='Computer Science'
        )
        batch = Batch.objects.create(
            name='Default Batch',
            start_session='2020',
            end_session='2024',
            discipline=discipline
        )
    return batch.id


def get_default_discipline():
    """Get the first discipline or create default"""
    from Academic.models import Discipline
    discipline = Discipline.objects.first()
    if not discipline:
        discipline = Discipline.objects.create(
            program='BS',
            field='Computer Science'
        )
    return discipline.id


def get_current_academic_year():
    """Get current academic year"""
    current_year = datetime.now().year
    return f"{current_year}-{current_year + 1}"

def load_mark_component(request, id):
    """Load configuration data for editing - Teacher specific"""
    try:
        teacher = Teacher.objects.get(user=request.user)
        component = SubjectMarkComponents.objects.get(id=id)
        
        # Verify teacher owns this configuration
        if component.teacher_id != teacher.id:
            return JsonResponse({'success': False, 'error': 'Unauthorized - You do not own this configuration'})
        
        data = {
            'success': True,
            'subject_id': component.subject_id,
            'mid_term_percentage': str(component.mid_term_percentage),
            'final_term_percentage': str(component.final_term_percentage),
            'quiz_percentage': str(component.quiz_percentage),
            'assignment_percentage': str(component.assignment_percentage),
            'presentation_percentage': str(component.presentation_percentage),
            'lab_percentage': str(component.lab_percentage),
            'viva_percentage': str(component.viva_percentage),
            'attendance_percentage': str(component.attendance_percentage),
        }
        return JsonResponse(data)
    except Teacher.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Teacher not found'})
    except SubjectMarkComponents.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Configuration not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

def delete_mark_component(request, id):
    """Delete mark distribution configuration - Teacher specific"""
    from teachers.models import Teacher
    from subject.models import SubjectAssign
    from django.contrib import messages
    from django.shortcuts import get_object_or_404, redirect
    from .models import SubjectMarkComponents
    
    try:
        teacher = Teacher.objects.get(user=request.user)
    except Teacher.DoesNotExist:
        messages.error(request, 'Teacher profile not found!')
        return redirect('subject_mark_components')
    except Exception as e:
        messages.error(request, f'Error finding teacher: {str(e)}')
        return redirect('subject_mark_components')
    
    # Get the component
    try:
        component = get_object_or_404(SubjectMarkComponents, id=id)
    except Exception as e:
        messages.error(request, f'Configuration not found: {str(e)}')
        return redirect('subject_mark_components')
    
    # Verify teacher owns this configuration
    if component.teacher_id != teacher.id:
        messages.error(request, 'You are not authorized to delete this configuration!')
        return redirect('subject_mark_components')
    
    if request.method == 'POST':
        try:
            subject_code = component.subject.code
            component.delete()
            messages.success(request, f'Mark distribution for {subject_code} deleted successfully!')
        except Exception as e:
            messages.error(request, f'Error deleting configuration: {str(e)}')
        return redirect('subject_mark_components')
    
    # GET request - show confirmation page
    context = {
        'component': component,
        'title': 'Delete Mark Distribution'
    }
    return render(request, 'exam/delete_confirmation.html', context)
def subject_result_detail(request, student_id, subject_mark_component_id):
    """Detailed view of a student's result in a subject"""
    student = get_object_or_404(Student, id=student_id)
    subject_mark_component = get_object_or_404(SubjectMarkComponents, id=subject_mark_component_id)
    
    # Get all exam results for this subject
    exams = Exam.objects.filter(
        subject_mark_component=subject_mark_component,
        is_published=True
    )
    
    exam_results = []
    for exam in exams:
        try:
            result = ExamResult.objects.get(exam=exam, student=student)
            exam_results.append({
                'exam': exam,
                'result': result
            })
        except ExamResult.DoesNotExist:
            exam_results.append({
                'exam': exam,
                'result': None
            })
    
    # Get comprehensive result
    try:
        comp_result = SubjectComprehensiveResult.objects.get(
            student=student,
            subject_mark_component=subject_mark_component
        )
    except SubjectComprehensiveResult.DoesNotExist:
        comp_result = None
    
    context = {
        'student': student,
        'subject_mark_component': subject_mark_component,
        'exam_results': exam_results,
        'comp_result': comp_result,
    }
    
    return render(request, 'exam/subject_result_detail.html', context)


def select_student_for_results(request):
    """View to select a student for viewing results"""
    students = Student.objects.all().select_related('batch', 'semester', 'discipline')
    
    if request.GET.get('search'):
        search_term = request.GET.get('search')
        students = students.filter(
            Q(student_id__icontains=search_term) |
            Q(first_name__icontains=search_term) |
            Q(last_name__icontains=search_term)
        )
    
    return render(request, 'exam/select_student.html', {'students': students})

def exam_dashboard(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    
    # Use the get_students() method
    students = exam.get_students()
    results = exam.results.all()
    
    # Statistics
    total_students = students.count()
    results_entered = results.count()
    absent_count = results.filter(is_absent=True).count()
    passed_count = results.exclude(grade='F').exclude(grade__isnull=True).count()
    failed_count = results.filter(grade='F').count()
    
    # Grade distribution
    grade_distribution = {}
    for grade_value, grade_label in ExamResult.GRADE_CHOICES:
        grade_distribution[grade_value] = results.filter(grade=grade_value).count()
    
    # Average marks
    avg_marks = Decimal('0.00')
    avg_percentage = Decimal('0.00')
    marks_results = results.filter(marks_obtained__isnull=False).exclude(is_absent=True)
    if marks_results.exists():
        avg_marks_result = marks_results.aggregate(avg=Avg('marks_obtained'))
        avg_percentage_result = marks_results.aggregate(avg=Avg('percentage'))
        avg_marks = avg_marks_result['avg'] or Decimal('0.00')
        avg_percentage = avg_percentage_result['avg'] or Decimal('0.00')
    
    context = {
        'exam': exam,
        'students': students,
        'results': results,
        'total_students': total_students,
        'results_entered': results_entered,
        'absent_count': absent_count,
        'passed_count': passed_count,
        'failed_count': failed_count,
        'grade_distribution': grade_distribution,
        'avg_marks': avg_marks,
        'avg_percentage': avg_percentage,
    }
    return render(request, 'exam/exam_dashboard.html', context)

def debug_exam(request, exam_id):
    from .models import Exam
    from student.models import Student
    
    exam = Exam.objects.get(id=exam_id)
    component = exam.subject_mark_component
    
    response_lines = []
    response_lines.append(f"<h1>Debug Exam {exam_id}</h1>")
    response_lines.append(f"<p>Exam: {exam}</p>")
    response_lines.append(f"<p>Subject: {component.subject}</p>")
    response_lines.append(f"<p>Batch: {component.batch}</p>")
    response_lines.append(f"<p>Semester: {component.semester}</p>")
    response_lines.append(f"<p>Discipline: {component.discipline}</p>")
    response_lines.append(f"<p>Section: {component.section}</p>")
    
    # Try direct query
    students = Student.objects.filter(
        batch=component.batch,
        semester=component.semester,
        discipline=component.discipline,
    )
    if component.section:
        students = students.filter(section=component.section)
    
    response_lines.append(f"<p>Students found: {students.count()}</p>")
    
    # List students
    for student in students:
        response_lines.append(f"<p>- {student} (ID: {student.student_id})</p>")
    
    return HttpResponse("\n".join(response_lines))

# transcript

def student_transcript_list(request):
    """Student transcript list"""
    # Get student_id from query parameter if provided
    student_id = request.GET.get('student_id')
    
    if student_id:
        try:
            student = Student.objects.get(id=student_id)
            transcripts = Transcript.objects.filter(
                student=student,
                is_issued=True
            ).order_by('-issue_date')
            
            return render(request, 'exam/student_transcripts.html', {
                'student': student,
                'transcripts': transcripts
            })
        except Student.DoesNotExist:
            pass
    
    # If no student_id or student not found, show all students
    students = Student.objects.all()
    return render(request, 'exam/select_student.html', {
        'students': students
    })

def all_transcripts_list(request):
    """List all transcripts in the system"""
    transcripts = Transcript.objects.filter(
        is_issued=True
    ).order_by('-issue_date')
    
    return render(request, 'exam/all_transcripts.html', {
        'transcripts': transcripts
    })

def generate_transcript(request, student_id):
    """Generate transcript for a student"""
    student = get_object_or_404(Student, id=student_id)
    
    # Get all comprehensive results
    comp_results = SubjectComprehensiveResult.objects.filter(student=student)
    
    if not comp_results.exists():
        return render(request, 'exam/transcript_empty.html', {'student': student})
    
    # Calculate cumulative GPA
    cumulative_gpa = calculate_cumulative_gpa(student)
    
    # Calculate totals - convert everything to Decimal
    total_credits_earned = Decimal('0.00')
    total_quality_points = Decimal('0.00')
    total_credits_attempted = Decimal('0.00')
    
    for result in comp_results:
        # Convert credit_hours to Decimal
        credits = Decimal(str(result.credit_hours))
        total_credits_attempted += credits
        
        if result.grade != 'F':
            total_credits_earned += credits
            
            # Convert quality_points to Decimal if needed
            if isinstance(result.quality_points, Decimal):
                total_quality_points += result.quality_points
            else:
                total_quality_points += Decimal(str(result.quality_points))
    
    # Create transcript
    transcript = Transcript.objects.create(
        student=student,
        transcript_number=f"TR-{student.student_id}-{timezone.now().strftime('%Y%m%d%H%M%S')}",
        transcript_type='official',
        issue_date=timezone.now().date(),
        cumulative_gpa=round(cumulative_gpa, 2),
        total_credits_earned=int(total_credits_earned),
        total_quality_points=total_quality_points,
        total_credits_attempted=int(total_credits_attempted),
        is_issued=True,
        university_name="University",
        department_name=str(student.discipline) if student.discipline else "",
        program_name="Academic Program"
    )
    
    return redirect('view_transcript', transcript_id=transcript.id)

def view_transcript(request, transcript_id):
    """View a transcript"""
    transcript = get_object_or_404(Transcript, id=transcript_id)
    
    # Get comprehensive results with related data
    comp_results = SubjectComprehensiveResult.objects.filter(
        student=transcript.student
    ).select_related(
        'subject_mark_component__subject', 
        'subject_mark_component__semester'
    ).order_by(
        'subject_mark_component__semester__number',  # Changed from name to number
        'subject_mark_component__subject__code'
    )
    
    # Group by semester
    results_by_semester = {}
    for result in comp_results:
        semester_name = f"Semester {result.subject_mark_component.semester.number}"  # Use number
        if semester_name not in results_by_semester:
            results_by_semester[semester_name] = []
        results_by_semester[semester_name].append(result)
    
    context = {
        'transcript': transcript,
        'results_by_semester': results_by_semester,
        'student': transcript.student,
    }
    
    return render(request, 'exam/view_transcript.html', context)

def print_transcript(request, transcript_id):
    """Print-friendly version of transcript"""
    transcript = get_object_or_404(Transcript, id=transcript_id)
    
    comp_results = SubjectComprehensiveResult.objects.filter(
        student=transcript.student
    ).select_related(
        'subject_mark_component__subject', 
        'subject_mark_component__semester'
    ).order_by(
        'subject_mark_component__semester__number',  # Changed from name to number
        'subject_mark_component__subject__code'
    )
    
    # Group by semester
    results_by_semester = {}
    for result in comp_results:
        semester_name = f"Semester {result.subject_mark_component.semester.number}"  # Use number
        if semester_name not in results_by_semester:
            results_by_semester[semester_name] = []
        results_by_semester[semester_name].append(result)
    
    context = {
        'transcript': transcript,
        'results_by_semester': results_by_semester,
        'student': transcript.student,
    }
    
    return render(request, 'exam/print_transcript.html', context)

def delete_transcript(request, transcript_id):
    if not request.user.is_staff:
        return HttpResponse("Unauthorized", status=401)
    
    transcript = get_object_or_404(Transcript, id=transcript_id)
    transcript.delete()
    
    return redirect('dashboard')

# In your views.py
from django.shortcuts import render, get_object_or_404

def transcript_detail(request, pk):
    transcript = get_object_or_404(Transcript, pk=pk)
    
    # Get results by semester
    results_by_semester = {}
    semester_calculations = {}
    
    for result in transcript.results.all():
        semester_name = result.semester.name
        if semester_name not in results_by_semester:
            results_by_semester[semester_name] = []
        
        results_by_semester[semester_name].append(result)
    
    # Calculate semester totals for each semester
    for semester_name, results in results_by_semester.items():
        total_subjects = len(results)
        total_marks = total_subjects * 100
        
        # Calculate total obtained marks
        total_obtained = 0
        for r in results:
            if r.obtained_marks:
                try:
                    total_obtained += float(r.obtained_marks)
                except (ValueError, TypeError):
                    pass
        
        # Calculate semester GPA
        total_grade_points = 0
        total_credits = 0
        for r in results:
            if r.grade_point and r.credit_hours:
                try:
                    grade_point = float(r.grade_point)
                    credit_hours = float(r.credit_hours)
                    total_grade_points += grade_point * credit_hours
                    total_credits += credit_hours
                except (ValueError, TypeError):
                    pass
        
        semester_gpa = total_grade_points / total_credits if total_credits > 0 else 0
        
        # Determine semester grade based on GPA
        if semester_gpa >= 3.67:
            semester_grade = "A"
        elif semester_gpa >= 3.33:
            semester_grade = "B+"
        elif semester_gpa >= 3.00:
            semester_grade = "B"
        elif semester_gpa >= 2.67:
            semester_grade = "C+"
        elif semester_gpa >= 2.33:
            semester_grade = "C"
        elif semester_gpa >= 2.00:
            semester_grade = "D"
        else:
            semester_grade = "F"
        
        semester_calculations[semester_name] = {
            'total_subjects': total_subjects,
            'total_marks': total_marks,
            'total_obtained': total_obtained,
            'semester_gpa': semester_gpa,
            'semester_grade': semester_grade,
            'total_credits': total_credits,
        }
    
    context = {
        'transcript': transcript,
        'results_by_semester': results_by_semester,
        'semester_calculations': semester_calculations,
    }
    
    return render(request, 'transcript_detail.html', context)










    # ==================== DIRECT MARKS UPLOAD SYSTEM ====================
def student_subject_marks(request):
    """Show all students with their total marks in each subject, grouped by section"""
    from teachers.models import Teacher
    from student.models import Student
    from subject.models import Subject
    from Academic.models import Section
    from django.core.paginator import Paginator
    from django.db.models import Q
    from collections import defaultdict
    
    try:
        teacher = Teacher.objects.get(user=request.user)
        
        # Get filter parameters
        selected_subject_id = request.GET.get('subject_id')
        selected_section_id = request.GET.get('section_id')
        search_query = request.GET.get('search', '')
        
        # Get all subjects assigned to this teacher
        assigned_subjects = Subject.objects.filter(
            assigned_teachers__teacher=teacher,
            assigned_teachers__is_active=True
        ).distinct()
        
        # Get all sections
        sections = Section.objects.all()
        
        # If subject_id is provided, filter to that subject only
        if selected_subject_id:
            assigned_subjects = assigned_subjects.filter(id=selected_subject_id)
        
        # Get students based on filters
        students = Student.objects.all()
        
        if selected_section_id:
            students = students.filter(section_id=selected_section_id)
        
        if search_query:
            students = students.filter(
                Q(student_id__icontains=search_query) |
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query)
            )
        
        # Prepare student data with marks, grouped by section
        students_by_section = defaultdict(list)
        
        for student in students:
            section_name = student.section.name if student.section else 'No Section'
            
            for subject in assigned_subjects:
                # Get mark component
                mark_component = SubjectMarkComponents.objects.filter(
                    subject=subject,
                    teacher=teacher
                ).first()
                
                if not mark_component:
                    continue
                
                # Get marks for each component
                component_marks = {
                    'mid_term': {'uploaded': False, 'marks': 0, 'max': float(mark_component.mid_term_percentage)},
                    'final': {'uploaded': False, 'marks': 0, 'max': float(mark_component.final_term_percentage)},
                    'quiz': {'uploaded': False, 'marks': 0, 'max': float(mark_component.quiz_percentage)},
                    'assignment': {'uploaded': False, 'marks': 0, 'max': float(mark_component.assignment_percentage)},
                    'lab': {'uploaded': False, 'marks': 0, 'max': float(mark_component.lab_percentage)},
                    'attendance': {'uploaded': False, 'marks': 0, 'max': float(mark_component.attendance_percentage)},
                }
                
                total_marks = 0
                total_max = 0
                
                for exam_type in component_marks.keys():
                    exam = Exam.objects.filter(
                        subject_mark_component=mark_component,
                        exam_type=exam_type
                    ).first()
                    
                    if exam:
                        result = ExamResult.objects.filter(exam=exam, student=student).first()
                        if result and result.marks_obtained:
                            component_marks[exam_type]['uploaded'] = True
                            component_marks[exam_type]['marks'] = float(result.marks_obtained)
                            total_marks += float(result.marks_obtained)
                            total_max += component_marks[exam_type]['max']
                
                percentage = (total_marks / total_max * 100) if total_max > 0 else 0
                is_passed = percentage >= 50
                grade = calculate_grade(percentage)
                
                students_by_section[section_name].append({
                    'id': student.id,
                    'student_id': student.student_id,
                    'name': f"{student.first_name} {student.last_name}",
                    'email': student.email,
                    'section': section_name,
                    'subject_id': subject.id,
                    'subject_code': subject.code,
                    'subject_name': subject.name,
                    'mid_term': component_marks['mid_term'],
                    'final': component_marks['final'],
                    'quiz': component_marks['quiz'],
                    'assignment': component_marks['assignment'],
                    'lab': component_marks['lab'],
                    'attendance': component_marks['attendance'],
                    'total_marks': total_marks,
                    'percentage': percentage,
                    'grade': grade,
                    'is_passed': is_passed,
                })
        
        context = {
            'students_by_section': dict(students_by_section),
            'subjects': assigned_subjects,
            'sections': sections,
            'selected_subject_id': selected_subject_id,
            'selected_section_id': selected_section_id,
            'search_query': search_query,
        }
        
        return render(request, 'exam/student_subject_marks.html', context)
        
    except Teacher.DoesNotExist:
        messages.error(request, 'Teacher profile not found!')
        return redirect('dashboard')
def calculate_grade(percentage):
    """Calculate grade based on percentage"""
    if percentage >= 90:
        return 'A+'
    elif percentage >= 80:
        return 'A'
    elif percentage >= 70:
        return 'B'
    elif percentage >= 60:
        return 'C'
    elif percentage >= 50:
        return 'D'
    else:
        return 'F'



def upload_marks_dashboard(request):
    """Dashboard showing all subjects and sections for marks upload"""
    from teachers.models import Teacher
    from subject.models import SubjectAssign
    from student.models import Student
    
    try:
        teacher = Teacher.objects.get(user=request.user)
        
        # Get all subject assignments for this teacher
        subject_assignments = SubjectAssign.objects.filter(
            teacher=teacher,
            is_active=True
        ).select_related('subject', 'batch', 'semester', 'discipline').prefetch_related('sections')
        
        # Organize data by subject
        subjects_data = []
        processed_assignments = set()
        
        for assignment in subject_assignments:
            subject = assignment.subject
            
            # Skip if we already processed this subject (to avoid duplicates)
            if subject.id in processed_assignments:
                continue
            processed_assignments.add(subject.id)
            
            # Get mark distribution for this subject
            mark_component = SubjectMarkComponents.objects.filter(
                subject=subject,
                teacher=teacher
            ).first()
            
            if not mark_component:
                continue
            
            # Get all sections for this subject from all assignments
            all_sections = []
            all_assignments = SubjectAssign.objects.filter(
                teacher=teacher,
                subject=subject,
                is_active=True
            ).prefetch_related('sections')
            
            for assign in all_assignments:
                for section in assign.sections.all():
                    # Get student count
                    student_count = Student.objects.filter(section=section).count()
                    
                    # Get exam types with their status and max marks
                    exam_types = []
                    exam_type_list = [
                        ('mid_term', 'Mid Term', mark_component.mid_term_percentage),
                        ('final', 'Final', mark_component.final_term_percentage),
                        ('quiz', 'Quiz', mark_component.quiz_percentage),
                        ('assignment', 'Assignment', mark_component.assignment_percentage),
                        ('presentation', 'Presentation', mark_component.presentation_percentage),
                        ('lab', 'Lab', mark_component.lab_percentage),
                        ('viva', 'Viva', mark_component.viva_percentage),
                        ('attendance', 'Attendance', mark_component.attendance_percentage),
                    ]
                    
                    for exam_type, exam_name, percentage in exam_type_list:
                        if percentage > 0:
                            # Check if marks already uploaded
                            exam = Exam.objects.filter(
                                subject_mark_component=mark_component,
                                exam_type=exam_type
                            ).first()
                            
                            if exam:
                                results_count = ExamResult.objects.filter(
                                    exam=exam, 
                                    student__section=section
                                ).count()
                                uploaded = results_count > 0
                            else:
                                uploaded = False
                                results_count = 0
                            
                            exam_types.append({
                                'type': exam_type,
                                'name': exam_name,
                                'percentage': float(percentage),
                                'max_marks': float(percentage),  # Max marks equals percentage
                                'uploaded': uploaded,
                                'student_count': results_count,
                            })
                    
                    all_sections.append({
                        'section': section,
                        'batch': assign.batch,
                        'semester': assign.semester,
                        'student_count': student_count,
                        'exam_types': exam_types,
                    })
            
            subjects_data.append({
                'subject': subject,
                'mark_component': mark_component,
                'sections': all_sections,
            })
        
        context = {
            'teacher': teacher,
            'subjects_data': subjects_data,
        }
        
        return render(request, 'exam/upload_marks_dashboard.html', context)
        
    except Teacher.DoesNotExist:
        messages.error(request, 'Teacher profile not found!')
        return redirect('dashboard')
def select_exam_type_for_marks(request, subject_id, section_id):
    """Select exam type after choosing subject and section"""
    from teachers.models import Teacher
    
    subject = get_object_or_404(Subject, id=subject_id)
    section = get_object_or_404(Section, id=section_id)
    
    try:
        teacher = Teacher.objects.get(user=request.user)
        
        # Get mark distribution for this subject
        mark_component = SubjectMarkComponents.objects.filter(
            subject=subject,
            teacher=teacher
        ).first()
        
        if not mark_component:
            messages.error(request, 'Mark distribution not configured for this subject!')
            return redirect('upload_marks_dashboard')
        
        # Get available exam types (those with percentage > 0)
        available_exams = []
        for exam_type, exam_name in Exam.EXAM_TYPE_CHOICES:
            percentage = getattr(mark_component, f'{exam_type}_percentage', 0)
            if percentage > 0:
                # Check if already uploaded
                existing_exam = Exam.objects.filter(
                    subject_mark_component=mark_component,
                    exam_type=exam_type
                ).first()
                
                available_exams.append({
                    'type': exam_type,
                    'name': exam_name,
                    'percentage': percentage,
                    'is_uploaded': existing_exam is not None,
                    'exam_id': existing_exam.id if existing_exam else None,
                })
        
        context = {
            'subject': subject,
            'section': section,
            'teacher': teacher,
            'mark_component': mark_component,
            'available_exams': available_exams,
        }
        
        return render(request, 'exam/select_exam_type.html', context)
        
    except Teacher.DoesNotExist:
        messages.error(request, 'Teacher profile not found!')
        return redirect('upload_marks_dashboard')

def upload_marks_direct(request, subject_id, section_id, exam_type):
    """Direct marks upload for a specific exam type with proper max marks"""
    from teachers.models import Teacher
    from decimal import Decimal
    
    subject = get_object_or_404(Subject, id=subject_id)
    section = get_object_or_404(Section, id=section_id)
    
    try:
        teacher = Teacher.objects.get(user=request.user)
        
        # Get mark distribution for this subject
        mark_component = SubjectMarkComponents.objects.filter(
            subject=subject,
            teacher=teacher
        ).first()
        
        if not mark_component:
            messages.error(request, 'Mark distribution not configured for this subject!')
            return redirect('upload_marks_dashboard')
        
        # Get the percentage weightage for this exam type
        weightage_field = f'{exam_type}_percentage'
        weightage = float(getattr(mark_component, weightage_field, 0))
        
        # Calculate maximum marks based on weightage (out of 100 total)
        # If Mid Term = 15%, then max marks = 15
        max_marks = weightage  # Because total is 100 marks
        
        # Get or create exam for this type
        exam, created = Exam.objects.get_or_create(
            subject_mark_component=mark_component,
            exam_type=exam_type,
            defaults={
                'total_marks': Decimal(str(max_marks)),
                'passing_marks': Decimal(str(max_marks * 0.4)),  # 40% of max marks
                'weightage_percentage': Decimal(str(weightage)),
                'is_published': True,
            }
        )
        
        # Update exam if weightage changed
        if not created and exam.total_marks != max_marks:
            exam.total_marks = Decimal(str(max_marks))
            exam.passing_marks = Decimal(str(max_marks * 0.4))
            exam.weightage_percentage = Decimal(str(weightage))
            exam.save()
        
        # Get students in this section
        students = Student.objects.filter(section=section).order_by('student_id')
        
        # Get existing results
        existing_results = {}
        for result in ExamResult.objects.filter(exam=exam, student__in=students):
            existing_results[result.student.id] = result
        
        if request.method == 'POST':
            success_count = 0
            for student in students:
                marks_key = f'marks_{student.id}'
                marks_value = request.POST.get(marks_key)
                
                if marks_value:
                    try:
                        marks_obtained = Decimal(marks_value)
                        is_absent = request.POST.get(f'absent_{student.id}') == 'on'
                        remarks = request.POST.get(f'remarks_{student.id}', '')
                        
                        # Validate marks not exceeding max_marks
                        if marks_obtained > Decimal(str(max_marks)):
                            messages.warning(request, f'Marks for {student.first_name} {student.last_name} exceed maximum ({max_marks})')
                            marks_obtained = Decimal(str(max_marks))
                        
                        result, result_created = ExamResult.objects.update_or_create(
                            exam=exam,
                            student=student,
                            defaults={
                                'marks_obtained': marks_obtained,
                                'is_absent': is_absent,
                                'remarks': remarks,
                                'entered_by': teacher,
                            }
                        )
                        success_count += 1
                    except:
                        pass
            
            # messages.success(request, f'Successfully saved marks for {success_count} students!')
            return redirect('view_marks', subject_id=subject_id, section_id=section_id, exam_type=exam_type)
        
        context = {
            'subject': subject,
            'section': section,
            'exam_type': exam_type,
            'exam_type_display': dict(Exam.EXAM_TYPE_CHOICES).get(exam_type, exam_type),
            'exam': exam,
            'students': students,
            'existing_results': existing_results,
            'mark_component': mark_component,
            'weightage': weightage,
            'max_marks': max_marks,  # This is the important field - max marks for this exam
        }
        
        return render(request, 'exam/upload_marks_direct.html', context)
        
    except Teacher.DoesNotExist:
        messages.error(request, 'Teacher profile not found!')
        return redirect('upload_marks_dashboard')

def view_marks(request, subject_id, section_id, exam_type):
    """View uploaded marks for a specific exam type"""
    from teachers.models import Teacher
    from student.models import Student
    from subject.models import Subject
    from Academic.models import Section
    from .models import SubjectMarkComponents, Exam, ExamResult
    
    subject = get_object_or_404(Subject, id=subject_id)
    section = get_object_or_404(Section, id=section_id)
    
    try:
        teacher = Teacher.objects.get(user=request.user)
        
        # Get mark distribution
        mark_component = SubjectMarkComponents.objects.filter(
            subject=subject,
            teacher=teacher
        ).first()
        
        if not mark_component:
            messages.error(request, 'Mark distribution not configured!')
            return redirect('upload_marks_dashboard')
        
        # Get exam
        exam = Exam.objects.filter(
            subject_mark_component=mark_component,
            exam_type=exam_type
        ).first()
        
        if not exam:
            messages.warning(request, 'No marks uploaded yet for this exam type!')
            return redirect('upload_marks_dashboard')
        
        # Get students in this section
        students = Student.objects.filter(section=section).order_by('student_id')
        
        # Prepare student data with results
        students_data = []
        present_count = 0
        absent_count = 0
        marks_list = []
        
        for student in students:
            try:
                result = ExamResult.objects.get(exam=exam, student=student)
                has_result = True
                marks_obtained = result.marks_obtained
                percentage = result.percentage
                is_absent = result.is_absent
                remarks = result.remarks
                
                if is_absent:
                    absent_count += 1
                elif marks_obtained is not None:
                    present_count += 1
                    marks_list.append(float(marks_obtained))
            except ExamResult.DoesNotExist:
                has_result = False
                marks_obtained = None
                percentage = None
                is_absent = False
                remarks = ''
            
            students_data.append({
                'id': student.id,
                'student_id': student.student_id,
                'first_name': student.first_name,
                'last_name': student.last_name,
                'has_result': has_result,
                'marks_obtained': marks_obtained,
                'percentage': percentage,
                'is_absent': is_absent,
                'remarks': remarks,
            })
        
        # Calculate average marks
        avg_marks = sum(marks_list) / len(marks_list) if marks_list else 0
        total_students = len(students_data)
        
        context = {
            'subject': subject,
            'section': section,
            'exam_type': exam_type,
            'exam_type_display': dict(Exam.EXAM_TYPE_CHOICES).get(exam_type, exam_type),
            'exam': exam,
            'students_data': students_data,
            'total_students': total_students,
            'present_count': present_count,
            'absent_count': absent_count,
            'avg_marks': round(avg_marks, 2),
        }
        
        return render(request, 'exam/view_marks.html', context)
        
    except Teacher.DoesNotExist:
        messages.error(request, 'Teacher profile not found!')
        return redirect('upload_marks_dashboard')
def delete_mark_component(request, id):
    """Delete mark distribution configuration - Only if no marks uploaded"""
    from teachers.models import Teacher
    from .models import Exam, ExamResult
    from django.contrib import messages
    from django.shortcuts import get_object_or_404, redirect
    
    try:
        teacher = Teacher.objects.get(user=request.user)
    except Teacher.DoesNotExist:
        messages.error(request, 'Teacher profile not found!')
        return redirect('subject_mark_components')
    
    # Get the component
    component = get_object_or_404(SubjectMarkComponents, id=id)
    
    # Verify teacher owns this configuration
    if component.teacher_id != teacher.id:
        messages.error(request, 'You are not authorized to delete this configuration!')
        return redirect('subject_mark_components')
    
    # Check if any marks have been uploaded for this configuration
    exams = Exam.objects.filter(subject_mark_component=component)
    has_marks = False
    for exam in exams:
        if ExamResult.objects.filter(exam=exam).exists():
            has_marks = True
            break
    
    if has_marks:
        messages.error(request, 'Cannot delete configuration because marks have already been uploaded!')
        return redirect('subject_mark_components')
    
    if request.method == 'POST':
        try:
            subject_code = component.subject.code
            component.delete()
            messages.success(request, f'Mark distribution for {subject_code} deleted successfully!')
        except Exception as e:
            messages.error(request, f'Error deleting configuration: {str(e)}')
        return redirect('subject_mark_components')
    
    # GET request - show confirmation page
    context = {
        'component': component,
        'title': 'Delete Mark Distribution'
    }
    return render(request, 'exam/delete_confirmation.html', context)

        