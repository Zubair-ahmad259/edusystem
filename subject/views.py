from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Subject, SubjectAssign
from student.models import Student
from Academic.models import Discipline, Batch, Semester, Section
from teachers.models import Teacher
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
import json
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta


def subject_dashboard(request):
    """Main dashboard for subject management"""
    # Overall Statistics
    total_subjects = Subject.objects.count()
    active_subjects = Subject.objects.filter(is_active=True).count()
    inactive_subjects = total_subjects - active_subjects
    
    # Subject Type Statistics
    core_subjects = Subject.objects.filter(subject_type='core').count()
    elective_subjects = Subject.objects.filter(subject_type='elective').count()
    
    # Assignment Statistics
    total_assignments = SubjectAssign.objects.count()
    active_assignments = SubjectAssign.objects.filter(is_active=True).count()
    
    # Recent Activity (last 7 days)
    seven_days_ago = timezone.now() - timedelta(days=7)
    recent_subjects = Subject.objects.filter(created_at__gte=seven_days_ago).count()
    recent_assignments = SubjectAssign.objects.filter(assigned_date__gte=seven_days_ago).count()
    
    # Subjects with/without prerequisites
    with_prereqs = Subject.objects.filter(prerequisites__isnull=False).distinct().count()
    without_prereqs = Subject.objects.filter(prerequisites__isnull=True).count()
    
    # Recent Subjects (last 10)
    latest_subjects = Subject.objects.order_by('-created_at')[:10]
    
    # Recent Assignments (last 10)
    latest_assignments = SubjectAssign.objects.select_related(
        'teacher', 'subject', 'batch', 'semester', 'discipline'
    ).prefetch_related('sections').order_by('-assigned_date')[:10]
    
    context = {
        'total_subjects': total_subjects,
        'active_subjects': active_subjects,
        'inactive_subjects': inactive_subjects,
        'core_subjects': core_subjects,
        'elective_subjects': elective_subjects,
        'total_assignments': total_assignments,
        'active_assignments': active_assignments,
        'recent_subjects': recent_subjects,
        'recent_assignments': recent_assignments,
        'with_prereqs': with_prereqs,
        'without_prereqs': without_prereqs,
        'latest_subjects': latest_subjects,
        'latest_assignments': latest_assignments,
    }
    
    return render(request, 'subject/dashboard.html', context)


def quick_stats_api(request):
    """API endpoint for quick statistics (AJAX)"""
    if request.method == 'GET':
        stats = {
            'total_subjects': Subject.objects.count(),
            'active_subjects': Subject.objects.filter(is_active=True).count(),
            'total_assignments': SubjectAssign.objects.count(),
            'active_assignments': SubjectAssign.objects.filter(is_active=True).count(),
        }
        return JsonResponse(stats)
    return JsonResponse({'error': 'Invalid request'}, status=400)


