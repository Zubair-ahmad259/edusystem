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

# exam

# def create_exam(request):
#     if request.method == 'POST':
#         try:
#             # Get form data
#             exam_type = request.POST.get('exam_type')
#             subject_mark_component_id = request.POST.get('subject_mark_component')
#             exam_date = request.POST.get('exam_date')
#             total_marks = request.POST.get('total_marks')
#             passing_marks = request.POST.get('passing_marks')
#             weightage_percentage = request.POST.get('weightage_percentage', 100.00)
#             is_published = request.POST.get('is_published') == 'on'
            
#             # Get subject mark component
#             subject_mark_component = SubjectMarkComponents.objects.get(id=subject_mark_component_id)
            
#             # Create exam
#             exam = Exam.objects.create(
#                 exam_type=exam_type,
#                 subject_mark_component=subject_mark_component,
#                 exam_date=exam_date,
#                 total_marks=Decimal(total_marks),
#                 passing_marks=Decimal(passing_marks) if passing_marks else Decimal('0.00'),
#                 weightage_percentage=Decimal(weightage_percentage),
#                 is_published=is_published
#             )
            
#             return redirect('exam_dashboard', exam_id=exam.id)
            
#         except Exception as e:
#             context = {
#                 'error': str(e),
#                 'subject_mark_components': SubjectMarkComponents.objects.all(),
#             }
#             return render(request, 'exam/create_exam.html', context)
    
#     # GET request
#     context = {
#         'subject_mark_components': SubjectMarkComponents.objects.all(),
#         'exam_types': Exam.EXAM_TYPE_CHOICES,
#     }
#     return render(request, 'exam/create_exam.html', context)


def create_exam(request):
    """Create a new exam"""
    # GET request - show the form
    if request.method == 'GET':
        try:
            # Get current date for today's default
            today = datetime.now()
            
            # Get all subject mark components
            subject_mark_components = SubjectMarkComponents.objects.all().select_related(
                'subject', 'semester', 'batch'
            )
            
            # Get exam types from Exam model
            exam_types = Exam.EXAM_TYPE_CHOICES
            
            context = {
                'subject_mark_components': subject_mark_components,
                'exam_types': exam_types,
                'today': today,
                'exams': Exam.objects.all().order_by('-created_at')[:5],  # Recent exams for sidebar
            }
            
            return render(request, 'exam/create_exam.html', context)
            
        except Exception as e:
            # Log the error for debugging
            print(f"Error in create_exam GET: {str(e)}")
            
            # Return a simple error page or redirect
            context = {
                'error': f'Error loading form: {str(e)}',
                'subject_mark_components': SubjectMarkComponents.objects.all(),
                'exam_types': Exam.EXAM_TYPE_CHOICES,
                'today': datetime.now(),
            }
            return render(request, 'exam/create_exam.html', context)
    
    # POST request - process form submission
    elif request.method == 'POST':
        try:
            # Get form data
            exam_type = request.POST.get('exam_type')
            subject_mark_component_id = request.POST.get('subject_mark_component')
            exam_date = request.POST.get('exam_date')
            total_marks = request.POST.get('total_marks')
            passing_marks = request.POST.get('passing_marks')
            weightage_percentage = request.POST.get('weightage_percentage', 100.00)
            is_published = request.POST.get('is_published') == 'on'
            
            # Validate required fields
            if not all([exam_type, subject_mark_component_id, exam_date, total_marks]):
                messages.error(request, 'Please fill all required fields!')
                return redirect('create_exam')
            
            # Get subject mark component
            subject_mark_component = SubjectMarkComponents.objects.get(id=subject_mark_component_id)
            
            # Create exam
            exam = Exam.objects.create(
                exam_type=exam_type,
                subject_mark_component=subject_mark_component,
                exam_date=exam_date,
                total_marks=Decimal(total_marks),
                passing_marks=Decimal(passing_marks) if passing_marks else Decimal('0.00'),
                weightage_percentage=Decimal(weightage_percentage),
                is_published=is_published
            )
            
            messages.success(request, f'Exam created successfully for {subject_mark_component.subject.code}!')
            return redirect('exam_dashboard', exam_id=exam.id)
            
        except SubjectMarkComponents.DoesNotExist:
            messages.error(request, 'Selected subject configuration does not exist!')
            return redirect('create_exam')
        except Exception as e:
            messages.error(request, f'Error creating exam: {str(e)}')
            
            # Return to form with error
            context = {
                'error': str(e),
                'subject_mark_components': SubjectMarkComponents.objects.all(),
                'exam_types': Exam.EXAM_TYPE_CHOICES,
                'today': datetime.now(),
            }
            return render(request, 'exam/create_exam.html', context)
    
    # If not GET or POST, return error
    return render(request, 'exam/error.html', {'error': 'Invalid request method'})

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

