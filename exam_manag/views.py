from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.db.models import Avg, Q, Count
from datetime import datetime, timedelta
from decimal import Decimal
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from .models import Exam, ExamResult, StudentSubjectResult, ComprehensiveResult, Transcript, TranscriptRequest
from student.models import Student
from Academic.models import Batch, Semester, Section, Discipline
from subject.models import Subject, SubjectAssign
from teachers.models import Teacher
from home_auth.models import CustomUser
from django.contrib.auth import get_user_model

# ==================== MAIN DASHBOARDS ====================

def dashboard(request):
    """Main dashboard page"""
    User = get_user_model()
    
    total_exams = Exam.objects.count()
    published_exams = Exam.objects.filter(is_published=True).count()
    
    exams_with_results = 0
    for exam in Exam.objects.all():
        if ExamResult.objects.filter(exam=exam).exists():
            exams_with_results += 1
    
    exams_without_results = total_exams - exams_with_results
    
    upcoming_date = datetime.now() + timedelta(days=7)
    upcoming_exams = Exam.objects.filter(
        exam_date__gte=datetime.now().date(),
        exam_date__lte=upcoming_date.date()
    ).order_by('exam_date')[:5]
    
    recent_exams = Exam.objects.all().select_related('subject', 'section').order_by('-created_at')
    
    active_users = User.objects.filter(is_active=True).count()
    
    recent_transcripts = Transcript.objects.filter(
        is_issued=True
    ).select_related('student').order_by('-created_at')[:5]
    
    comprehensive_results_count = ComprehensiveResult.objects.count()
    
    student_comprehensive_stats = None
    if request.user.is_authenticated:
        try:
            student = Student.objects.get(user=request.user)
            comp_results = ComprehensiveResult.objects.filter(student=student)
            
            if comp_results.exists():
                total_subjects = 0
                passed_subjects = 0
                failed_subjects = 0
                for result in comp_results:
                    total_subjects += result.passed_subjects + result.failed_subjects
                    passed_subjects += result.passed_subjects
                    failed_subjects += result.failed_subjects
                
                student_comprehensive_stats = {
                    'total_subjects': total_subjects,
                    'passed_subjects': passed_subjects,
                    'failed_subjects': failed_subjects,
                    'cumulative_gpa': 0,
                    'student': student,
                }
        except Student.DoesNotExist:
            pass
    
    context = {
        'exams': recent_exams,
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
    """Exam detail dashboard"""
    exam = get_object_or_404(Exam, id=exam_id)
    students = exam.get_students()
    results = ExamResult.objects.filter(exam=exam)
    
    total_students = students.count()
    results_entered = results.count()
    absent_count = results.filter(is_absent=True).count()
    
    passed_count = 0
    failed_count = 0
    total_marks_sum = Decimal('0.00')
    total_percentage_sum = Decimal('0.00')
    marks_count = 0
    
    for result in results:
        if not result.is_absent and result.marks_obtained is not None:
            marks_count += 1
            total_marks_sum += result.marks_obtained
            if exam.total_marks > 0:
                percentage = (result.marks_obtained / exam.total_marks) * 100
                total_percentage_sum += percentage
                if percentage >= 40:
                    passed_count += 1
                else:
                    failed_count += 1
        elif not result.is_absent and result.marks_obtained is None:
            failed_count += 1
    
    avg_marks = total_marks_sum / marks_count if marks_count > 0 else Decimal('0.00')
    avg_percentage = total_percentage_sum / marks_count if marks_count > 0 else Decimal('0.00')
    
    grade_distribution = {'A+': 0, 'A': 0, 'B+': 0, 'B': 0, 'C+': 0, 'C': 0, 'D': 0, 'F': 0}
    
    for result in results:
        if not result.is_absent and result.marks_obtained is not None:
            if exam.total_marks > 0:
                pct = float((result.marks_obtained / exam.total_marks) * 100)
                if pct >= 90:
                    grade_distribution['A+'] += 1
                elif pct >= 80:
                    grade_distribution['A'] += 1
                elif pct >= 70:
                    grade_distribution['B+'] += 1
                elif pct >= 60:
                    grade_distribution['B'] += 1
                elif pct >= 50:
                    grade_distribution['C+'] += 1
                elif pct >= 40:
                    grade_distribution['C'] += 1
                elif pct >= 33:
                    grade_distribution['D'] += 1
                else:
                    grade_distribution['F'] += 1
        else:
            grade_distribution['F'] += 1
    
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
        'avg_marks': round(avg_marks, 2),
        'avg_percentage': round(avg_percentage, 2),
    }
    return render(request, 'exam/exam_dashboard.html', context)


# ==================== MARKS UPLOAD (TEACHER) - NO CONFIGURATION NEEDED ====================

def upload_marks_dashboard(request):
    """Dashboard showing all subjects and sections for marks upload - NO CONFIGURATION NEEDED"""
    try:
        teacher = Teacher.objects.get(user=request.user)
        
        subject_assignments = SubjectAssign.objects.filter(
            teacher=teacher,
            is_active=True
        ).select_related('subject').prefetch_related('sections')
        
        subjects_data = []
        processed_subjects = set()
        
        for assignment in subject_assignments:
            subject = assignment.subject
            
            if subject.id in processed_subjects:
                continue
            processed_subjects.add(subject.id)
            
            sections_data = []
            
            for section in assignment.sections.all():
                student_count = Student.objects.filter(section=section).count()
                
                # All exam types - teacher can upload any of these
                components = [
                    {'type': 'mid_term', 'name': 'Mid Term'},
                    {'type': 'final', 'name': 'Final'},
                    {'type': 'quiz', 'name': 'Quiz'},
                    {'type': 'assignment', 'name': 'Assignment'},
                    {'type': 'lab', 'name': 'Lab'},
                    {'type': 'attendance', 'name': 'Attendance'},
                ]
                
                exam_types = []
                for comp in components:
                    exam = Exam.objects.filter(
                        subject=subject,
                        section=section,
                        exam_type=comp['type']
                    ).first()
                    
                    if exam:
                        results_count = ExamResult.objects.filter(
                            exam=exam,
                            student__section=section
                        ).count()
                        uploaded = results_count > 0
                        max_marks = float(exam.total_marks)
                        is_published = exam.is_published
                    else:
                        uploaded = False
                        results_count = 0
                        max_marks = 100
                        is_published = False
                    
                    exam_types.append({
                        'type': comp['type'],
                        'name': comp['name'],
                        'max_marks': max_marks,
                        'uploaded': uploaded,
                        'student_count': results_count,
                        'is_published': is_published,
                    })
                
                uploaded_count = sum(1 for e in exam_types if e['uploaded'])
                total_components = len(exam_types)
                upload_percentage = int((uploaded_count / total_components) * 100) if total_components > 0 else 0
                
                sections_data.append({
                    'section': section,
                    'student_count': student_count,
                    'exam_types': exam_types,
                    'uploaded_count': uploaded_count,
                    'upload_percentage': upload_percentage,
                    'total_components': total_components,
                })
            
            subjects_data.append({
                'subject': subject,
                'sections': sections_data,
            })
        
        context = {
            'teacher': teacher,
            'subjects_data': subjects_data,
        }
        return render(request, 'exam/upload_marks_dashboard.html', context)
        
    except Teacher.DoesNotExist:
        messages.error(request, 'Teacher profile not found!')
        return redirect('dashboard')

