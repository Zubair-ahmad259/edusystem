# attendance/views.py
from multiprocessing import context
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Count, Q  # Add this import
from datetime import date, datetime, timedelta
from collections import defaultdict  # Add this import

import json

from .models import Attendance, DailyAttendanceSummary, MonthlyAttendanceReport
from student.models import Student
from teachers.models import Teacher
from subject.models import Subject
from Academic.models import Batch, Semester, Section, Discipline

def attendance_dashboard(request):
    """Attendance Dashboard for everyone"""
    today = date.today()
    
    # Get today's attendance count
    today_attendance = Attendance.objects.filter(date=today).count()
    
    # Get total attendance count
    total_attendance = Attendance.objects.count()
    
    # Get recent attendance (last 10 records)
    recent_attendance = Attendance.objects.order_by('-date', '-created_at')[:10]
    
    # Get top batches by attendance
    batch_stats = Attendance.objects.values('batch__name').annotate(
        total=Count('id'),
        present=Count('id', filter=Q(status='P'))
    ).order_by('-total')[:5]
    
    context = {
        'today_attendance': today_attendance,
        'total_attendance': total_attendance,
        'recent_attendance': recent_attendance,
        'batch_stats': batch_stats,
        'today': today,
    }
    
    return render(request, 'attendance/dashboard.html', context)

def attendance_list(request):
    """List all attendance records"""
    attendances = Attendance.objects.all().order_by('-date', '-created_at')
    
    # Filters
    batch_id = request.GET.get('batch')
    subject_id = request.GET.get('subject')
    status = request.GET.get('status')
    date_filter = request.GET.get('date')
    
    if batch_id:
        attendances = attendances.filter(batch_id=batch_id)
    if subject_id:
        attendances = attendances.filter(subject_id=subject_id)
    if status:
        attendances = attendances.filter(status=status)
    if date_filter:
        attendances = attendances.filter(date=date_filter)
    
    # Get filter options
    batches = Batch.objects.all()
    subjects = Subject.objects.all()
    
    context = {
        'attendances': attendances,
        'batches': batches,
        'subjects': subjects,
    }
    
    return render(request, 'attendance/attendance_list.html', context)

def student_attendance(request, student_id):
    """View attendance for a specific student"""
    student = get_object_or_404(Student, id=student_id)
    
    # Get all attendance for this student
    attendances = Attendance.objects.filter(student=student).order_by('-date', '-created_at')
    
    # Calculate statistics
    total_days = attendances.count()
    present_days = attendances.filter(status='P').count()
    absent_days = attendances.filter(status='A').count()
    
    if total_days > 0:
        attendance_percentage = (present_days / total_days) * 100
    else:
        attendance_percentage = 0
    
    context = {
        'student': student,
        'attendances': attendances,
        'total_days': total_days,
        'present_days': present_days,
        'absent_days': absent_days,
        'attendance_percentage': round(attendance_percentage, 2),
    }
    
    return render(request, 'attendance/student_attendance.html', context)

def subject_attendance(request, subject_id):
    """View attendance for a specific subject"""
    subject = get_object_or_404(Subject, id=subject_id)
    
    # Get all attendance for this subject
    attendances = Attendance.objects.filter(subject=subject).order_by('-date', '-created_at')
    
    # Calculate statistics
    total_records = attendances.count()
    present_records = attendances.filter(status='P').count()
    absent_records = attendances.filter(status='A').count()
    
    if total_records > 0:
        attendance_percentage = (present_records / total_records) * 100
    else:
        attendance_percentage = 0
    
    context = {
        'subject': subject,
        'attendances': attendances,
        'total_records': total_records,
        'present_records': present_records,
        'absent_records': absent_records,
        'attendance_percentage': round(attendance_percentage, 2),
    }
    
    return render(request, 'attendance/subject_attendance.html', context)

def mark_attendance(request):
    """Mark attendance (simple form)"""
    if request.method == 'POST':
        try:
            student_id = request.POST.get('student_id')
            subject_id = request.POST.get('subject_id')
            status = request.POST.get('status', 'P')
            attendance_date = request.POST.get('date', date.today())
            
            student = Student.objects.get(id=student_id)
            subject = Subject.objects.get(id=subject_id)
            
            # Check if attendance already exists for this student+subject+date
            existing = Attendance.objects.filter(
                student=student,
                subject=subject,
                date=attendance_date
            ).exists()
            
            if existing:
                messages.warning(request, f"Attendance already marked for {student} on {attendance_date}")
            else:
                # Create attendance record
                attendance = Attendance(
                    student=student,
                    subject=subject,
                    date=attendance_date,
                    status=status,
                    batch=student.batch,
                    semester=student.semester,
                    section=student.section,
                    discipline=student.discipline,
                )
                attendance.save()
                
                messages.success(request, f"Attendance marked successfully for {student}")
            
            return redirect('attendance_list')
            
        except Student.DoesNotExist:
            messages.error(request, "Student not found")
        except Subject.DoesNotExist:
            messages.error(request, "Subject not found")
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
    
    # GET request - show form
    students = Student.objects.all()
    subjects = Subject.objects.all()
    
    context = {
        'students': students,
        'subjects': subjects,
        'today': date.today(),
    }
    
    return render(request, 'attendance/mark_attendance.html', context)