# def subject_mark_components(request):
#     """Configure mark distribution for subjects"""
#     if request.method == 'POST':
#         subject_id = request.POST.get('subject')
#         teacher_id = request.POST.get('teacher')
#         semester_id = request.POST.get('semester')
#         batch_id = request.POST.get('batch')
#         section_id = request.POST.get('section')
#         discipline_id = request.POST.get('discipline')
#         academic_year = request.POST.get('academic_year')
        
#         component, created = SubjectMarkComponents.objects.update_or_create(
#             subject_id=subject_id,
#             teacher_id=teacher_id,
#             semester_id=semester_id,
#             batch_id=batch_id,
#             section_id=section_id if section_id else None,
#             discipline_id=discipline_id,
#             academic_year=academic_year,
#             defaults={
#                 'mid_term_percentage': Decimal(request.POST.get('mid_term', 20.00)),
#                 'final_term_percentage': Decimal(request.POST.get('final', 65.00)),
#                 'quiz_percentage': Decimal(request.POST.get('quiz', 5.00)),
#                 'assignment_percentage': Decimal(request.POST.get('assignment', 5.00)),
#                 'presentation_percentage': Decimal(request.POST.get('presentation', 5.00)),
#                 'lab_percentage': Decimal(request.POST.get('lab', 0.00)),
#                 'viva_percentage': Decimal(request.POST.get('viva', 0.00)),
#                 'attendance_percentage': Decimal(request.POST.get('attendance', 5.00)),
#                 'notes': request.POST.get('notes', ''),
#             }
#         )
        
#         return redirect('subject_mark_components')
    
#     components = SubjectMarkComponents.objects.all().select_related(
#         'subject', 'teacher', 'semester', 'batch', 'section', 'discipline'
#     )
    
#     context = {
#         'components': components,
#         'subjects': Subject.objects.all(),
#         'teachers': Teacher.objects.all(),
#         'semesters': Semester.objects.all(),
#         'batches': Batch.objects.all(),
#         'sections': Section.objects.all(),
#         'disciplines': Discipline.objects.all(),
#     }
    
#     return render(request, 'exam/subject_mark_components.html', context)

from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from datetime import datetime
from decimal import Decimal
from exam_mang.models import SubjectMarkComponents, Subject, Teacher, Semester, Batch, Section, Discipline