def upload_marks_direct(request, subject_id, section_id, exam_type):
    """Direct marks upload - Teacher can set total marks"""
    subject = get_object_or_404(Subject, id=subject_id)
    section = get_object_or_404(Section, id=section_id)
    
    try:
        teacher = Teacher.objects.get(user=request.user)
        
        # Get or create exam
        exam, created = Exam.objects.get_or_create(
            subject=subject,
            section=section,
            exam_type=exam_type,
            defaults={
                'total_marks': Decimal('100'),
                'teacher': teacher,
            }
        )
        
        students = Student.objects.filter(section=section).order_by('student_id')
        
        if request.method == 'POST':
            total_marks = Decimal(request.POST.get('total_marks', exam.total_marks))
            exam.total_marks = total_marks
            exam.save()
            
            success_count = 0
            for student in students:
                marks_key = f'marks_{student.id}'
                marks_value = request.POST.get(marks_key)
                
                if marks_value:
                    try:
                        marks_obtained = Decimal(marks_value)
                        is_absent = request.POST.get(f'absent_{student.id}') == 'on'
                        remarks = request.POST.get(f'remarks_{student.id}', '')
                        
                        if marks_obtained > total_marks:
                            marks_obtained = total_marks
                        
                        ExamResult.objects.update_or_create(
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
            
            if success_count > 0:
                # Update student subject results
                for student in students:
                    update_student_subject_result(student, subject, section)
                    # Update comprehensive result
                    update_comprehensive_result_for_student(student)
            
            messages.success(request, f'Successfully saved marks for {success_count} students!')
            return redirect('exam_manag:upload_marks_dashboard')
        
        # GET request - prepare form
        students_data = []
        for student in students:
            try:
                result = ExamResult.objects.get(exam=exam, student=student)
                students_data.append({
                    'id': student.id,
                    'student_id': student.student_id,
                    'first_name': student.first_name,
                    'last_name': student.last_name,
                    'marks_obtained': float(result.marks_obtained) if result.marks_obtained else '',
                    'is_absent': result.is_absent,
                    'remarks': result.remarks,
                })
            except ExamResult.DoesNotExist:
                students_data.append({
                    'id': student.id,
                    'student_id': student.student_id,
                    'first_name': student.first_name,
                    'last_name': student.last_name,
                    'marks_obtained': '',
                    'is_absent': False,
                    'remarks': '',
                })
        
        context = {
            'subject': subject,
            'section': section,
            'exam_type': exam_type,
            'exam_type_display': exam_type.replace('_', ' ').title(),
            'exam': exam,
            'students': students_data,
            'total_marks': float(exam.total_marks),
        }
        return render(request, 'exam/upload_marks_direct.html', context)
        
    except Teacher.DoesNotExist:
        messages.error(request, 'Teacher profile not found!')
        return redirect('dashboard')

def view_marks(request, subject_id, section_id, exam_type):
    """View uploaded marks for a specific exam type"""
    subject = get_object_or_404(Subject, id=subject_id)
    section = get_object_or_404(Section, id=section_id)
    
    # Get the exam
    exam = get_object_or_404(Exam, subject=subject, section=section, exam_type=exam_type)
    
    # Get all students in this section
    students = Student.objects.filter(section=section).order_by('student_id')
    
    # Prepare student data with results
    students_data = []
    present_count = 0
    absent_count = 0
    marks_list = []
    
    for student in students:
        try:
            result = ExamResult.objects.get(exam=exam, student=student)
            marks_obtained = result.marks_obtained
            is_absent = result.is_absent
            percentage = float(marks_obtained) / float(exam.total_marks) * 100 if marks_obtained else 0
            status = 'Absent' if is_absent else ('Passed' if percentage >= 40 else 'Failed') if marks_obtained is not None else 'Not Entered'
            
            if is_absent:
                absent_count += 1
            elif marks_obtained is not None:
                present_count += 1
                marks_list.append(float(marks_obtained))
                
            students_data.append({
                'id': student.id,
                'student_id': student.student_id,
                'first_name': student.first_name,
                'last_name': student.last_name,
                'email': student.email,
                'marks_obtained': float(marks_obtained) if marks_obtained else None,
                'percentage': round(percentage, 2) if marks_obtained else None,
                'is_absent': is_absent,
                'status': status,
                'remarks': result.remarks,
            })
        except ExamResult.DoesNotExist:
            students_data.append({
                'id': student.id,
                'student_id': student.student_id,
                'first_name': student.first_name,
                'last_name': student.last_name,
                'email': student.email,
                'marks_obtained': None,
                'percentage': None,
                'is_absent': False,
                'status': 'Not Entered',
                'remarks': '',
            })
    
    avg_marks = sum(marks_list) / len(marks_list) if marks_list else 0
    
    context = {
        'subject': subject,
        'section': section,
        'exam_type': exam_type,
        'exam_type_display': exam.get_exam_type_display(),
        'exam': exam,
        'students_data': students_data,
        'total_students': len(students_data),
        'present_count': present_count,
        'absent_count': absent_count,
        'avg_marks': round(avg_marks, 2),
    }
    return render(request, 'exam/view_marks.html', context)
def delete_all_exam_results(request, subject_id, section_id, exam_type):
    """Delete all results for a specific exam"""
    subject = get_object_or_404(Subject, id=subject_id)
    section = get_object_or_404(Section, id=section_id)
    exam = get_object_or_404(Exam, subject=subject, section=section, exam_type=exam_type)
    
    if request.method == 'POST':
        # Delete all exam results for this exam
        deleted_count = ExamResult.objects.filter(exam=exam).count()
        ExamResult.objects.filter(exam=exam).delete()
        
        # Get all students in this section
        students = Student.objects.filter(section=section)
        
        # Update student subject results and comprehensive results
        for student in students:
            update_student_subject_result(student, subject, section)
            update_comprehensive_result_for_student(student)
        
        messages.success(request, f'✅ Deleted {deleted_count} results for {subject.code} - {exam_type} exam')
        return redirect('exam_manag:view_marks', subject_id=subject_id, section_id=section_id, exam_type=exam_type)
    
    return redirect('exam_manag:view_marks', subject_id=subject_id, section_id=section_id, exam_type=exam_type)


def edit_student_mark(request, subject_id, section_id, exam_type, student_id):
    """Edit individual student mark"""
    subject = get_object_or_404(Subject, id=subject_id)
    section = get_object_or_404(Section, id=section_id)
    exam = get_object_or_404(Exam, subject=subject, section=section, exam_type=exam_type)
    student = get_object_or_404(Student, id=student_id)
    
    if request.method == 'POST':
        marks_obtained = request.POST.get('marks_obtained')
        is_absent = request.POST.get('is_absent') == 'on'
        remarks = request.POST.get('remarks', '')
        
        if marks_obtained and marks_obtained != '':
            marks_obtained = Decimal(marks_obtained)
            if marks_obtained > exam.total_marks:
                marks_obtained = exam.total_marks
        else:
            marks_obtained = None
        
        # Update or create exam result
        result, created = ExamResult.objects.update_or_create(
            exam=exam,
            student=student,
            defaults={
                'marks_obtained': marks_obtained if marks_obtained is not None else Decimal('0') if is_absent else None,
                'is_absent': is_absent,
                'remarks': remarks,
                'entered_by': Teacher.objects.get(user=request.user),
            }
        )
        
        # Update student subject result
        update_student_subject_result(student, subject, section)
        
        # Update comprehensive result
        update_comprehensive_result_for_student(student)
        
        messages.success(request, f'✅ Marks updated for {student.first_name} {student.last_name}')
        return redirect('exam_manag:view_marks', subject_id=subject_id, section_id=section_id, exam_type=exam_type)
    
    return redirect('exam_manag:view_marks', subject_id=subject_id, section_id=section_id, exam_type=exam_type)


def delete_student_mark(request, subject_id, section_id, exam_type, student_id):
    """Delete individual student mark"""
    subject = get_object_or_404(Subject, id=subject_id)
    section = get_object_or_404(Section, id=section_id)
    exam = get_object_or_404(Exam, subject=subject, section=section, exam_type=exam_type)
    student = get_object_or_404(Student, id=student_id)
    
    if request.method == 'POST':
        # Delete the exam result
        ExamResult.objects.filter(exam=exam, student=student).delete()
        
        # Update student subject result
        update_student_subject_result(student, subject, section)
        
        # Update comprehensive result
        update_comprehensive_result_for_student(student)
        
        messages.success(request, f'✅ Marks deleted for {student.first_name} {student.last_name}')
        return redirect('exam_manag:view_marks', subject_id=subject_id, section_id=section_id, exam_type=exam_type)
    
    return redirect('exam_manag:view_marks', subject_id=subject_id, section_id=section_id, exam_type=exam_type)
def publish_section_marks(request, subject_id, section_id):
    """Publish all unpublished uploaded marks for a section - MANUAL ONLY"""
    try:
        teacher = Teacher.objects.get(user=request.user)
    except Teacher.DoesNotExist:
        messages.error(request, 'Teacher profile not found!')
        return redirect('exam_manag:upload_marks_dashboard')
    
    subject = get_object_or_404(Subject, id=subject_id)
    section = get_object_or_404(Section, id=section_id)
    
    exam_type_list = ['mid_term', 'final', 'quiz', 'assignment', 'lab', 'attendance']
    published_count = 0
    
    for exam_type in exam_type_list:
        exam = Exam.objects.filter(
            subject=subject,
            section=section,
            exam_type=exam_type
        ).first()
        
        if exam:
            has_results = ExamResult.objects.filter(
                exam=exam,
                student__section=section
            ).exists()
            
            if has_results and not exam.is_published:
                exam.is_published = True
                exam.published_at = timezone.now()
                exam.save()
                published_count += 1
    
    if published_count > 0:
        # Update student results for ALL students in this section
        students = Student.objects.filter(section=section)
        
        for student in students:
            # Update StudentSubjectResult for this student and subject
            update_student_subject_result(student, subject, section)
            # Update comprehensive result for this student
            update_comprehensive_result_for_student(student)
        
        messages.success(request, f'✅ Published {published_count} components and updated comprehensive results for {subject.code} - Section {section.name}')
    else:
        messages.info(request, f'No unpublished components found for {subject.code} - Section {section.name}')
    
    return redirect('exam_manag:upload_marks_dashboard')

# ==================== UPDATE STUDENT RESULTS ====================

def update_student_subject_result(student, subject, section):
    """Update StudentSubjectResult for a student in a subject with calculations"""
    semester = student.semester
    
    # Get all published exams for this subject and section
    exams = Exam.objects.filter(
        subject=subject,
        section=section,
        is_published=True
    )
    
    marks = {
        'mid_term_marks': Decimal('0'),
        'final_marks': Decimal('0'),
        'quiz_marks': Decimal('0'),
        'assignment_marks': Decimal('0'),
        'lab_marks': Decimal('0'),
        'attendance_marks': Decimal('0'),
    }
    
    for exam in exams:
        try:
            result = ExamResult.objects.get(exam=exam, student=student)
            if result.marks_obtained is not None and not result.is_absent:
                field_name = f"{exam.exam_type}_marks"
                if field_name in marks:
                    marks[field_name] = result.marks_obtained
        except ExamResult.DoesNotExist:
            pass
            
    # Calculate Total Obtained Marks
    obtained_total = (
        marks['mid_term_marks'] + marks['final_marks'] + 
        marks['quiz_marks'] + marks['assignment_marks'] + 
        marks['lab_marks'] + marks['attendance_marks']
    )
    
    # ASSUMPTION: Out of 100 maximum marks. Adjust if your system uses different weighting.
    total_possible = Decimal('100.00') 
    percentage = (obtained_total / total_possible) * 100 if total_possible > 0 else Decimal('0')
    
    # Assign Grade based on your dashboard rules
    if percentage >= 90: grade = 'A+'
    elif percentage >= 80: grade = 'A'
    elif percentage >= 70: grade = 'B+'
    elif percentage >= 60: grade = 'B'
    elif percentage >= 50: grade = 'C+'
    elif percentage >= 40: grade = 'C'
    elif percentage >= 33: grade = 'D'
    else: grade = 'F'
    
    is_passed = percentage >= 40

    subject_result, created = StudentSubjectResult.objects.update_or_create(
        student=student,
        subject=subject,
        defaults={
            'semester': semester,
            'section': section,
            'mid_term_marks': marks['mid_term_marks'],
            'final_marks': marks['final_marks'],
            'quiz_marks': marks['quiz_marks'],
            'assignment_marks': marks['assignment_marks'],
            'lab_marks': marks['lab_marks'],
            'attendance_marks': marks['attendance_marks'],
            'total_marks': obtained_total,     # Added calculation saving
            'percentage': percentage,           # Added calculation saving
            'grade': grade,                     # Added calculation saving
            'is_passed': is_passed,             # Added calculation saving
        }
    )
    
    return subject_result


def update_comprehensive_result(student, semester):
    """Update ComprehensiveResult for a student (one row per student)"""
    from decimal import Decimal
    
    subject_results = StudentSubjectResult.objects.filter(
        student=student,
        semester=semester
    )
    
    if not subject_results.exists():
        print(f"No subject results for {student.first_name}")
        return None
    
    # Build subject marks dictionary
    subject_marks = {}
    total_marks = Decimal('0.00')
    passed = 0
    failed = 0
    
    for result in subject_results:
        subject_marks[result.subject.code] = {
            'marks': float(result.total_marks),
            'grade': result.grade,
            'percentage': float(result.percentage)
        }
        total_marks += result.total_marks
        if result.is_passed:
            passed += 1
        else:
            failed += 1
    
    total_possible = Decimal(str(len(subject_results) * 100))
    percentage = (total_marks / total_possible) * 100 if total_possible > 0 else 0
    cgpa = percentage / 25
    
    comp_result, created = ComprehensiveResult.objects.update_or_create(
        student=student,
        semester=semester,
        defaults={
            'section': student.section,
            'batch': student.batch,
            'subject_marks': subject_marks,
            'total_marks': total_marks,
            'total_possible': total_possible,
            'percentage': percentage,
            'cgpa': cgpa,
            'passed_subjects': passed,
            'failed_subjects': failed,
        }
    )
    
    print(f"Updated comprehensive result for {student.first_name}: Total={total_marks}, CGPA={cgpa:.2f}")
    return comp_result

def comprehensive_result_view(request):
    """View comprehensive results with filters - Compatible with existing template"""
    
    # Get filter parameters
    batch_id = request.GET.get('batch')
    semester_id = request.GET.get('semester')
    section_id = request.GET.get('section')
    search_query = request.GET.get('search', '')
    
    # Get all filter options
    batches = Batch.objects.all().order_by('-start_session')
    semesters = Semester.objects.all().order_by('number')
    sections = Section.objects.all().order_by('name')
    disciplines = Discipline.objects.all().order_by('field')
    
    # Start with all comprehensive results
    comp_results = ComprehensiveResult.objects.all().select_related(
        'student',
        'student__user',
        'student__batch',
        'student__semester',
        'student__section',
        'semester',
        'section'
    )
    
    # Apply filters
    if batch_id:
        comp_results = comp_results.filter(student__batch_id=batch_id)
    if semester_id:
        comp_results = comp_results.filter(semester_id=semester_id)
    if section_id:
        comp_results = comp_results.filter(section_id=section_id)
    if search_query:
        comp_results = comp_results.filter(
            Q(student__first_name__icontains=search_query) |
            Q(student__last_name__icontains=search_query) |
            Q(student__student_id__icontains=search_query)
        )
    
    # Organize data by student and semester
    student_semester_data = []
    
    for result in comp_results:
        student = result.student
        semester = result.semester
        
        # Get subjects from JSON field
        subjects = []
        total_obtained_marks = 0
        total_max_marks = 0
        total_grade_points = 0
        
        for subject_code, data in result.subject_marks.items():
            obtained = data.get('marks', 0)
            grade = data.get('grade', 'F')
            percentage = data.get('percentage', 0)
            
            # Calculate grade point
            if grade == 'A+':
                grade_point = 4.0
            elif grade == 'A':
                grade_point = 4.0
            elif grade == 'B+':
                grade_point = 3.5
            elif grade == 'B':
                grade_point = 3.0
            elif grade == 'C+':
                grade_point = 2.5
            elif grade == 'C':
                grade_point = 2.0
            elif grade == 'D':
                grade_point = 1.5
            else:
                grade_point = 0.0
            
            subjects.append({
                'subject_code': subject_code,
                'subject_name': subject_code,
                'obtained_marks': obtained,
                'max_marks': 100,
                'percentage': percentage,
                'grade': grade,
                'grade_point': grade_point,
                'is_passed': grade != 'F',
            })
            
            total_obtained_marks += obtained
            total_max_marks += 100
            total_grade_points += grade_point
        
        # Calculate averages
        total_subjects = len(subjects)
        overall_percentage = (total_obtained_marks / total_max_marks * 100) if total_max_marks > 0 else 0
        gpa = total_grade_points / total_subjects if total_subjects > 0 else 0
        cgpa = overall_percentage / 25  # Simplified CGPA
        
        student_semester_data.append({
            'student': student,
            'semester': semester,
            'subjects': subjects,
            'total_obtained_marks': total_obtained_marks,
            'total_max_marks': total_max_marks,
            'overall_percentage': overall_percentage,
            'gpa': gpa,
            'cgpa': cgpa,
            'passed_subjects': sum(1 for s in subjects if s['is_passed']),
            'failed_subjects': sum(1 for s in subjects if not s['is_passed']),
            'total_subjects': total_subjects,
        })
    
    # Pagination
    paginator = Paginator(student_semester_data, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get selected filter names for display
    selected_batch_name = None
    selected_section_name = None
    selected_semester_name = None
    
    if batch_id:
        try:
            selected_batch_name = Batch.objects.get(id=batch_id).name
        except:
            pass
    if section_id:
        try:
            selected_section_name = Section.objects.get(id=section_id).name
        except:
            pass
    if semester_id:
        try:
            selected_semester_name = Semester.objects.get(id=semester_id).number
        except:
            pass
    
    context = {
        'page_obj': page_obj,
        'batches': batches,
        'semesters': semesters,
        'sections': sections,
        'disciplines': disciplines,
        'selected_batch': batch_id,
        'selected_semester': semester_id,
        'selected_section': section_id,
        'selected_batch_name': selected_batch_name,
        'selected_section_name': selected_section_name,
        'selected_semester_name': selected_semester_name,
        'search_query': search_query,
        'total_students': len(student_semester_data),
        'total_subjects': ComprehensiveResult.objects.count(),
    }
    
    return render(request, 'exam/comprehensive_result.html', context)

def update_comprehensive_result_for_student(student):
    """Update comprehensive result for a single student"""
    from decimal import Decimal
    
    subject_results = StudentSubjectResult.objects.filter(student=student)
    
    if not subject_results.exists():
        return None
    
    subject_marks = {}
    total_marks = Decimal('0.00')
    passed = 0
    failed = 0
    
    for result in subject_results:
        # Fallback values if fields are somehow empty
        obt_marks = result.total_marks if result.total_marks else Decimal('0.00')
        pct = result.percentage if result.percentage else Decimal('0.00')
        grade = result.grade if result.grade else 'F'
        
        subject_marks[result.subject.code] = {
            'marks': float(obt_marks),
            'grade': grade,
            'percentage': float(pct)
        }
        total_marks += obt_marks
        
        # Check pass status
        if grade != 'F':
            passed += 1
        else:
            failed += 1
    
    total_possible = len(subject_results) * 100
    percentage = (float(total_marks) / total_possible * 100) if total_possible > 0 else 0
    cgpa = percentage / 25
    
    comp_result, created = ComprehensiveResult.objects.update_or_create(
        student=student,
        semester=student.semester,
        defaults={
            'section': student.section,
            'batch': student.batch,
            'subject_marks': subject_marks,
            'total_marks': total_marks,
            'total_possible': Decimal(str(total_possible)),
            'percentage': Decimal(str(percentage)),
            'cgpa': Decimal(str(cgpa)),
            'passed_subjects': passed,
            'failed_subjects': failed,
        }
    )
    return comp_result
def delete_comprehensive_results(request):
    """Delete all comprehensive results"""
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, 'Access denied. Admin only.')
        return redirect('dashboard')
    
    count = ComprehensiveResult.objects.count()
    ComprehensiveResult.objects.all().delete()
    messages.success(request, f'✅ Deleted {count} comprehensive results successfully!')
    return redirect('exam_manag:comprehensive_results')

def fix_student_marks(request, student_id):
    """Fix comprehensive results for a specific student"""
    from decimal import Decimal
    
    student = get_object_or_404(Student, id=student_id)
    
    # Get all subject results for this student
    subject_results = StudentSubjectResult.objects.filter(student=student)
    
    if not subject_results.exists():
        return HttpResponse(f"No subject results found for {student.first_name}")
    
    subject_marks = {}
    total_marks = Decimal('0.00')
    passed = 0
    failed = 0
    
    output = []
    output.append(f"<h2>Fixing marks for {student.first_name} {student.last_name}</h2>")
    
    for result in subject_results:
        marks = result.total_marks
        subject_marks[result.subject.code] = {
            'marks': float(marks),
            'grade': result.grade,
            'percentage': float(result.percentage)
        }
        total_marks += marks
        output.append(f"<p>{result.subject.code}: {marks} marks (Grade: {result.grade})</p>")
        
        if result.is_passed:
            passed += 1
        else:
            failed += 1
    
    total_possible = len(subject_results) * 100
    percentage = (float(total_marks) / total_possible * 100) if total_possible > 0 else 0
    cgpa = percentage / 25
    
    output.append(f"<p><strong>Total: {total_marks}/{total_possible} = {percentage:.1f}%</strong></p>")
    output.append(f"<p><strong>CGPA: {cgpa:.2f}</strong></p>")
    
    # Update or create comprehensive result
    comp_result, created = ComprehensiveResult.objects.update_or_create(
        student=student,
        semester=student.semester,
        defaults={
            'section': student.section,
            'batch': student.batch,
            'subject_marks': subject_marks,
            'total_marks': total_marks,
            'total_possible': Decimal(str(total_possible)),
            'percentage': Decimal(str(percentage)),
            'cgpa': Decimal(str(cgpa)),
            'passed_subjects': passed,
            'failed_subjects': failed,
        }
    )
    
    output.append(f"<p style='color:green;'>✅ Comprehensive result {'created' if created else 'updated'} successfully!</p>")
    output.append(f"<p><a href='/exam_manag/comprehensive-results/'>Go back to Comprehensive Results</a></p>")
    
    return HttpResponse("<br>".join(output))


# ==================== STUDENT VIEWS ====================

@login_required
def student_my_marks(request):
    """Student view to see their marks"""
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        messages.error(request, 'Student profile not found!')
        return redirect('student_dashboard')
    
    subject_results = StudentSubjectResult.objects.filter(student=student).select_related('subject')
    
    subjects_data = []
    total_marks = 0
    passed_count = 0
    failed_count = 0
    
    for result in subject_results:
        subjects_data.append({
            'id': result.subject.id,  # ADD THIS LINE - subject_id
            'code': result.subject.code,
            'name': result.subject.name,
            'mid_term_marks': float(result.mid_term_marks),
            'final_marks': float(result.final_marks),
            'quiz_marks': float(result.quiz_marks),
            'assignment_marks': float(result.assignment_marks),
            'lab_marks': float(result.lab_marks),
            'attendance_marks': float(result.attendance_marks),
            'total_marks': float(result.total_marks),
            'percentage': float(result.percentage),
            'grade': result.grade,
            'is_passed': result.is_passed,
        })
        total_marks += float(result.total_marks)
        if result.is_passed:
            passed_count += 1
        else:
            failed_count += 1
    
    overall_percentage = (total_marks / (len(subject_results) * 100) * 100) if subject_results else 0
    cgpa = overall_percentage / 25
    
    context = {
        'student': student,
        'subjects': subjects_data,
        'total_marks': total_marks,
        'total_max': len(subject_results) * 100,
        'overall_percentage': overall_percentage,
        'subjects_passed': passed_count,
        'subjects_failed': failed_count,
        'cgpa': cgpa,
    }
    return render(request, 'exam/student_my_marks.html', context)

# ==================== TRANSCRIPT FUNCTIONS ====================

@login_required
def all_transcripts_list(request):
    """Admin view - List all transcripts"""
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, 'Access denied. Admin only.')
        return redirect('dashboard')
    
    transcripts = Transcript.objects.all().select_related('student').order_by('-issue_date')
    
    paginator = Paginator(transcripts, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {'transcripts': page_obj, 'page_obj': page_obj}
    return render(request, 'exam/all_transcripts_list.html', context)


@login_required
def view_transcript(request, transcript_id):
    """View a specific transcript"""
    transcript = get_object_or_404(Transcript, id=transcript_id)
    
    comp_results = ComprehensiveResult.objects.filter(student=transcript.student)
    
    results_by_semester = {}
    for result in comp_results:
        semester_name = f"Semester {result.semester.number}" if result.semester else "Unknown"
        if semester_name not in results_by_semester:
            results_by_semester[semester_name] = []
        
        for subject_code, data in result.subject_marks.items():
            results_by_semester[semester_name].append({
                'subject_code': subject_code,
                'subject_name': subject_code,
                'credit_hours': 3,
                'grade': data.get('grade', 'F'),
                'total_marks': 100,
                'obtained_marks': data.get('marks', 0),
                'percentage': data.get('percentage', 0),
            })
    
    context = {
        'transcript': transcript,
        'student': transcript.student,
        'results_by_semester': results_by_semester,
    }
    return render(request, 'exam/view_transcript.html', context)


@login_required
def generate_transcript(request, student_id):
    """Generate transcript for a student"""
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, 'Access denied. Admin only.')
        return redirect('dashboard')
    
    student = get_object_or_404(Student, id=student_id)
    
    comp_results = ComprehensiveResult.objects.filter(student=student)
    
    if not comp_results.exists():
        messages.error(request, f'No results found for student {student.student_id}.')
        return redirect('all_transcripts_list')
    
    total_marks = 0
    total_possible = 0
    for result in comp_results:
        total_marks += float(result.total_marks)
        total_possible += float(result.total_possible)
    
    cumulative_gpa = (total_marks / total_possible * 100 / 25) if total_possible > 0 else 0
    
    transcript = Transcript.objects.create(
        student=student,
        transcript_number=f"TR-{student.student_id}-{timezone.now().strftime('%Y%m%d%H%M%S')}",
        transcript_type='official',
        issue_date=timezone.now().date(),
        cumulative_gpa=round(Decimal(str(cumulative_gpa)), 2),
        total_credits_attempted=comp_results.count() * 3,
        total_credits_earned=0,
        total_quality_points=Decimal('0.00'),
        is_issued=True,
        issued_by=request.user,
    )
    
    messages.success(request, f'Transcript generated successfully!')
    return redirect('exam_manag:view_transcript', transcript_id=transcript.id)