def bulk_attendance(request):
    """Mark attendance for multiple students at once"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            subject_id = data.get('subject_id')
            date_str = data.get('date', str(date.today()))
            attendance_data = data.get('attendance', {})
            
            subject = Subject.objects.get(id=subject_id)
            attendance_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            success_count = 0
            error_count = 0
            
            for student_id, status in attendance_data.items():
                try:
                    student = Student.objects.get(id=student_id)
                    
                    # Check if attendance already exists
                    existing = Attendance.objects.filter(
                        student=student,
                        subject=subject,
                        date=attendance_date
                    ).exists()
                    
                    if not existing:
                        attendance = Attendance(
                            student=student,
                            subject=subject,
                            date=attendance_date,
                            status=status,
                            batch=student.batch,
                            semester=student.semester,
                            section=student.section,
                            discipline=student.discipline,
                        )
                        attendance.save()
                        success_count += 1
                    else:
                        error_count += 1
                        
                except Student.DoesNotExist:
                    error_count += 1
                except Exception as e:
                    error_count += 1
            
            return JsonResponse({
                'success': True,
                'message': f'Attendance marked for {success_count} students. {error_count} errors.',
                'success_count': success_count,
                'error_count': error_count
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
    
    # GET request - show bulk attendance form
    batches = Batch.objects.all()
    subjects = Subject.objects.all()
    
    context = {
        'batches': batches,
        'subjects': subjects,
        'today': date.today(),
    }
    
    return render(request, 'attendance/bulk_attendance.html', context)

def daily_summary(request):
    """View daily attendance summaries"""
    summaries = DailyAttendanceSummary.objects.all().order_by('-date')
    
    # Filter by date if provided
    date_filter = request.GET.get('date')
    if date_filter:
        summaries = summaries.filter(date=date_filter)
    
    context = {
        'summaries': summaries,
    }
    
    return render(request, 'attendance/daily_summary.html', context)

def monthly_reports(request):
    """View monthly attendance reports"""
    reports = MonthlyAttendanceReport.objects.all().order_by('-year', '-month')
    
    # Filter by month/year if provided
    month = request.GET.get('month')
    year = request.GET.get('year')
    
    if month:
        reports = reports.filter(month=month)
    if year:
        reports = reports.filter(year=year)
    
    context = {
        'reports': reports,
    }
    
    return render(request, 'attendance/monthly_summary.html', context)

def attendance_statistics(request):
    """Attendance statistics and analytics"""
    # Overall statistics
    total_attendance = Attendance.objects.count()
    present_count = Attendance.objects.filter(status='P').count()
    absent_count = Attendance.objects.filter(status='A').count()
    
    if total_attendance > 0:
        overall_percentage = (present_count / total_attendance) * 100
    else:
        overall_percentage = 0
    
    # Batch-wise statistics
    batch_stats = []
    batches = Batch.objects.all()
    
    for batch in batches:
        batch_attendance = Attendance.objects.filter(batch=batch)
        batch_total = batch_attendance.count()
        batch_present = batch_attendance.filter(status='P').count()
        
        if batch_total > 0:
            batch_percentage = (batch_present / batch_total) * 100
        else:
            batch_percentage = 0
        
        batch_stats.append({
            'batch': batch,
            'total': batch_total,
            'present': batch_present,
            'percentage': round(batch_percentage, 2)
        })
    
    # Subject-wise statistics
    subject_stats = []
    subjects = Subject.objects.all()
    
    for subject in subjects:
        subject_attendance = Attendance.objects.filter(subject=subject)
        subject_total = subject_attendance.count()
        subject_present = subject_attendance.filter(status='P').count()
        
        if subject_total > 0:
            subject_percentage = (subject_present / subject_total) * 100
        else:
            subject_percentage = 0
        
        subject_stats.append({
            'subject': subject,
            'total': subject_total,
            'present': subject_present,
            'percentage': round(subject_percentage, 2)
        })
    
    context = {
        'total_attendance': total_attendance,
        'present_count': present_count,
        'absent_count': absent_count,
        'overall_percentage': round(overall_percentage, 2),
        'batch_stats': batch_stats,
        'subject_stats': subject_stats,
    }
    
    return render(request, 'attendance/attendance_statistics.html', context)

def get_students_by_batch(request):
    """Get students for a specific batch (AJAX)"""
    batch_id = request.GET.get('batch_id')
    
    if batch_id:
        students = Student.objects.filter(batch_id=batch_id).values('id', 'student_id', 'first_name', 'last_name')
        students_list = list(students)
        return JsonResponse({'students': students_list})
    
    return JsonResponse({'students': []})

def attendance_api(request):
    """Simple API to get attendance data"""
    attendances = Attendance.objects.all().order_by('-date')[:50]
    
    data = []
    for att in attendances:
        data.append({
            'id': att.id,
            'student_id': att.student.student_id,
            'student_name': f"{att.student.first_name} {att.student.last_name}",
            'subject_code': att.subject.code,
            'subject_name': att.subject.name,
            'date': att.date.strftime('%Y-%m-%d'),
            'status': att.status,
            'status_display': att.get_status_display(),
            'batch': att.batch.name,
            'section': att.section.name,
        })
    
    return JsonResponse({'attendance': data})


def export_attendance(request):

    """Export attendance data as CSV"""
    import csv
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="attendance_export.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Student ID', 'Student Name', 'Subject Code', 'Subject Name', 
                     'Date', 'Status', 'Batch', 'Section', 'Semester'])
    
    attendances = Attendance.objects.all().order_by('-date')
    
    for att in attendances:
        writer.writerow([
            att.student.student_id,
            f"{att.student.first_name} {att.student.last_name}",
            att.subject.code,
            att.subject.name,
            att.date.strftime('%Y-%m-%d'),
            att.get_status_display(),
            att.batch.name,
            att.section.name,
            att.semester.number
        ])
    
    return response

def subject_attendance(request, subject_id):
    """View attendance for a specific subject with filtering"""
    subject = get_object_or_404(Subject, id=subject_id)
    
    # Get all attendance for this subject
    attendances = Attendance.objects.filter(subject=subject).order_by('-date', '-created_at')
    
    # Apply filters
    discipline_id = request.GET.get('discipline')
    batch_id = request.GET.get('batch')
    semester_id = request.GET.get('semester')
    section_id = request.GET.get('section')
    status = request.GET.get('status')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if discipline_id:
        attendances = attendances.filter(discipline_id=discipline_id)
    if batch_id:
        attendances = attendances.filter(batch_id=batch_id)
    if semester_id:
        attendances = attendances.filter(semester_id=semester_id)
    if section_id:
        attendances = attendances.filter(section_id=section_id)
    if status:
        attendances = attendances.filter(status=status)
    if start_date:
        attendances = attendances.filter(date__gte=start_date)
    if end_date:
        attendances = attendances.filter(date__lte=end_date)
    
    # Calculate statistics
    total_records = attendances.count()
    present_records = attendances.filter(status='P').count()
    absent_records = attendances.filter(status='A').count()
    
    if total_records > 0:
        attendance_percentage = (present_records / total_records) * 100
    else:
        attendance_percentage = 0
    
    # Get batch distribution
    batch_distribution = attendances.values('batch__name').annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    # Calculate percentages for batch distribution
    for batch in batch_distribution:
        batch['percentage'] = (batch['count'] / total_records * 100) if total_records > 0 else 0
    
    # Get recent activity
    recent_activity = attendances.select_related('student').order_by('-date')[:5]
    
    # Get filter options
    from Academic.models import Discipline, Batch, Semester, Section
    
    context = {
        'subject': subject,
        'attendances': attendances,
        'total_records': total_records,
        'present_records': present_records,
        'absent_records': absent_records,
        'attendance_percentage': round(attendance_percentage, 2),
        'batch_distribution': batch_distribution,
        'recent_activity': recent_activity,
        'disciplines': Discipline.objects.all(),
        'batches': Batch.objects.all(),
        'semesters': Semester.objects.all(),
        'sections': Section.objects.all(),
    }
    
    return render(request, 'attendance/subject_attendance.html', context)
# Add these API views to attendance/views.py

def get_disciplines(request):
    """Get all disciplines (AJAX)"""
    disciplines = Discipline.objects.all()
    data = []
    for d in disciplines:
        data.append({
            'id': d.id,
            'text': f"{d.program} in {d.field}"
        })
    return JsonResponse(data, safe=False)

def get_batches_by_discipline(request):
    """Get batches by discipline (AJAX)"""
    discipline_id = request.GET.get('discipline_id')
    if discipline_id:
        batches = Batch.objects.filter(discipline_id=discipline_id)
        data = []
        for b in batches:
            data.append({
                'id': b.id,
                'text': b.name
            })
        return JsonResponse(data, safe=False)
    return JsonResponse([], safe=False)

def get_sections_by_batch(request):
    """Get sections by batch (AJAX)"""
    batch_id = request.GET.get('batch_id')
    if batch_id:
        sections = Section.objects.filter(batch_id=batch_id)
        data = []
        for s in sections:
            data.append({
                'id': s.id,
                'text': s.name
            })
        return JsonResponse(data, safe=False)
    return JsonResponse([], safe=False)

def get_semesters(request):
    """Get all semesters (AJAX)"""
    semesters = Semester.objects.all()
    data = []
    for s in semesters:
        data.append({
            'id': s.id,
            'text': f"Semester {s.number}"
        })
    return JsonResponse(data, safe=False)
# Add these imports at the top of your views.py

def attendance_statistics_enhanced(request):
    """Enhanced attendance statistics with short attendance data"""
    # ... [your existing attendance_statistics code] ...
    
    # Add short attendance count
    from django.db.models import Count, Q
    
    # Get short attendance count
    students = Student.objects.all()
    short_attendance_students = []
    
    for student in students:
        attendance_records = Attendance.objects.filter(student=student)
        total_days = attendance_records.count()
        if total_days > 0:
            present_days = attendance_records.filter(status='P').count()
            percentage = (present_days / total_days) * 100
            if percentage < 75:
                short_attendance_students.append({
                    'student': student,
                    'percentage': percentage
                })
    
    # Sort by percentage
    short_attendance_students.sort(key=lambda x: x['percentage'])
    
    # Get critical count
    critical_students = [s for s in short_attendance_students if s['percentage'] < 50]
    
    # Get very critical count
    very_critical_students = [s for s in short_attendance_students if s['percentage'] < 30]
    
    # Get problem subjects
    problem_subjects = Attendance.objects.values(
        'subject__code', 'subject__name'
    ).annotate(
        low_count=Count('id', filter=Q(status='A'))
    ).order_by('-low_count')[:5]
    
    context.update({
        'short_attendance_students': short_attendance_students[:10],  # Top 10
        'short_attendance_count': len(short_attendance_students),
        'critical_count': len(critical_students),
        'very_critical_count': len(very_critical_students),
        'problem_subjects': problem_subjects,
    })
    
    return render(request, 'attendance/attendance_statistics.html', context)
def get_subjects_by_semester(request):
    """Get subjects by semester number (AJAX)"""
    semester_number = request.GET.get('semester_id')  # This is actually semester NUMBER, not Semester ID
    discipline_id = request.GET.get('discipline_id')
    
    try:
        # Convert semester_id to integer (it's the semester number, not Semester model ID)
        if semester_number:
            semester_num = int(semester_number)
            
            # Get subjects for this semester number
            subjects = Subject.objects.filter(semester=semester_num)
            
            # Filter by discipline if provided
            if discipline_id:
                subjects = subjects.filter(desciplain_id=discipline_id)  # Note: field is 'desciplain', not 'discipline'
            
            data = []
            for subject in subjects:
                data.append({
                    'id': subject.id,
                    'text': f"{subject.code} - {subject.name}",
                    'code': subject.code,
                    'name': subject.name,
                    'semester': subject.semester
                })
            
            return JsonResponse(data, safe=False)
        else:
            return JsonResponse([], safe=False)
            
    except ValueError:
        return JsonResponse([], safe=False)
    except Exception as e:
        print(f"Error loading subjects: {str(e)}")  # For debugging
        return JsonResponse({'error': str(e)}, status=500)
def get_subjects_for_attendance(request):
    """Get subjects filtered by semester number and discipline (AJAX)"""
    semester_number = request.GET.get('semester_id')
    discipline_id = request.GET.get('discipline_id')
    
    if not semester_number or not discipline_id:
        return JsonResponse([], safe=False)
    
    try:
        semester_num = int(semester_number)
        
        # Get subjects for this semester and discipline
        subjects = Subject.objects.filter(
            semester=semester_num,
            desciplain_id=discipline_id
        )
        
        # Also check SubjectAssign for this semester and discipline
        from Academic.models import Semester as SemesterModel
        
        try:
            # Get Semester model instance for this semester number
            semester_obj = SemesterModel.objects.get(number=semester_num)
            
            # Get subjects from SubjectAssign for this semester and discipline
            assigned_subjects = SubjectAssign.objects.filter(
                semester=semester_obj,
                discipline_id=discipline_id
            ).select_related('subject')
            
            # Combine both querysets
            subject_ids = list(subjects.values_list('id', flat=True))
            assigned_subject_ids = [a.subject_id for a in assigned_subjects]
            
            # Get unique subjects
            all_subject_ids = list(set(subject_ids + assigned_subject_ids))
            all_subjects = Subject.objects.filter(id__in=all_subject_ids)
            
        except SemesterModel.DoesNotExist:
            all_subjects = subjects
        
        data = []
        for subject in all_subjects:
            data.append({
                'id': subject.id,
                'text': f"{subject.code} - {subject.name}",
                'code': subject.code,
                'name': subject.name,
                'semester': subject.semester
            })
        
        return JsonResponse(data, safe=False)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return JsonResponse([], safe=False)
def get_students_by_section(request):


    """Get students by section and semester (AJAX)"""
    section_id = request.GET.get('section_id')
    semester_id = request.GET.get('semester_id')
    
    if section_id and semester_id:
        students = Student.objects.filter(
            section_id=section_id,
            semester_id=semester_id
        )
        data = []
        for student in students:
            data.append({
                'id': student.id,
                'student_id': student.student_id,
                'first_name': student.first_name,
                'last_name': student.last_name
            })
        return JsonResponse({'students': data})
    
    return JsonResponse({'students': []})
    """Get students by section and semester (AJAX)"""
    section_id = request.GET.get('section_id')
    semester_id = request.GET.get('semester_id')
    
    if section_id and semester_id:
        students = Student.objects.filter(
            section_id=section_id,
            semester_id=semester_id
        ).values('id', 'student_id', 'first_name', 'last_name')
        return JsonResponse({'students': list(students)})
    
    return JsonResponse({'students': []})


# attendance/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Count, Q
from django.core.paginator import Paginator
from datetime import date, datetime, timedelta
import json
from collections import defaultdict  # Add this import

from .models import Attendance, DailyAttendanceSummary, MonthlyAttendanceReport
from student.models import Student
from teachers.models import Teacher
from subject.models import Subject
from Academic.models import Batch, Semester, Section, Discipline

# ... rest of your existing code ...

def short_attendance(request):
    """View students with short attendance (below threshold)"""
    # Get filter parameters
    batch_id = request.GET.get('batch')
    discipline_id = request.GET.get('discipline')
    threshold = int(request.GET.get('threshold', 75))
    
    # Get all students
    students = Student.objects.select_related('batch', 'section', 'semester', 'discipline')
    
    # Apply filters
    if batch_id:
        students = students.filter(batch_id=batch_id)
    if discipline_id:
        students = students.filter(discipline_id=discipline_id)
    
    # Calculate attendance for each student
    short_attendance_students = []
    for student in students:
        # Get all attendance for this student
        attendance_records = Attendance.objects.filter(student=student)
        total_days = attendance_records.count()
        
        if total_days == 0:
            continue
            
        present_days = attendance_records.filter(status='P').count()
        overall_percentage = (present_days / total_days) * 100 if total_days > 0 else 0
        
        # Check if below threshold
        if overall_percentage < threshold:
            # Get subject-wise attendance
            subject_stats = []
            
            # Get subjects from attendance records
            subjects_from_attendance = Subject.objects.filter(
                attendances__student=student
            ).distinct()
            
            # If you have a SubjectAssign model, get subjects from there too
            try:
                from Academic.models import SubjectAssign
                subjects_from_assign = Subject.objects.filter(
                    subjectassign__student=student
                ).distinct()
                
                # Combine both querysets
                subject_ids = list(subjects_from_attendance.values_list('id', flat=True))
                assigned_subject_ids = list(subjects_from_assign.values_list('id', flat=True))
                all_subject_ids = list(set(subject_ids + assigned_subject_ids))
                
                # Get all unique subjects
                subjects = Subject.objects.filter(id__in=all_subject_ids)
            except:
                # If SubjectAssign doesn't exist, just use attendance subjects
                subjects = subjects_from_attendance
            
            for subject in subjects:
                subject_attendance = attendance_records.filter(subject=subject)
                subject_total = subject_attendance.count()
                if subject_total > 0:
                    subject_present = subject_attendance.filter(status='P').count()
                    subject_percentage = (subject_present / subject_total) * 100
                    if subject_percentage < threshold:
                        subject_stats.append({
                            'subject': subject,
                            'percentage': subject_percentage
                        })
            
            # Sort by lowest percentage
            subject_stats.sort(key=lambda x: x['percentage'])
            
            student_data = {
                'student': student,
                'total_days': total_days,
                'present_days': present_days,
                'overall_percentage': overall_percentage,
                'low_subjects': subject_stats,
                'lowest_percentage': subject_stats[0]['percentage'] if subject_stats else 0
            }
            
            short_attendance_students.append(student_data)
    
    # Sort by overall percentage (lowest first)
    short_attendance_students.sort(key=lambda x: x['overall_percentage'])
    
    # Get statistics
    total_students = students.count()
    short_attendance_count = len(short_attendance_students)
    critical_count = len([s for s in short_attendance_students if s['overall_percentage'] < 50])
    good_attendance_count = total_students - short_attendance_count
    
    # Get batch distribution
    batch_distribution = []
    if batch_id:
        # For selected batch only
        batch_students = Student.objects.filter(batch_id=batch_id)
        total_in_batch = batch_students.count()
        short_in_batch = short_attendance_count
        percentage = (short_in_batch / total_in_batch * 100) if total_in_batch > 0 else 0
        batch_distribution.append({
            'batch__name': batch_students.first().batch.name if batch_students.exists() else 'Selected Batch',
            'total_students': total_in_batch,
            'short_count': short_in_batch,
            'percentage': percentage
        })
    else:
        # For all batches
        batches = Batch.objects.all()
        for batch in batches:
            batch_students = students.filter(batch=batch)
            total_in_batch = batch_students.count()
            if total_in_batch > 0:
                # Calculate short attendance in this batch
                short_in_batch = 0
                for student_data in short_attendance_students:
                    if student_data['student'].batch == batch:
                        short_in_batch += 1
                
                percentage = (short_in_batch / total_in_batch * 100) if total_in_batch > 0 else 0
                batch_distribution.append({
                    'batch__name': batch.name,
                    'total_students': total_in_batch,
                    'short_count': short_in_batch,
                    'percentage': percentage
                })
    
    # Get problem subjects (subjects with most low attendance)
    problem_subjects = []
    subject_low_count = defaultdict(int)  # Now this will work
    subject_lowest_percentage = defaultdict(float)
    
    for student_data in short_attendance_students:
        for subject_stat in student_data['low_subjects']:
            subject = subject_stat['subject']
            subject_low_count[subject] += 1
            if subject not in subject_lowest_percentage or subject_stat['percentage'] < subject_lowest_percentage[subject]:
                subject_lowest_percentage[subject] = subject_stat['percentage']
    
    for subject, count in subject_low_count.items():
        problem_subjects.append({
            'subject__code': subject.code,
            'subject__name': subject.name,
            'low_count': count,
            'lowest_percentage': subject_lowest_percentage[subject]
        })
    
    # Sort by most low attendance
    problem_subjects.sort(key=lambda x: x['low_count'], reverse=True)
    
    # Pagination
    paginator = Paginator(short_attendance_students, 25)  # Show 25 students per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'short_attendance_students': page_obj,
        'page_obj': page_obj,
        'total_students': total_students,
        'short_attendance_count': short_attendance_count,
        'critical_count': critical_count,
        'good_attendance_count': good_attendance_count,
        'batches': Batch.objects.all(),
        'disciplines': Discipline.objects.all(),
        'selected_batch': batch_id,
        'selected_discipline': discipline_id,
        'selected_threshold': str(threshold),
        'batch_distribution': batch_distribution,
        'problem_subjects': problem_subjects[:10],  # Top 10 problem subjects
    }
    
    return render(request, 'attendance/short_attendance.html', context)

def subject_short_attendance(request):
    """View subjects with students having short attendance"""
    # Get filter parameters
    discipline_id = request.GET.get('discipline')
    semester_num = request.GET.get('semester')
    threshold = int(request.GET.get('threshold', 75))
    
    # Get all subjects - REMOVED select_related('desciplain') since it doesn't exist
    subjects = Subject.objects.all()
    
    # Apply filters - REMOVED desciplain filter since it doesn't exist
    # If you want to filter by discipline, you need to use SubjectAssign or another model
    # For now, we'll skip discipline filter
    if semester_num:
        # Assuming your Subject model has a semester field
        # If not, you'll need to adjust this
        try:
            subjects = subjects.filter(semester=semester_num)
        except:
            pass
    
    # Calculate statistics for each subject
    subject_stats = []
    total_affected_students = 0
    
    for subject in subjects:
        # Get all attendance for this subject
        attendance_records = Attendance.objects.filter(subject=subject)
        
        if not attendance_records.exists():
            continue
        
        # Get unique students for this subject
        student_ids = attendance_records.values_list('student', flat=True).distinct()
        students = Student.objects.filter(id__in=student_ids)
        
        total_students = students.count()
        if total_students == 0:
            continue
        
        # Calculate student-wise attendance
        short_students = 0
        student_percentages = []
        lowest_percentage = 100
        
        for student in students:
            student_records = attendance_records.filter(student=student)
            total_days = student_records.count()
            if total_days == 0:
                continue
            
            present_days = student_records.filter(status='P').count()
            percentage = (present_days / total_days) * 100
            student_percentages.append(percentage)
            
            if percentage < lowest_percentage:
                lowest_percentage = percentage
            
            if percentage < threshold:
                short_students += 1
                total_affected_students += 1
        
        if not student_percentages:
            continue
        
        # Calculate average percentage
        average_percentage = sum(student_percentages) / len(student_percentages)
        
        # Calculate percentage of students with short attendance
        short_percentage = (short_students / total_students) * 100 if total_students > 0 else 0
        
        if short_students > 0:  # Only include subjects with short attendance
            subject_stats.append({
                'subject': subject,
                'total_students': total_students,
                'short_students': short_students,
                'short_percentage': short_percentage,
                'lowest_percentage': lowest_percentage,
                'average_percentage': average_percentage
            })
    
    # Sort by number of short students (most first)
    subject_stats.sort(key=lambda x: x['short_students'], reverse=True)
    
    # Get best performing subjects (no short attendance)
    best_subjects = []
    for subject in subjects:
        attendance_records = Attendance.objects.filter(subject=subject)
        if not attendance_records.exists():
            continue
        
        student_ids = attendance_records.values_list('student', flat=True).distinct()
        students = Student.objects.filter(id__in=student_ids)
        
        all_good = True
        student_percentages = []
        
        for student in students:
            student_records = attendance_records.filter(student=student)
            total_days = student_records.count()
            if total_days == 0:
                continue
            
            present_days = student_records.filter(status='P').count()
            percentage = (present_days / total_days) * 100
            student_percentages.append(percentage)
            
            if percentage < threshold:
                all_good = False
                break
        
        if all_good and student_percentages:
            average_percentage = sum(student_percentages) / len(student_percentages)
            best_subjects.append({
                'subject': subject,
                'total_students': len(student_ids),
                'average_percentage': average_percentage
            })
    
    # Sort best subjects by average percentage (highest first)
    best_subjects.sort(key=lambda x: x['average_percentage'], reverse=True)
    
    # Get unique semesters from subjects
    # Assuming Subject model has a semester field (ForeignKey to Semester)
    try:
        semesters = Subject.objects.values_list('semester__number', flat=True).distinct().order_by('semester__number')
    except:
        semesters = []
    
    context = {
        'subject_stats': subject_stats,
        'best_subjects': best_subjects,
        'total_subjects': subjects.count(),
        'problem_subjects_count': len(subject_stats),
        'total_affected_students': total_affected_students,
        'disciplines': Discipline.objects.all(),  # For filter dropdown
        'semesters': semesters,
        'selected_discipline': request.GET.get('discipline'),
        'selected_semester': semester_num,
        'selected_threshold': str(threshold),
    }
    
    return render(request, 'attendance/subject_short_attendance.html', context)

def subject_detail_short_attendance(request, subject_id):
    """View students with short attendance for a specific subject"""
    subject = get_object_or_404(Subject, id=subject_id)
    
    # Get filter parameters
    batch_id = request.GET.get('batch')
    section_id = request.GET.get('section')
    threshold = int(request.GET.get('threshold', 75))
    
    # Get all attendance for this subject
    attendance_records = Attendance.objects.filter(subject=subject)
    
    # Calculate overall statistics
    total_records = attendance_records.count()
    present_records = attendance_records.filter(status='P').count()
    absent_records = attendance_records.filter(status='A').count()
    overall_percentage = (present_records / total_records * 100) if total_records > 0 else 0
    
    # Get unique students for this subject
    student_ids = attendance_records.values_list('student', flat=True).distinct()
    students = Student.objects.filter(id__in=student_ids).select_related(
        'batch', 'section', 'semester'
    )
    
    # Apply filters
    if batch_id:
        students = students.filter(batch_id=batch_id)
    
    if section_id:
        students = students.filter(section_id=section_id)
    
    # Calculate student-wise attendance
    short_attendance_students = []
    all_percentages = []
    lowest_percentage = 100
    highest_percentage = 0
    
    for student in students:
        student_records = attendance_records.filter(student=student)
        total_days = student_records.count()
        
        if total_days == 0:
            continue
        
        present_days = student_records.filter(status='P').count()
        percentage = (present_days / total_days) * 100
        all_percentages.append(percentage)
        
        # Update lowest and highest
        if percentage < lowest_percentage:
            lowest_percentage = percentage
        if percentage > highest_percentage:
            highest_percentage = percentage
        
        # Check if below threshold
        if percentage < threshold:
            student_data = {
                'student': student,
                'total_days': total_days,
                'present_days': present_days,
                'percentage': percentage
            }
            short_attendance_students.append(student_data)
    
    # Sort by percentage (lowest first)
    short_attendance_students.sort(key=lambda x: x['percentage'])
    
    # Calculate statistics
    total_students = students.count()
    short_attendance_count = len(short_attendance_students)
    critical_count = len([s for s in short_attendance_students if s['percentage'] < 50])
    very_critical_count = len([s for s in short_attendance_students if s['percentage'] < 30])
    good_attendance_count = total_students - short_attendance_count
    perfect_attendance_count = len([p for p in all_percentages if p == 100])
    
    # Calculate average and median
    if all_percentages:
        average_percentage = sum(all_percentages) / len(all_percentages)
        sorted_percentages = sorted(all_percentages)
        mid = len(sorted_percentages) // 2
        median_percentage = sorted_percentages[mid] if len(sorted_percentages) % 2 != 0 else (sorted_percentages[mid-1] + sorted_percentages[mid]) / 2
    else:
        average_percentage = 0
        median_percentage = 0
    
    # Get batch distribution
    batch_distribution = []
    if batch_id:
        # For selected batch only
        batch_students = students.filter(batch_id=batch_id)
        total_in_batch = batch_students.count()
        short_in_batch = short_attendance_count
        percentage = (short_in_batch / total_in_batch * 100) if total_in_batch > 0 else 0
        batch_distribution.append({
            'batch__name': batch_students.first().batch.name if batch_students.exists() else 'Selected Batch',
            'total_students': total_in_batch,
            'short_count': short_in_batch,
            'percentage': percentage
        })
    else:
        # For all batches
        batches = Batch.objects.filter(student__in=students).distinct()
        for batch in batches:
            batch_students = students.filter(batch=batch)
            total_in_batch = batch_students.count()
            if total_in_batch > 0:
                # Calculate short attendance in this batch
                short_in_batch = 0
                for student_data in short_attendance_students:
                    if student_data['student'].batch == batch:
                        short_in_batch += 1
                
                batch_percentage = (short_in_batch / total_in_batch * 100) if total_in_batch > 0 else 0
                batch_distribution.append({
                    'batch__name': batch.name,
                    'total_students': total_in_batch,
                    'short_count': short_in_batch,
                    'percentage': batch_percentage
                })
    
    # Get filter names for display
    selected_batch_name = None
    selected_section_name = None
    
    if batch_id:
        try:
            batch = Batch.objects.get(id=batch_id)
            selected_batch_name = batch.name
        except:
            selected_batch_name = "Unknown"
    
    if section_id:
        try:
            section = Section.objects.get(id=section_id)
            selected_section_name = section.name
        except:
            selected_section_name = "Unknown"
    
    context = {
        'subject': subject,
        'total_students': total_students,
        'total_records': total_records,
        'present_records': present_records,
        'absent_records': absent_records,
        'overall_percentage': overall_percentage,
        'short_attendance_students': short_attendance_students,
        'short_attendance_count': short_attendance_count,
        'critical_count': critical_count,
        'very_critical_count': very_critical_count,
        'good_attendance_count': good_attendance_count,
        'perfect_attendance_count': perfect_attendance_count,
        'average_percentage': average_percentage,
        'median_percentage': median_percentage,
        'lowest_percentage': lowest_percentage,
        'highest_percentage': highest_percentage,
        'batch_distribution': batch_distribution,
        'batches': Batch.objects.filter(student__in=students).distinct(),
        'sections': Section.objects.filter(student__in=students).distinct(),
        'selected_batch': batch_id,
        'selected_section': section_id,
        'selected_threshold': str(threshold),
        'selected_batch_name': selected_batch_name,
        'selected_section_name': selected_section_name,
    }
    
    return render(request, 'attendance/subject_detail_short_attendance.html', context)
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.conf import settings
from datetime import datetime

def subject_short_attendance_report(request, subject_id):
    """Generate PDF/Print report for subject short attendance"""
    subject = get_object_or_404(Subject, id=subject_id)
    
    # Get filter parameters
    batch_id = request.GET.get('batch')
    section_id = request.GET.get('section')
    threshold = int(request.GET.get('threshold', 75))
    
    # Get all attendance for this subject
    attendance_records = Attendance.objects.filter(subject=subject)
    
    # Calculate overall statistics
    total_records = attendance_records.count()
    present_records = attendance_records.filter(status='P').count()
    absent_records = attendance_records.filter(status='A').count()
    overall_percentage = (present_records / total_records * 100) if total_records > 0 else 0
    
    # Get unique students for this subject
    student_ids = attendance_records.values_list('student', flat=True).distinct()
    students = Student.objects.filter(id__in=student_ids).select_related(
        'batch', 'section', 'semester'
    )
    
    # Apply filters
    if batch_id:
        students = students.filter(batch_id=batch_id)
    
    if section_id:
        students = students.filter(section_id=section_id)
    
    # Calculate student-wise attendance
    short_attendance_students = []
    all_percentages = []
    lowest_percentage = 100
    highest_percentage = 0
    
    for student in students:
        student_records = attendance_records.filter(student=student)
        total_days = student_records.count()
        
        if total_days == 0:
            continue
        
        present_days = student_records.filter(status='P').count()
        percentage = (present_days / total_days) * 100
        all_percentages.append(percentage)
        
        # Update lowest and highest
        if percentage < lowest_percentage:
            lowest_percentage = percentage
        if percentage > highest_percentage:
            highest_percentage = percentage
        
        # Check if below threshold
        if percentage < threshold:
            student_data = {
                'student': student,
                'total_days': total_days,
                'present_days': present_days,
                'percentage': percentage
            }
            short_attendance_students.append(student_data)
    
    # Sort by percentage (lowest first)
    short_attendance_students.sort(key=lambda x: x['percentage'])
    
    # Calculate statistics
    total_students = students.count()
    short_attendance_count = len(short_attendance_students)
    critical_count = len([s for s in short_attendance_students if s['percentage'] < 50])
    very_critical_count = len([s for s in short_attendance_students if s['percentage'] < 30])
    good_attendance_count = total_students - short_attendance_count
    perfect_attendance_count = len([p for p in all_percentages if p == 100])
    
    # Calculate average and median
    if all_percentages:
        average_percentage = sum(all_percentages) / len(all_percentages)
        sorted_percentages = sorted(all_percentages)
        mid = len(sorted_percentages) // 2
        median_percentage = sorted_percentages[mid] if len(sorted_percentages) % 2 != 0 else (sorted_percentages[mid-1] + sorted_percentages[mid]) / 2
    else:
        average_percentage = 0
        median_percentage = 0
    
    # Get batch distribution
    batch_distribution = []
    if batch_id:
        # For selected batch only
        batch_students = students.filter(batch_id=batch_id)
        total_in_batch = batch_students.count()
        short_in_batch = short_attendance_count
        percentage = (short_in_batch / total_in_batch * 100) if total_in_batch > 0 else 0
        batch_distribution.append({
            'batch__name': batch_students.first().batch.name if batch_students.exists() else 'Selected Batch',
            'total_students': total_in_batch,
            'short_count': short_in_batch,
            'percentage': percentage
        })
    else:
        # For all batches
        batches = Batch.objects.filter(student__in=students).distinct()
        for batch in batches:
            batch_students = students.filter(batch=batch)
            total_in_batch = batch_students.count()
            if total_in_batch > 0:
                # Calculate short attendance in this batch
                short_in_batch = 0
                for student_data in short_attendance_students:
                    if student_data['student'].batch == batch:
                        short_in_batch += 1
                
                batch_percentage = (short_in_batch / total_in_batch * 100) if total_in_batch > 0 else 0
                batch_distribution.append({
                    'batch__name': batch.name,
                    'total_students': total_in_batch,
                    'short_count': short_in_batch,
                    'percentage': batch_percentage
                })
    
    # Get subject teacher information
    subject_teacher = None
    try:
        # Try to get subject teacher from SubjectAssign or similar model
        from Academic.models import SubjectAssign
        assign = SubjectAssign.objects.filter(subject=subject).first()
        if assign and assign.teacher:
            subject_teacher = assign.teacher.get_full_name()
    except:
        pass
    
    # Get department information
    department_name = None
    if subject.desciplain:
        department_name = f"{subject.desciplain.program} Department"
    
    # Prepare context for report
    context = {
        'subject': subject,
        'short_attendance_students': short_attendance_students,
        'total_students': total_students,
        'short_attendance_count': short_attendance_count,
        'critical_count': critical_count,
        'very_critical_count': very_critical_count,
        'good_attendance_count': good_attendance_count,
        'perfect_attendance_count': perfect_attendance_count,
        'total_records': total_records,
        'present_records': present_records,
        'absent_records': absent_records,
        'overall_percentage': overall_percentage,
        'average_percentage': average_percentage,
        'median_percentage': median_percentage,
        'lowest_percentage': lowest_percentage,
        'highest_percentage': highest_percentage,
        'batch_distribution': batch_distribution,
        'selected_threshold': threshold,
        'subject_teacher': subject_teacher,
        'department_name': department_name,
        'generated_date': datetime.now(),
        'report_id': f"SA-{subject.code}-{datetime.now().strftime('%Y%m%d')}",
        'report_period': f"{datetime.now().strftime('%B %Y')}",
        
        # University information (you can customize these)
        'university_name': getattr(settings, 'UNIVERSITY_NAME', 'Your University'),
        'university_slogan': getattr(settings, 'UNIVERSITY_SLOGAN', 'Excellence in Education'),
        'university_address': getattr(settings, 'UNIVERSITY_ADDRESS', 'City, Country'),
        'university_logo': getattr(settings, 'UNIVERSITY_LOGO_URL', None),
        'coordinator_name': getattr(settings, 'COORDINATOR_NAME', 'Academic Coordinator'),
        'hod_name': getattr(settings, 'HOD_NAME', 'Head of Department'),
    }
    
    return render(request, 'attendance/subject_short_attendance_report.html', context)