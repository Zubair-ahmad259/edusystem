from django.shortcuts import render
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Q, Count
from decimal import Decimal

# Import models
from teachers.models import Teacher
from student.models import Student  # ADD THIS IMPORT
from subject.models import Subject, SubjectAssign
from Academic.models import Batch, Semester, Section, Discipline
from exam_manag.models import Exam, ExamResult, ComprehensiveResult
from assignm.models import Assignment, AssignmentSubmission
from attendance.models import Attendance
def index(request):
    return render(request, "authentication/login.html")
    #  return render(request, "Home/index.html")

def admin_dashboard(request):
    return render(request, "Home/index.html")

@login_required
def student_dashboard(request):
    """Student Dashboard with all data including fees"""
    try:
        from fee_system.models import UploadFee
        
        student = Student.objects.get(user=request.user)
        
        # Get current date
        current_date = timezone.now()
        
        # Get enrolled subjects
        total_subjects = Subject.objects.filter(
            assigned_teachers__sections=student.section,
            assigned_teachers__batch=student.batch,
            assigned_teachers__is_active=True
        ).distinct().count()
        
        # Get CGPA from comprehensive results
        comp_result = ComprehensiveResult.objects.filter(
            student=student,
            semester=student.semester
        ).first()
        cgpa = float(comp_result.cgpa) if comp_result and comp_result.cgpa else 0.0
        
        # Credits earned (assuming 3 credits per subject)
        credits_earned = total_subjects * 3
        
        # Get attendance
        from attendance.models import Attendance
        attendance_records = Attendance.objects.filter(student=student)
        total_classes = attendance_records.count()
        present_days = attendance_records.filter(status='Present').count()
        attendance_percentage = int((present_days / total_classes) * 100) if total_classes > 0 else 0
        
        # Get recent results
        recent_results = []
        exam_results = ExamResult.objects.filter(
            student=student,
            exam__is_published=True
        ).select_related('exam', 'exam__subject')[:10]
        
        for result in exam_results:
            marks = float(result.marks_obtained) if result.marks_obtained else 0
            total = float(result.exam.total_marks)
            percentage = (marks / total * 100) if total > 0 else 0
            recent_results.append({
                'subject_code': result.exam.subject.code,
                'exam_type': result.exam.get_exam_type_display(),
                'marks_obtained': marks,
                'total_marks': total,
                'percentage': round(percentage, 1),
                'grade': result.grade if result.grade else 'F',
            })
        
        # Get fee details from UploadFee model
        fee_record = UploadFee.objects.filter(student=student).first()
        
        if fee_record:
            total_fee = float(fee_record.total_fee())
            paid_fee = float(fee_record.paid_amount)
            due_fee = float(fee_record.remaining_amount)
            fee_percentage = int((paid_fee / total_fee) * 100) if total_fee > 0 else 0
            fee_status = fee_record.get_status_display()
            fee_status_color = fee_record.get_status_color()
            due_date = fee_record.due_date
            is_overdue = fee_record.is_overdue
        else:
            total_fee = 0
            paid_fee = 0
            due_fee = 0
            fee_percentage = 0
            fee_status = 'No Fee Record'
            fee_status_color = 'secondary'
            due_date = None
            is_overdue = False
        
        context = {
            'student': student,
            'current_date': current_date,
            'total_subjects': total_subjects,
            'cgpa': round(cgpa, 2),
            'credits_earned': credits_earned,
            'attendance_percentage': attendance_percentage,
            'present_days': present_days,
            'absent_days': total_classes - present_days,
            'total_classes': total_classes,
            'recent_results': recent_results,
            # Fee details
            'total_fee': total_fee,
            'paid_fee': paid_fee,
            'due_fee': due_fee,
            'fee_percentage': fee_percentage,
            'fee_status': fee_status,
            'fee_status_color': fee_status_color,
            'due_date': due_date,
            'is_overdue': is_overdue,
        }
        return render(request, 'students/index.html', context)
        
    except Student.DoesNotExist:
        messages.error(request, 'Student profile not found!')
        return redirect('index')
    except Exception as e:
        print(f"Error in student_dashboard: {str(e)}")
        messages.error(request, f'Error loading dashboard: {str(e)}')
        return redirect('index')


def teacher_dashboard(request):
    return render(request,"teacher/teacher_dashboard.html")