@login_required
def delete_transcript(request, transcript_id):
    """Delete a transcript"""
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, 'Access denied. Admin only.')
        return redirect('dashboard')
    
    transcript = get_object_or_404(Transcript, id=transcript_id)
    
    if request.method == 'POST':
        transcript.delete()
        messages.success(request, 'Transcript deleted successfully!')
        return redirect('all_transcripts_list')
    
    context = {'transcript': transcript}
    return render(request, 'exam/delete_transcript_confirmation.html', context)


@login_required
def print_transcript(request, transcript_id):
    """Print-friendly version of transcript"""
    transcript = get_object_or_404(Transcript, id=transcript_id)
    return render(request, 'exam/print_transcript.html', {'transcript': transcript})

def student_subject_marks(request):
    """Show all students with their total marks in each subject - Direct from ExamResult"""
    try:
        teacher = Teacher.objects.get(user=request.user)
        
        selected_subject_id = request.GET.get('subject_id')
        selected_section_id = request.GET.get('section_id')
        search_query = request.GET.get('search', '')
        
        # Get all sections
        sections = Section.objects.all()
        
        # Get subjects assigned to this teacher
        assigned_subjects = Subject.objects.filter(
            assigned_teachers__teacher=teacher,
            assigned_teachers__is_active=True
        ).distinct()
        
        if selected_subject_id:
            assigned_subjects = assigned_subjects.filter(id=selected_subject_id)
        
        # Get students with filters
        students = Student.objects.all()
        if selected_section_id:
            students = students.filter(section_id=selected_section_id)
        if search_query:
            students = students.filter(
                Q(student_id__icontains=search_query) |
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query)
            )
        
        # Prepare student data grouped by section
        students_by_section = {}
        
        for student in students:
            section_name = student.section.name if student.section else 'No Section'
            
            for subject in assigned_subjects:
                # Get all exams for this subject and student's section
                exams = Exam.objects.filter(
                    subject=subject,
                    section=student.section
                )
                
                # Initialize component marks
                mid_term_marks = None
                final_marks = None
                quiz_marks = None
                assignment_marks = None
                lab_marks = None
                attendance_marks = None
                
                mid_term_max = 0
                final_max = 0
                quiz_max = 0
                assignment_max = 0
                lab_max = 0
                attendance_max = 0
                
                total_marks = 0
                total_max = 0
                
                # Get marks from ExamResult for each exam
                for exam in exams:
                    try:
                        result = ExamResult.objects.get(exam=exam, student=student)
                        marks = float(result.marks_obtained) if result.marks_obtained else 0
                        max_marks = float(exam.total_marks)
                        
                        if exam.exam_type == 'mid_term':
                            mid_term_marks = marks
                            mid_term_max = max_marks
                        elif exam.exam_type == 'final':
                            final_marks = marks
                            final_max = max_marks
                        elif exam.exam_type == 'quiz':
                            quiz_marks = marks
                            quiz_max = max_marks
                        elif exam.exam_type == 'assignment':
                            assignment_marks = marks
                            assignment_max = max_marks
                        elif exam.exam_type == 'lab':
                            lab_marks = marks
                            lab_max = max_marks
                        elif exam.exam_type == 'attendance':
                            attendance_marks = marks
                            attendance_max = max_marks
                        
                        total_marks += marks
                        total_max += max_marks
                        
                    except ExamResult.DoesNotExist:
                        pass
                
                # Only show if there's at least one exam result
                if total_max > 0:
                    percentage = (total_marks / total_max * 100) if total_max > 0 else 0
                    is_passed = percentage >= 50
                    
                    # Calculate grade
                    if percentage >= 90:
                        grade = 'A+'
                    elif percentage >= 80:
                        grade = 'A'
                    elif percentage >= 70:
                        grade = 'B+'
                    elif percentage >= 60:
                        grade = 'B'
                    elif percentage >= 50:
                        grade = 'C+'
                    elif percentage >= 40:
                        grade = 'C'
                    elif percentage >= 33:
                        grade = 'D'
                    else:
                        grade = 'F'
                    
                    student_data = {
                        'id': student.id,
                        'student_id': student.student_id,
                        'name': f"{student.first_name} {student.last_name}",
                        'email': student.email,
                        'subject_code': subject.code,
                        'subject_name': subject.name,
                        'mid_term': {'uploaded': mid_term_marks is not None, 'marks': mid_term_marks or 0, 'max': mid_term_max},
                        'final': {'uploaded': final_marks is not None, 'marks': final_marks or 0, 'max': final_max},
                        'quiz': {'uploaded': quiz_marks is not None, 'marks': quiz_marks or 0, 'max': quiz_max},
                        'assignment': {'uploaded': assignment_marks is not None, 'marks': assignment_marks or 0, 'max': assignment_max},
                        'lab': {'uploaded': lab_marks is not None, 'marks': lab_marks or 0, 'max': lab_max},
                        'attendance': {'uploaded': attendance_marks is not None, 'marks': attendance_marks or 0, 'max': attendance_max},
                        'total_marks': round(total_marks, 1),
                        'percentage': round(percentage, 1),
                        'grade': grade,
                        'is_passed': is_passed,
                    }
                    
                    if section_name not in students_by_section:
                        students_by_section[section_name] = []
                    
                    students_by_section[section_name].append(student_data)
        
        context = {
            'students_by_section': students_by_section,
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

# ==================== HELPER FUNCTIONS ====================
# ==================== STUDENT SUBJECT MARKS DETAIL ====================

@login_required
def student_subject_marks_detail(request, subject_id):
    """Student view - Detailed marks for a specific subject"""
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        messages.error(request, 'Student profile not found!')
        return redirect('student_dashboard')
    
    subject = get_object_or_404(Subject, id=subject_id)
    
    # Get the student's result for this subject
    try:
        subject_result = StudentSubjectResult.objects.get(
            student=student,
            subject=subject
        )
    except StudentSubjectResult.DoesNotExist:
        messages.warning(request, f'No results found for {subject.code} - {subject.name}')
        return redirect('student_my_marks')
    
    # Get all exams for this subject (to show individual component marks)
    exams = Exam.objects.filter(
        subject=subject,
        section=student.section,
        is_published=True
    ).order_by('exam_type')
    
    # Prepare exam results
    exam_results = []
    for exam in exams:
        try:
            exam_result = ExamResult.objects.get(exam=exam, student=student)
            exam_results.append({
                'exam_type': exam.get_exam_type_display(),
                'exam_type_key': exam.exam_type,
                'marks_obtained': float(exam_result.marks_obtained) if exam_result.marks_obtained else 0,
                'total_marks': float(exam.total_marks),
                'percentage': float(exam_result.percentage),
                'grade': exam_result.grade,
                'is_absent': exam_result.is_absent,
                'remarks': exam_result.remarks,
            })
        except ExamResult.DoesNotExist:
            exam_results.append({
                'exam_type': exam.get_exam_type_display(),
                'exam_type_key': exam.exam_type,
                'marks_obtained': 0,
                'total_marks': float(exam.total_marks),
                'percentage': 0,
                'grade': 'F',
                'is_absent': False,
                'remarks': '',
            })
    
    # Get component wise marks from StudentSubjectResult
    component_marks = {
        'mid_term': float(subject_result.mid_term_marks),
        'final': float(subject_result.final_marks),
        'quiz': float(subject_result.quiz_marks),
        'assignment': float(subject_result.assignment_marks),
        'lab': float(subject_result.lab_marks),
        'attendance': float(subject_result.attendance_marks),
    }
    
    # Calculate grade information
    percentage = float(subject_result.percentage)
    if percentage >= 90:
        grade = 'A+'
        grade_point = 4.00
        remarks = 'Outstanding'
    elif percentage >= 80:
        grade = 'A'
        grade_point = 4.00
        remarks = 'Excellent'
    elif percentage >= 70:
        grade = 'B+'
        grade_point = 3.50
        remarks = 'Very Good'
    elif percentage >= 60:
        grade = 'B'
        grade_point = 3.00
        remarks = 'Good'
    elif percentage >= 50:
        grade = 'C+'
        grade_point = 2.50
        remarks = 'Satisfactory'
    elif percentage >= 40:
        grade = 'C'
        grade_point = 2.00
        remarks = 'Fair'
    elif percentage >= 33:
        grade = 'D'
        grade_point = 1.50
        remarks = 'Pass'
    else:
        grade = 'F'
        grade_point = 0.00
        remarks = 'Fail'
    
    context = {
        'student': student,
        'subject': subject,
        'subject_result': subject_result,
        'component_marks': component_marks,
        'exam_results': exam_results,
        'total_marks': float(subject_result.total_marks),
        'percentage': percentage,
        'grade': grade,
        'grade_point': grade_point,
        'remarks': remarks,
        'is_passed': subject_result.is_passed,
    }
    
    return render(request, 'exam/student_subject_marks_detail.html', context)


# ==================== STUDENT MARKS API ====================

@login_required
def student_marks_api(request, subject_id):
    """API endpoint for student marks data"""
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        return JsonResponse({'error': 'Student not found'}, status=404)
    
    subject = get_object_or_404(Subject, id=subject_id)
    
    try:
        subject_result = StudentSubjectResult.objects.get(
            student=student,
            subject=subject
        )
    except StudentSubjectResult.DoesNotExist:
        return JsonResponse({'error': 'No results found'}, status=404)
    
    return JsonResponse({
        'success': True,
        'subject_code': subject.code,
        'subject_name': subject.name,
        'total_marks': float(subject_result.total_marks),
        'percentage': float(subject_result.percentage),
        'grade': subject_result.grade,
        'grade_point': float(subject_result.grade_point),
        'is_passed': subject_result.is_passed,
        'mid_term': float(subject_result.mid_term_marks),
        'final': float(subject_result.final_marks),
        'quiz': float(subject_result.quiz_marks),
        'assignment': float(subject_result.assignment_marks),
        'lab': float(subject_result.lab_marks),
        'attendance': float(subject_result.attendance_marks),
    })


# ==================== STUDENT TRANSCRIPT REQUEST ====================

@login_required
def student_transcript_request(request):
    """Student request for transcript"""
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        messages.error(request, 'Student profile not found!')
        return redirect('student_dashboard')
    
    if request.method == 'POST':
        request_type = request.POST.get('request_type')
        purpose = request.POST.get('purpose')
        number_of_copies = int(request.POST.get('number_of_copies', 1))
        delivery_method = request.POST.get('delivery_method')
        delivery_address = request.POST.get('delivery_address', '')
        
        transcript_request = TranscriptRequest.objects.create(
            student=student,
            request_type=request_type,
            purpose=purpose,
            number_of_copies=number_of_copies,
            delivery_method=delivery_method,
            delivery_address=delivery_address,
            status='pending'
        )
        
        messages.success(request, 'Transcript request submitted successfully!')
    
    context = {'student': student}
    return render(request, 'exam/student_transcript_request.html', context)


@login_required
def student_transcript_requests_list(request):
    """Student view all their transcript requests"""
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        messages.error(request, 'Student profile not found!')
        return redirect('student_dashboard')
    
    transcript_requests = TranscriptRequest.objects.filter(student=student).order_by('-request_date')
    
    context = {
        'student': student,
        'transcript_requests': transcript_requests,
    }
    return render(request, 'exam/student_transcript_requests.html', context)


@login_required
def student_view_transcript(request, request_id):
    """Student view approved transcript"""
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        messages.error(request, 'Student profile not found!')
        return redirect('student_dashboard')
    
    transcript_request = get_object_or_404(TranscriptRequest, id=request_id, student=student)
    
    if transcript_request.status not in ['approved', 'issued']:
        messages.error(request, 'Transcript not available yet.')
        return redirect('student_transcript_requests_list')
    
    # Get comprehensive results
    comp_results = ComprehensiveResult.objects.filter(student=student)
    
    results_by_semester = {}
    for result in comp_results:
        semester_name = f"Semester {result.semester.number}" if result.semester else "Unknown"
        if semester_name not in results_by_semester:
            results_by_semester[semester_name] = []
        
        for subject_code, data in result.subject_marks.items():
            results_by_semester[semester_name].append({
                'subject_code': subject_code,
                'subject_name': subject_code,
                'credit_hours': 3,
                'grade': data.get('grade', 'F'),
                'total_marks': 100,
                'obtained_marks': data.get('marks', 0),
                'percentage': data.get('percentage', 0),
            })
    
    context = {
        'student': student,
        'transcript_request': transcript_request,
        'results_by_semester': results_by_semester,
    }
    return render(request, 'exam/student_view_transcript.html', context)


# ==================== ADMIN TRANSCRIPT MANAGEMENT ====================

@login_required
def admin_transcript_requests(request):
    """Admin view all transcript requests"""
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, 'Access denied. Admin only.')
        return redirect('dashboard')
    
    status_filter = request.GET.get('status', '')
    transcript_requests = TranscriptRequest.objects.all().select_related('student').order_by('-request_date')
    
    if status_filter:
        transcript_requests = transcript_requests.filter(status=status_filter)
    
    context = {
        'transcript_requests': transcript_requests,
        'status_filter': status_filter,
        'status_choices': TranscriptRequest.STATUS_CHOICES,
    }
    return render(request, 'exam/admin_transcript_requests.html', context)