def add_subject(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        code = request.POST.get('code')
        credit_hours = request.POST.get('credit_hours')
        description = request.POST.get('description')
        subject_type = request.POST.get('subject_type')
        prerequisite_ids = request.POST.getlist('prerequisites')

        credit_hours = int(credit_hours) if credit_hours else 3

        if Subject.objects.filter(code=code).exists():
            messages.error(request, "Error: A subject with this code already exists.")
        else:
            try:
                subject = Subject.objects.create(
                    name=name,
                    code=code,
                    credit_hours=credit_hours,
                    description=description,
                    subject_type=subject_type,
                    is_active=True
                )
                
                if prerequisite_ids:
                    prerequisites = Subject.objects.filter(id__in=prerequisite_ids)
                    subject.prerequisites.set(prerequisites)
                
                messages.success(request, "Subject saved successfully.")
            except Exception as e:
                messages.error(request, f"Error saving subject: {str(e)}")
        
        return redirect('subject:view_subject')

    context = {
        'subject_type_choices': Subject.SUBJECT_TYPE_CHOICES,
        'prerequisite_subjects': Subject.objects.all().order_by('code')
    }
    return render(request, 'subject/add-subject.html', context)


def edit_subject(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)
    
    if request.method == 'POST':
        subject.name = request.POST.get('name')
        subject.code = request.POST.get('code')
        subject.credit_hours = int(request.POST.get('credit_hours', 3))
        subject.description = request.POST.get('description')
        subject.subject_type = request.POST.get('subject_type')
        subject.is_active = request.POST.get('is_active') == 'on'
        
        prerequisite_ids = request.POST.getlist('prerequisites')
        
        try:
            subject.save()
            if prerequisite_ids:
                prerequisites = Subject.objects.filter(id__in=prerequisite_ids)
                subject.prerequisites.set(prerequisites)
            else:
                subject.prerequisites.clear()
            
            messages.success(request, "Subject updated successfully.")
            return redirect('subject:view_subject')
        except Exception as e:
            messages.error(request, f"Error updating subject: {str(e)}")
    
    context = {
        'subject': subject,
        'subject_type_choices': Subject.SUBJECT_TYPE_CHOICES,
        'prerequisite_subjects': Subject.objects.exclude(id=subject_id).order_by('code'),
    }
    return render(request, 'subject/edit-subject.html', context)


def delete_subject(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)
    
    if request.method == 'POST':
        try:
            subject.delete()
            messages.success(request, f"Subject '{subject.code}' deleted successfully.")
        except Exception as e:
            messages.error(request, f"Error deleting subject: {str(e)}")
        return redirect('subject:view_subject')
    
    return render(request, 'subject/delete-subject.html', {'subject': subject})


def view_subject(request):
    subjects = Subject.objects.all().order_by('code').prefetch_related('prerequisites')
    
    # Get filter parameters
    code = request.GET.get('code')
    name = request.GET.get('name')
    subject_type = request.GET.get('subject_type')
    is_active = request.GET.get('is_active')

    if code:
        subjects = subjects.filter(code__icontains=code)
    if name:
        subjects = subjects.filter(name__icontains=name)
    if subject_type:
        subjects = subjects.filter(subject_type=subject_type)
    if is_active:
        subjects = subjects.filter(is_active=(is_active.lower() == 'true'))

    # Pagination
    paginator = Paginator(subjects, 10)
    page = request.GET.get('page')
    subjects = paginator.get_page(page)

    context = {
        'subjects': subjects,
        'total_subjects': Subject.objects.count(),
        'subject_type_choices': Subject.SUBJECT_TYPE_CHOICES,
    }
    return render(request, 'subject/subject-list.html', context)


def add_subject_assign(request):
    if request.method == "POST":
        teacher_id = request.POST.get("teacher")
        subject_id = request.POST.get("subject")
        batch_id = request.POST.get("batch")
        semester_id = request.POST.get("semester")
        section_ids = request.POST.getlist("sections")
        discipline_id = request.POST.get("disciplines")
        
        if not all([teacher_id, subject_id, batch_id, semester_id, section_ids, discipline_id]):
            messages.error(request, "Please fill all required fields.")
            return redirect("subject:add_subject_assign")
        
        teacher = get_object_or_404(Teacher, id=teacher_id)
        subject = get_object_or_404(Subject, id=subject_id)
        batch = get_object_or_404(Batch, id=batch_id)
        semester = get_object_or_404(Semester, id=semester_id)
        discipline = get_object_or_404(Discipline, id=discipline_id)

        # Check if assignment exists
        existing_assignment = SubjectAssign.objects.filter(
            teacher=teacher,
            subject=subject,
            batch=batch,
            semester=semester,
            discipline=discipline
        ).first()
        
        if existing_assignment:
            existing_assignment.sections.add(*section_ids)
            messages.success(request, f"Sections added to existing assignment for {subject.name}.")
        else:
            subject_assign = SubjectAssign.objects.create(
                teacher=teacher,
                subject=subject,
                batch=batch,
                semester=semester,
                discipline=discipline,
                is_active=True
            )
            subject_assign.sections.set(section_ids)
            messages.success(request, "Subject assigned successfully.")
        
        return redirect("subject:show_subject_assign")

    context = {
        "teachers": Teacher.objects.all(),
        "subjects": Subject.objects.filter(is_active=True),
        "batches": Batch.objects.all(),
        "semesters": Semester.objects.all(),
        "sections": Section.objects.all(),
        "disciplines": Discipline.objects.all()
    }
    return render(request, "subject/add-subject-assign.html", context)


def edit_subject_assign(request, assign_id):
    assignment = get_object_or_404(SubjectAssign, id=assign_id)
    
    if request.method == "POST":
        teacher_id = request.POST.get("teacher")
        subject_id = request.POST.get("subject")
        batch_id = request.POST.get("batch")
        semester_id = request.POST.get("semester")
        section_ids = request.POST.getlist("sections")
        discipline_id = request.POST.get("disciplines")
        is_active = request.POST.get("is_active") == 'on'
        
        assignment.teacher_id = teacher_id
        assignment.subject_id = subject_id
        assignment.batch_id = batch_id
        assignment.semester_id = semester_id
        assignment.discipline_id = discipline_id
        assignment.is_active = is_active
        assignment.save()
        
        assignment.sections.set(section_ids)
        
        messages.success(request, "Assignment updated successfully.")
        return redirect("subject:show_subject_assign")
    
    context = {
        'assignment': assignment,
        "teachers": Teacher.objects.all(),
        "subjects": Subject.objects.filter(is_active=True),
        "batches": Batch.objects.all(),
        "semesters": Semester.objects.all(),
        "sections": Section.objects.all(),
        "disciplines": Discipline.objects.all(),
        'selected_sections': assignment.sections.all(),
    }
    return render(request, "subject/edit-subject-assign.html", context)


def delete_subject_assign(request, assign_id):
    assignment = get_object_or_404(SubjectAssign, id=assign_id)
    
    if request.method == 'POST':
        try:
            assignment.delete()
            messages.success(request, "Assignment deleted successfully.")
        except Exception as e:
            messages.error(request, f"Error deleting assignment: {str(e)}")
        return redirect('subject:show_subject_assign')
    
    return render(request, 'subject/delete-assign.html', {'assignment': assignment})


def show_subject_assign(request):
    assigns = SubjectAssign.objects.select_related(
        "teacher", "subject", "batch", "semester", "discipline"
    ).prefetch_related("sections").order_by('-id')
    
    # Get filter parameters
    subject_id = request.GET.get('subject')
    teacher_id = request.GET.get('teacher')
    batch_id = request.GET.get('batch')
    semester_id = request.GET.get('semester')
    
    if subject_id:
        assigns = assigns.filter(subject_id=subject_id)
    if teacher_id:
        assigns = assigns.filter(teacher_id=teacher_id)
    if batch_id:
        assigns = assigns.filter(batch_id=batch_id)
    if semester_id:
        assigns = assigns.filter(semester_id=semester_id)
    
    context = {
        "assigns": assigns,
        "subjects": Subject.objects.filter(is_active=True),
        "teachers": Teacher.objects.all(),
        "batches": Batch.objects.all(),
        "semesters": Semester.objects.all(),
    }
    return render(request, "subject/show-subject-assign-record.html", context)


@csrf_exempt
def get_prerequisite_suggestions(request):
    """API endpoint for prerequisite suggestions"""
    if request.method == 'GET':
        subject_id = request.GET.get('subject_id')
        
        # Get all subjects except the current one (for editing)
        subjects = Subject.objects.all()
        if subject_id:
            subjects = subjects.exclude(id=subject_id)
        
        data = [{
            'id': s.id,
            'code': s.code,
            'name': s.name,
            'display': f"{s.code} - {s.name} ({s.credit_hours} credits)"
        } for s in subjects.order_by('code')]
        
        return JsonResponse({'suggestions': data})
    
    return JsonResponse({'error': 'Invalid request method'}, status=400)


@csrf_exempt
def get_sections_for_assignment(request):
    """API endpoint to get sections based on discipline and batch"""
    if request.method == 'GET':
        discipline_id = request.GET.get('discipline_id')
        batch_id = request.GET.get('batch_id')
        
        if not discipline_id or not batch_id:
            return JsonResponse({'error': 'Missing required parameters'}, status=400)
        
        try:
            sections = Section.objects.filter(
                discipline_id=discipline_id,
                batch_id=batch_id
            )
            
            data = [{
                'id': section.id,
                'name': section.name,
                'display': f"Section {section.name}"
            } for section in sections]
            
            return JsonResponse({'sections': data})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=400)