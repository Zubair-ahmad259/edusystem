from django.shortcuts import render, get_object_or_404, redirect
from .models import Cases
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import JsonResponse
from student.models import Student
from Academic.models import Batch, Semester, Section, Discipline
from subject.models import Subject
from teachers.models import Teacher


class CaseForm(forms.ModelForm):
    class Meta:
        model = Cases
        fields = [
            'case_type', 'student', 'teacher', 'subject', 'batch', 
            'semester', 'section', 'Disciplines', 'incident_date', 
            'case_date', 'description', 'fine', 'status',
            'committee_hearing_date', 'committee_hearing_time', 
            'committee_venue', 'committee_remarks'
        ]
        widgets = {
            'incident_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'case_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'committee_hearing_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'committee_hearing_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'committee_remarks': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }


@login_required
def case_list(request):
    cases = Cases.objects.all().order_by('-created_at')
    return render(request, "cases/case_list.html", {"cases": cases})


@login_required
def case_detail(request, case_id):
    case = get_object_or_404(Cases, id=case_id)
    return render(request, "cases/case_detail.html", {"case": case})
@login_required
def add_case(request):
    if request.method == "POST":
        form = CaseForm(request.POST, request.FILES)
        if form.is_valid():
            case = form.save(commit=False)
            if not case.case_date:
                case.case_date = timezone.now().date()
            case.save()
            messages.success(request, 'Case added successfully!')
            return redirect("ddcomit:case_list")
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CaseForm()
    
    # Get all disciplines for dropdown
    disciplines = Discipline.objects.all()
    semesters = Semester.objects.all()
    
    # Define case type choices for the form
    CASE_TYPE_CHOICES = [
        ('academic', 'Academic Misconduct'),
        ('ddc', 'Department Discipline Committee'),
        ('unfair_means', 'Unfair Means'),
        ('other', 'Other'),
    ]
    
    context = {
        'form': form,
        'disciplines': disciplines,
        'semesters': semesters,
        'case_type_choices': CASE_TYPE_CHOICES,
    }
    return render(request, "cases/add_case.html", context)

# AJAX endpoints
def get_batches_by_discipline(request):
    discipline_id = request.GET.get('discipline_id')
    if discipline_id:
        batches = Batch.objects.filter(discipline_id=discipline_id).values('id', 'name')
        return JsonResponse(list(batches), safe=False)
    return JsonResponse([], safe=False)


def get_sections_by_batch(request):
    batch_id = request.GET.get('batch_id')
    if batch_id:
        sections = Section.objects.filter(batch_id=batch_id).values('id', 'name')
        return JsonResponse(list(sections), safe=False)
    return JsonResponse([], safe=False)


def get_students_by_section(request):
    section_id = request.GET.get('section_id')
    if section_id:
        students = Student.objects.filter(section_id=section_id).values('id', 'first_name', 'last_name', 'student_id')
        student_list = [
            {
                'id': s['id'],
                'name': f"{s['first_name']} {s['last_name']} ({s['student_id']})"
            }
            for s in students
        ]
        return JsonResponse(student_list, safe=False)
    return JsonResponse([], safe=False)


def get_subjects_by_semester(request):
    semester_id = request.GET.get('semester_id')
    if semester_id:
        subjects = Subject.objects.filter(
            assigned_teachers__semester_id=semester_id,
            assigned_teachers__is_active=True
        ).distinct().values('id', 'code', 'name')
        subject_list = [
            {
                'id': s['id'],
                'name': f"{s['code']} - {s['name']}"
            }
            for s in subjects
        ]
        return JsonResponse(subject_list, safe=False)
    return JsonResponse([], safe=False)


def get_teachers_by_subject(request):
    subject_id = request.GET.get('subject_id')
    if subject_id:
        teachers = Teacher.objects.filter(
            assigned_subjects__subject_id=subject_id,
            assigned_subjects__is_active=True
        ).distinct().values('id', 'first_name', 'last_name')
        teacher_list = [
            {
                'id': t['id'],
                'name': f"{t['first_name']} {t['last_name']}"
            }
            for t in teachers
        ]
        return JsonResponse(teacher_list, safe=False)
    return JsonResponse([], safe=False)


@login_required
def committee_cases(request):
    """View for Department Discipline Committee - All DDC cases"""
    ddc_cases = Cases.objects.filter(case_type='ddc').order_by('-committee_hearing_date', '-created_at')
    
    upcoming_hearings = ddc_cases.filter(
        committee_hearing_date__gte=timezone.now().date(),
        status__in=['pending', 'under_review']
    )
    
    past_hearings = ddc_cases.filter(committee_hearing_date__lt=timezone.now().date())
    
    context = {
        'ddc_cases': ddc_cases,
        'upcoming_hearings': upcoming_hearings,
        'past_hearings': past_hearings,
        'total_cases': ddc_cases.count(),
        'pending_cases': ddc_cases.filter(status='pending').count(),
        'resolved_cases': ddc_cases.filter(status='resolved').count(),
    }
    return render(request, "cases/committee_cases.html", context)


@login_required
def update_case_status(request, case_id):
    """Update case status"""
    case = get_object_or_404(Cases, id=case_id)
    if request.method == "POST":
        status = request.POST.get('status')
        remarks = request.POST.get('remarks', '')
        if status:
            case.status = status
            case.committee_remarks = remarks
            case.save()
            messages.success(request, f'Case status updated to {status}!')
    return redirect('ddcomit:case_detail', case_id=case_id)


@login_required
def schedule_hearing(request, case_id):
    """Schedule DDC hearing for a case"""
    case = get_object_or_404(Cases, id=case_id)
    if request.method == "POST":
        hearing_date = request.POST.get('hearing_date')
        hearing_time = request.POST.get('hearing_time')
        venue = request.POST.get('venue')
        
        if hearing_date:
            case.committee_hearing_date = hearing_date
            case.committee_hearing_time = hearing_time
            case.committee_venue = venue
            case.status = 'under_review'
            case.save()
            messages.success(request, f'Hearing scheduled for {hearing_date} at {hearing_time}!')
    
    return redirect('ddcomit:case_detail', case_id=case_id)