@login_required
def approve_transcript_request(request, request_id):
    """Admin approve transcript request"""
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, 'Access denied. Admin only.')
        return redirect('dashboard')
    
    transcript_request = get_object_or_404(TranscriptRequest, id=request_id)
    transcript_request.status = 'approved'
    transcript_request.processed_date = timezone.now()
    transcript_request.save()
    
    messages.success(request, f'Transcript request approved!')
    return redirect('admin_transcript_requests')


@login_required
def reject_transcript_request(request, request_id):
    """Admin reject transcript request"""
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, 'Access denied. Admin only.')
        return redirect('dashboard')
    
    transcript_request = get_object_or_404(TranscriptRequest, id=request_id)
    reason = request.POST.get('reason', 'No reason provided')
    
    transcript_request.status = 'rejected'
    transcript_request.processed_date = timezone.now()
    transcript_request.remarks = reason
    transcript_request.save()
    
    messages.success(request, f'Transcript request rejected.')
    return redirect('admin_transcript_requests')


@login_required
def issue_transcript_request(request, request_id):
    """Admin issue transcript"""
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, 'Access denied. Admin only.')
        return redirect('dashboard')
    
    transcript_request = get_object_or_404(TranscriptRequest, id=request_id)
    
    transcript_request.status = 'issued'
    transcript_request.issued_date = timezone.now()
    transcript_request.save()
    
    # Generate transcript record
    transcript = Transcript.objects.create(
        student=transcript_request.student,
        transcript_number=f"TR-{transcript_request.student.student_id}-{timezone.now().strftime('%Y%m%d%H%M%S')}",
        transcript_type=transcript_request.request_type,
        issue_date=timezone.now().date(),
        cumulative_gpa=Decimal('0.00'),
        is_issued=True,
    )
    
    messages.success(request, f'Transcript issued successfully!')
    return redirect('admin_transcript_requests')