def subject_mark_components(request):
    """Configure mark distribution for subjects"""
    if request.method == 'POST':
        try:
            # Get form data
            subject_id = request.POST.get('subject')
            teacher_id = request.POST.get('teacher')
            semester_id = request.POST.get('semester')
            batch_id = request.POST.get('batch')
            section_id = request.POST.get('section')
            discipline_id = request.POST.get('discipline')
            academic_year = request.POST.get('academic_year')
            
            # Validate required fields
            if not all([subject_id, teacher_id, semester_id, batch_id, discipline_id, academic_year]):
                messages.error(request, 'Please fill all required fields!')
                return redirect('subject_mark_components')
            
            # Handle section - convert empty string to None
            section_val = section_id if section_id and section_id != '' else None
            
            # Create filter dictionary
            filter_kwargs = {
                'subject_id': subject_id,
                'teacher_id': teacher_id,
                'semester_id': semester_id,
                'batch_id': batch_id,
                'discipline_id': discipline_id,
                'academic_year': academic_year,
            }
            
            # Add section condition
            if section_val:
                filter_kwargs['section_id'] = section_val
            else:
                filter_kwargs['section__isnull'] = True
            
            # Parse percentage values with safe defaults
            mid_term = Decimal(request.POST.get('mid_term', '20.00'))
            final_term = Decimal(request.POST.get('final', '65.00'))
            quiz = Decimal(request.POST.get('quiz', '5.00'))
            assignment = Decimal(request.POST.get('assignment', '5.00'))
            presentation = Decimal(request.POST.get('presentation', '0.00'))
            lab = Decimal(request.POST.get('lab', '0.00'))
            viva = Decimal(request.POST.get('viva', '0.00'))
            attendance = Decimal(request.POST.get('attendance', '5.00'))
            
            # Calculate total
            total = (mid_term + final_term + quiz + assignment + 
                    presentation + lab + viva + attendance)
            
            # Validate total is 100%
            if abs(total - Decimal('100.00')) > Decimal('0.01'):
                messages.warning(request, f'Total percentage is {total}%, not 100%.')
            
            # Create or update the component
            component, created = SubjectMarkComponents.objects.update_or_create(
                **filter_kwargs,
                defaults={
                    'mid_term_percentage': mid_term,
                    'final_term_percentage': final_term,
                    'quiz_percentage': quiz,
                    'assignment_percentage': assignment,
                    'presentation_percentage': presentation,
                    'lab_percentage': lab,
                    'viva_percentage': viva,
                    'attendance_percentage': attendance,
                    'notes': request.POST.get('notes', ''),
                }
            )
            
            if created:
                messages.success(request, 'Mark distribution configuration created successfully!')
            else:
                messages.success(request, 'Mark distribution configuration updated successfully!')
                
        except Subject.DoesNotExist:
            messages.error(request, 'Selected subject does not exist!')
        except Teacher.DoesNotExist:
            messages.error(request, 'Selected teacher does not exist!')
        except Semester.DoesNotExist:
            messages.error(request, 'Selected semester does not exist!')
        except Batch.DoesNotExist:
            messages.error(request, 'Selected batch does not exist!')
        except Discipline.DoesNotExist:
            messages.error(request, 'Selected discipline does not exist!')
        except Exception as e:
            messages.error(request, f'Error saving configuration: {str(e)}')
        
        return redirect('subject_mark_components')
    
    # GET request - show the form
    # Get current date for academic year
    current_year = datetime.now().year
    next_year = current_year + 1
    
    # Get all necessary data
    components = SubjectMarkComponents.objects.all().select_related(
        'subject', 'teacher', 'semester', 'batch', 'section', 'discipline'
    ).order_by('-id')
    
    context = {
        'components': components,
        'subjects': Subject.objects.all(),
        'teachers': Teacher.objects.all(),
        'semesters': Semester.objects.all(),
        'batches': Batch.objects.all(),
        'sections': Section.objects.all(),
        'disciplines': Discipline.objects.all(),
        'current_year': current_year,
        'next_year': next_year,
    }
    
    return render(request, 'exam/subject_mark_components.html', context)  # MAKE SURE THIS LINE RETURNS!

def load_mark_component(request, id):
    """Load configuration data for editing"""
    try:
        component = SubjectMarkComponents.objects.get(id=id)
        data = {
            'success': True,
            'subject_id': component.subject_id,
            'teacher_id': component.teacher_id,
            'semester_id': component.semester_id,
            'batch_id': component.batch_id,
            'section_id': component.section_id,
            'discipline_id': component.discipline_id,
            'academic_year': component.academic_year,
            'notes': component.notes,
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
    except SubjectMarkComponents.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Configuration not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

def delete_mark_component(request, id):
    """Delete confirmation page for mark distribution configuration"""
    # Get the component or show 404 error
    component = get_object_or_404(SubjectMarkComponents, id=id)
    
    if request.method == 'POST':
        # User confirmed deletion
        subject_code = component.subject.code
        component.delete()
        messages.success(request, f'Mark distribution for {subject_code} has been deleted successfully!')
        return redirect('subject_mark_components')
    
    # Show confirmation page for GET request
    return render(request, 'exam/delete_confirmation.html', {
        'component': component,
        'title': 'Delete Mark Distribution'
    })

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