@login_required
def generate_transcript_pdf(request, request_id):
    """Generate PDF of transcript"""
    from django.http import HttpResponse
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    
    transcript_request = get_object_or_404(TranscriptRequest, id=request_id)
    student = transcript_request.student
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="transcript_{student.student_id}.pdf"'
    
    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter
    
    p.setFont("Helvetica-Bold", 20)
    p.drawString(1*72, height - 1*72, "ACADEMIC TRANSCRIPT")
    
    p.setFont("Helvetica", 10)
    p.drawString(1*72, height - 1.5*72, f"Student Name: {student.first_name} {student.last_name}")
    p.drawString(1*72, height - 1.7*72, f"Student ID: {student.student_id}")
    
    p.showPage()
    p.save()
    
    return response


@login_required
def admin_generate_transcript_form(request):
    """Admin - Form to select student for transcript generation"""
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, 'Access denied. Admin only.')
        return redirect('dashboard')
    
    students = Student.objects.all().select_related('batch', 'semester', 'section').order_by('first_name')
    
    search_query = request.GET.get('search', '')
    if search_query:
        students = students.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(student_id__icontains=search_query)
        )
    
    context = {
        'students': students,
        'search_query': search_query,
        'total_count': students.count(),
    }
    return render(request, 'exam/admin_generate_transcript.html', context)


@login_required
def generate_all_transcripts(request):
    """Admin - Generate transcripts for all students"""
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, 'Access denied. Admin only.')
        return redirect('dashboard')
    
    students = Student.objects.all()
    generated_count = 0
    failed_count = 0
    
    for student in students:
        try:
            comp_results = ComprehensiveResult.objects.filter(student=student)
            if comp_results.exists():
                existing = Transcript.objects.filter(student=student, is_issued=True).first()
                if not existing:
                    total_marks = 0
                    total_possible = 0
                    for result in comp_results:
                        total_marks += float(result.total_marks)
                        total_possible += float(result.total_possible)
                    
                    cumulative_gpa = (total_marks / total_possible * 100 / 25) if total_possible > 0 else 0
                    
                    Transcript.objects.create(
                        student=student,
                        transcript_number=f"TR-{student.student_id}-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                        transcript_type='official',
                        issue_date=timezone.now().date(),
                        cumulative_gpa=round(Decimal(str(cumulative_gpa)), 2),
                        total_credits_attempted=comp_results.count() * 3,
                        total_credits_earned=0,
                        total_quality_points=Decimal('0.00'),
                        is_issued=True,
                        issued_by=request.user,
                    )
                    generated_count += 1
        except Exception as e:
            failed_count += 1
            print(f"Error generating transcript for {student.student_id}: {e}")
    
    messages.success(request, f'Generated {generated_count} transcripts. Failed: {failed_count}')
    return redirect('all_transcripts_list')


# ==================== DEBUG VIEW ====================

def debug_exam(request, exam_id):
    """Debug view for exam"""
    exam = get_object_or_404(Exam, id=exam_id)
    
    response_lines = []
    response_lines.append(f"<h1>Debug Exam {exam_id}</h1>")
    response_lines.append(f"<p>Exam: {exam}</p>")
    response_lines.append(f"<p>Subject: {exam.subject}</p>")
    response_lines.append(f"<p>Section: {exam.section}</p>")
    response_lines.append(f"<p>Exam Type: {exam.get_exam_type_display()}</p>")
    response_lines.append(f"<p>Total Marks: {exam.total_marks}</p>")
    response_lines.append(f"<p>Published: {exam.is_published}</p>")
    
    students = Student.objects.filter(section=exam.section)
    response_lines.append(f"<p>Students found: {students.count()}</p>")
    
    for student in students:
        response_lines.append(f"<p>- {student.student_id}: {student.first_name} {student.last_name}</p>")
    
    return HttpResponse("\n".join(response_lines))
def get_current_academic_year():
    current_year = datetime.now().year
    return f"{current_year}-{current_year + 1}"