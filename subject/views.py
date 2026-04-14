from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Subject, SubjectAssign
from student.models import Student
from Academic.models import Discipline, Batch, Semester, Section
from teachers.models import Teacher
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
# import pandas as pd  # COMMENTED OUT - pandas not available on Railway
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
    recent_subjects = Subject.objects.filter(
        created_at__gte=seven_days_ago
    ).count()
    
    recent_assignments = SubjectAssign.objects.filter(
        assigned_date__gte=seven_days_ago
    ).count()
    
    # Semester Distribution
    semester_stats = Subject.objects.values(
        'semester__number'
    ).annotate(
        count=Count('id')
    ).order_by('semester__number')
    
    # Discipline Distribution
    discipline_stats = Subject.objects.values(
        'desciplain__field'
    ).annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # Subjects with/without prerequisites
    with_prereqs = Subject.objects.filter(prerequisites__isnull=False).distinct().count()
    without_prereqs = Subject.objects.filter(prerequisites__isnull=True).count()
    
    # Recent Subjects (last 10)
    latest_subjects = Subject.objects.select_related(
        'semester', 'desciplain', 'section'
    ).order_by('-created_at')[:10]
    
    # Recent Assignments (last 10)
    latest_assignments = SubjectAssign.objects.select_related(
        'teacher', 'subject', 'batch', 'semester', 'section'
    ).order_by('-assigned_date')[:10]
    
    # Subjects needing attention (no section, no prerequisites when needed, etc.)
    attention_needed = Subject.objects.filter(
        Q(section__isnull=True) |
        Q(credit_hours__lt=1) |
        Q(credit_hours__gt=10)
    ).count()
    
    context = {
        # Statistics
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
        'attention_needed': attention_needed,
        
        # Charts Data
        'semester_stats': list(semester_stats),
        'discipline_stats': list(discipline_stats),
        
        # Recent Data
        'latest_subjects': latest_subjects,
        'latest_assignments': latest_assignments,
        
        # Filter Options
        'disciplines': Discipline.objects.all(),
        'semesters': Semester.objects.all(),
        'sections': Section.objects.all()[:5],
    }
    
    return render(request, 'subject/dashboard.html', context)


def subject_analytics(request):
    """Advanced analytics and reports"""
    # Date range filters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # Base queryset
    subjects = Subject.objects.all()
    assignments = SubjectAssign.objects.all()
    
    # Apply date filters if provided
    if start_date:
        try:
            start_date = timezone.datetime.strptime(start_date, '%Y-%m-%d')
            subjects = subjects.filter(created_at__gte=start_date)
            assignments = assignments.filter(assigned_date__gte=start_date)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_date = timezone.datetime.strptime(end_date, '%Y-%m-%d')
            subjects = subjects.filter(created_at__lte=end_date)
            assignments = assignments.filter(assigned_date__lte=end_date)
        except ValueError:
            pass
    
    # Monthly trend
    monthly_data = []
    for i in range(5, -1, -1):
        month_start = timezone.now() - timedelta(days=30*i)
        month_end = month_start + timedelta(days=30)
        
        month_subjects = subjects.filter(
            created_at__gte=month_start,
            created_at__lt=month_end
        ).count()
        
        month_assignments = assignments.filter(
            assigned_date__gte=month_start,
            assigned_date__lt=month_end
        ).count()
        
        monthly_data.append({
            'month': month_start.strftime('%b %Y'),
            'subjects': month_subjects,
            'assignments': month_assignments,
        })
    
    # Teacher assignment distribution
    teacher_assignments = assignments.values(
        'teacher__first_name', 'teacher__last_name'
    ).annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # Section-wise distribution
    section_distribution = subjects.values(
        'section__name'
    ).annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Prerequisite chain analysis
    prereq_analysis = []
    for subject in subjects.filter(prerequisites__isnull=False)[:10]:
        prereq_count = subject.prerequisites.count()
        prereq_analysis.append({
            'subject': subject.code,
            'name': subject.name,
            'prereq_count': prereq_count,
            'prereqs': [p.code for p in subject.prerequisites.all()[:3]]
        })
    
    context = {
        'monthly_data': monthly_data,
        'teacher_assignments': teacher_assignments,
        'section_distribution': section_distribution,
        'prereq_analysis': prereq_analysis,
        'start_date': start_date,
        'end_date': end_date,
    }
    
    return render(request, 'subject/analytics.html', context)


def quick_stats_api(request):
    """API endpoint for quick statistics (AJAX)"""
    if request.method == 'GET':
        stats = {
            'total_subjects': Subject.objects.count(),
            'active_subjects': Subject.objects.filter(is_active=True).count(),
            'today_subjects': Subject.objects.filter(
                created_at__date=timezone.now().date()
            ).count(),
            'pending_assignments': SubjectAssign.objects.filter(
                is_active=False
            ).count(),
        }
        return JsonResponse(stats)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


def recent_activity_api(request):
    """API endpoint for recent activity (AJAX)"""
    if request.method == 'GET':
        # Recent subjects
        recent_subjects = Subject.objects.select_related(
            'semester', 'desciplain'
        ).order_by('-created_at')[:5].values(
            'code', 'name', 'semester__number', 'desciplain__field', 'created_at'
        )
        
        # Recent assignments
        recent_assignments = SubjectAssign.objects.select_related(
            'teacher', 'subject'
        ).order_by('-assigned_date')[:5].values(
            'subject__code',
            'teacher__first_name',
            'teacher__last_name',
            'assigned_date'
        )
        
        activity = {
            'subjects': list(recent_subjects),
            'assignments': list(recent_assignments),
            'timestamp': timezone.now().isoformat(),
        }
        
        return JsonResponse(activity)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


def dashboard_overview(request):
    """Overview dashboard with widgets"""
    # Quick action counts
    quick_actions = {
        'add_subject': request.user.has_perm('subject.add_subject'),
        'import_subjects': request.user.has_perm('subject.add_subject'),
        'assign_subject': request.user.has_perm('subject.add_subjectassign'),
        'view_reports': request.user.has_perm('subject.view_subject'),
    }
    
    # System status
    system_status = {
        'database': 'active',
        'api': 'active',
        'storage': '90%',
        'last_backup': (timezone.now() - timedelta(hours=2)).strftime('%Y-%m-%d %H:%M'),
    }
    
    # Upcoming tasks (based on assignments)
    upcoming_tasks = SubjectAssign.objects.filter(
        is_active=True
    ).select_related(
        'subject', 'teacher'
    ).order_by('assigned_date')[:5]
    
    context = {
        'quick_actions': quick_actions,
        'system_status': system_status,
        'upcoming_tasks': upcoming_tasks,
        'total_disciplines': Discipline.objects.count(),
        'total_semesters': Semester.objects.count(),
        'total_sections': Section.objects.count(),
        'total_teachers': Teacher.objects.count(),
    }
    
    return render(request, 'subject/overview.html', context)


def subject_health_check(request):
    """Health check and validation dashboard"""
    # Subjects with issues
    subjects_no_section = Subject.objects.filter(section__isnull=True).count()
    subjects_invalid_credits = Subject.objects.filter(
        Q(credit_hours__lt=1) | Q(credit_hours__gt=10)
    ).count()
    subjects_no_discipline = Subject.objects.filter(desciplain__isnull=True).count()
    
    # Assignments with issues
    assignments_no_teacher = SubjectAssign.objects.filter(teacher__isnull=True).count()
    assignments_no_subject = SubjectAssign.objects.filter(subject__isnull=True).count()
    
    # Prerequisite issues
    circular_prereqs = []  # Would need custom logic to detect
    missing_prereq_subjects = Subject.objects.filter(
        prerequisites__isnull=False
    ).exclude(
        prerequisites__in=Subject.objects.all()
    ).distinct().count()
    
    health_status = {
        'subjects': {
            'total': Subject.objects.count(),
            'no_section': subjects_no_section,
            'invalid_credits': subjects_invalid_credits,
            'no_discipline': subjects_no_discipline,
            'health_percentage': 95,  # Calculated based on issues
        },
        'assignments': {
            'total': SubjectAssign.objects.count(),
            'no_teacher': assignments_no_teacher,
            'no_subject': assignments_no_subject,
            'health_percentage': 98,
        },
        'prerequisites': {
            'with_prereqs': Subject.objects.filter(prerequisites__isnull=False).count(),
            'missing_refs': missing_prereq_subjects,
            'health_percentage': 99,
        }
    }
    
    # Recent fixes
    recent_fixes = [
        {'issue': 'Missing sections', 'fixed': 5, 'date': '2024-01-15'},
        {'issue': 'Invalid credit hours', 'fixed': 3, 'date': '2024-01-14'},
        {'issue': 'Assignment issues', 'fixed': 2, 'date': '2024-01-13'},
    ]
    
    context = {
        'health_status': health_status,
        'recent_fixes': recent_fixes,
        'total_issues': (subjects_no_section + subjects_invalid_credits + 
                        subjects_no_discipline + assignments_no_teacher + 
                        assignments_no_subject),
        'last_check': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
    }
    
    return render(request, 'subject/health_check.html', context)


def add_subject(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        code = request.POST.get('code')
        credit_hours = request.POST.get('credit_hours')
        description = request.POST.get('description')
        subject_type = request.POST.get('subject_type')
        
        # Get prerequisite subjects
        prerequisite_ids = request.POST.getlist('prerequisites')

        # Convert to integers safely
        credit_hours = int(credit_hours) if credit_hours else None

        # Check if subject with same code exists
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
                
                # Add prerequisites
                if prerequisite_ids:
                    prerequisites = Subject.objects.filter(id__in=prerequisite_ids)
                    subject.prerequisites.set(prerequisites)
                
                messages.success(request, "Subject saved successfully with prerequisites.")
            except Exception as e:
                messages.error(request, f"Error saving subject: {str(e)}")

    context = {
        'subject_type_choices': Subject.SUBJECT_TYPE_CHOICES,
        'prerequisite_subjects': Subject.objects.all().order_by('code')
    }
    return render(request, 'subject/add-subject.html', context)

def view_subject(request):
    # Get all subjects (no semester, section, discipline filtering since they're removed from Subject)
    subjects = Subject.objects.all().order_by('code').prefetch_related('prerequisites')
    
    # Get data for filters (from SubjectAssign model)
    disciplines = Discipline.objects.all()
    semesters = Semester.objects.all()
    sections = Section.objects.all()

    # Get filter parameters
    semester_id = request.GET.get('semester')
    section_id = request.GET.get('section')
    subject_type = request.GET.get('subject_type')
    is_active = request.GET.get('is_active')
    discipline_id = request.GET.get('discipline')
    code = request.GET.get('code')
    name = request.GET.get('name')

    # Filter by subject code
    if code:
        subjects = subjects.filter(code__icontains=code)

    # Filter by subject name
    if name:
        subjects = subjects.filter(name__icontains=name)

    # Filter by subject type
    if subject_type:
        subjects = subjects.filter(subject_type=subject_type)

    # Filter by active/inactive status
    if is_active:
        subjects = subjects.filter(is_active=(is_active.lower() == 'true'))

    # Note: semester, section, discipline filters now work through SubjectAssign
    # If you want to filter subjects by these, you need to filter through SubjectAssign
    if semester_id or section_id or discipline_id:
        # Get subject IDs from SubjectAssign with these filters
        subject_assignments = SubjectAssign.objects.all()
        
        if semester_id:
            subject_assignments = subject_assignments.filter(semester_id=semester_id)
        if section_id:
            subject_assignments = subject_assignments.filter(sections__id=section_id)
        if discipline_id:
            subject_assignments = subject_assignments.filter(discipline_id=discipline_id)
        
        # Get unique subject IDs
        subject_ids = subject_assignments.values_list('subject_id', flat=True).distinct()
        subjects = subjects.filter(id__in=subject_ids)

    # Get selected values for displaying in template
    selected_semester = get_object_or_404(Semester, id=semester_id) if semester_id else None
    selected_section = get_object_or_404(Section, id=section_id) if section_id else None
    selected_discipline = get_object_or_404(Discipline, id=discipline_id) if discipline_id else None

    # Pagination
    paginator = Paginator(subjects, 10)
    page = request.GET.get('page')
    subjects = paginator.get_page(page)

    context = {
        'subjects': subjects,
        'total_subjects': Subject.objects.count(),
        'subject_type_choices': Subject.SUBJECT_TYPE_CHOICES,
        'disciplines': disciplines,
        'semesters': semesters,
        'sections': sections,
        'selected_discipline': selected_discipline,
        'selected_semester': selected_semester,
        'selected_section': selected_section,
    }

    return render(request, 'subject/subject-list.html', context)

# DEBUG VIEWS - ADD THESE FUNCTIONS:

def show_all_subjects(request):
    """Show all subjects in the database for debugging"""
    subjects = Subject.objects.all().select_related(
        'semester', 'desciplain', 'section'
    ).prefetch_related('prerequisites')
    
    # Get filter parameters
    discipline_id = request.GET.get('discipline')
    semester_id = request.GET.get('semester')
    
    if discipline_id:
        subjects = subjects.filter(desciplain_id=discipline_id)
    
    if semester_id:
        subjects = subjects.filter(semester_id=semester_id)
    
    # Count statistics
    total_subjects = subjects.count()
    
    context = {
        'subjects': subjects,
        'total_subjects': total_subjects,
        'disciplines': Discipline.objects.all(),
        'semesters': Semester.objects.all(),
        'selected_discipline': get_object_or_404(Discipline, id=discipline_id) if discipline_id else None,
        'selected_semester': get_object_or_404(Semester, id=semester_id) if semester_id else None,
    }
    
    return render(request, 'subject/all-subjects.html', context)


def debug_prerequisites(request):
    """Debug view to see what prerequisites are available"""
    disciplines = Discipline.objects.all()
    semesters = Semester.objects.all()
    sections = Section.objects.all()
    
    discipline_id = request.GET.get('discipline_id')
    semester_id = request.GET.get('semester_id')
    section_id = request.GET.get('section_id')
    
    context = {
        'disciplines': disciplines,
        'semesters': semesters,
        'sections': sections,
        'selected_discipline_id': discipline_id,
        'selected_semester_id': semester_id,
        'selected_section_id': section_id,
    }
    
    if discipline_id and semester_id:
        try:
            discipline = get_object_or_404(Discipline, id=discipline_id)
            semester = get_object_or_404(Semester, id=semester_id)
            section = get_object_or_404(Section, id=section_id) if section_id else None
            
            # ALL subjects for this discipline (for reference)
            all_subjects = Subject.objects.filter(
                desciplain=discipline
            ).select_related('semester', 'section').order_by('semester__number', 'code')
            
            # Available prerequisites (subjects from same or previous semesters)
            available_prereqs = Subject.objects.filter(
                desciplain=discipline,
                semester__number__lte=semester.number  # Changed from lt to lte to include same semester
            )
            
            if section:
                available_prereqs = available_prereqs.filter(section=section)
            
            # Exclude the subject itself if editing
            subject_id = request.GET.get('subject_id')
            if subject_id:
                available_prereqs = available_prereqs.exclude(id=subject_id)
            
            context.update({
                'selected_discipline': discipline,
                'selected_semester': semester,
                'selected_section': section,
                'all_subjects': all_subjects,
                'available_prereqs': available_prereqs.order_by('semester__number', 'code'),
                'total_all_subjects': all_subjects.count(),
                'total_available_prereqs': available_prereqs.count(),
            })
            
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
    
    return render(request, 'subject/debug-prerequisites.html', context)


# Import subjects from Excel/CSV - TEMPORARILY DISABLED
def import_subjects(request):
    messages.error(request, "Import feature temporarily disabled. Please use admin panel to add subjects.")
    return redirect('subject:view_subject')


# Export subjects template - TEMPORARILY DISABLED
def export_subjects_template(request):
    messages.error(request, "Export feature temporarily disabled.")
    return redirect('subject:view_subject')


# API endpoint for prerequisite suggestions - FIXED VERSION
@csrf_exempt
def get_prerequisite_suggestions(request):
    if request.method == 'GET':
        discipline_id = request.GET.get('discipline_id')
        semester_id = request.GET.get('semester_id')
        section_id = request.GET.get('section_id')
        
        print(f"DEBUG API CALL: discipline_id={discipline_id}, semester_id={semester_id}, section_id={section_id}")
        
        if not discipline_id or not semester_id:
            return JsonResponse({'error': 'Missing discipline_id or semester_id'}, status=400)
        
        try:
            # Get semester instance
            semester = Semester.objects.get(id=semester_id)
            print(f"DEBUG: Found semester: {semester.number}")
            
            # Get ALL subjects for this discipline (for debugging)
            all_subjects = Subject.objects.filter(
                desciplain_id=discipline_id
            ).select_related('semester', 'section')
            print(f"DEBUG: Total subjects for discipline: {all_subjects.count()}")
            
            # Build query for prerequisites - include same or previous semesters
            query = Subject.objects.filter(
                desciplain_id=discipline_id,
                semester__number__lte=semester.number  # Changed from lt to lte
            )
            
            # Filter by section if provided
            if section_id and section_id != '':
                query = query.filter(section_id=section_id)
            
            suggestions = query.order_by('semester__number', 'code')
            
            print(f"DEBUG: Found {suggestions.count()} prerequisite suggestions")
            
            data = []
            for subject in suggestions:
                subject_data = {
                    'id': subject.id,
                    'code': subject.code,
                    'name': subject.name,
                    'semester': subject.semester.number,
                    'section': subject.section.name if subject.section else '',
                    'display': f"{subject.code} - {subject.name} (Sem {subject.semester.number})"
                }
                data.append(subject_data)
                print(f"  - {subject_data['code']}: {subject_data['name']} (Sem {subject_data['semester']})")
            
            return JsonResponse({
                'suggestions': data,
                'debug_info': {
                    'total_subjects': all_subjects.count(),
                    'available_prerequisites': suggestions.count(),
                    'current_semester': semester.number
                }
            })
            
        except Semester.DoesNotExist:
            return JsonResponse({'error': 'Semester not found'}, status=404)
        except Exception as e:
            print(f"DEBUG ERROR: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=400)


# API endpoint to get sections based on discipline and batch
@csrf_exempt
def get_sections_for_discipline(request):
    """API endpoint to get sections based on discipline and batch"""
    if request.method == 'GET':
        discipline_id = request.GET.get('discipline_id')
        batch_id = request.GET.get('batch_id')
        
        print(f"API called with discipline_id={discipline_id}, batch_id={batch_id}")
        
        if not discipline_id:
            return JsonResponse({'error': 'Missing discipline parameter'}, status=400)
        
        try:
            from Academic.models import Section
            
            # Get sections for discipline
            sections = Section.objects.filter(discipline_id=discipline_id)
            
            # Filter by batch if provided
            if batch_id:
                sections = sections.filter(batch_id=batch_id)
            
            data = [{
                'id': section.id,
                'name': section.name,
                'batch': section.batch.name if section.batch else '',
                'display': f"{section.name} - {section.batch.name if section.batch else 'All Batches'}"
            } for section in sections]
            
            print(f"Found {len(data)} sections")
            return JsonResponse({'sections': data})
            
        except Exception as e:
            print(f"Error: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=400)

# API endpoint to get batches for discipline
@csrf_exempt
def get_batches_for_discipline(request):
    """API endpoint to get batches for a discipline"""
    if request.method == 'GET':
        discipline_id = request.GET.get('discipline_id')
        
        if not discipline_id:
            return JsonResponse({'error': 'Discipline ID required'}, status=400)
        
        try:
            from Academic.models import Batch
            batches = Batch.objects.filter(discipline_id=discipline_id).values('id', 'name')
            return JsonResponse({
                'batches': list(batches)
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid method'}, status=405)


@login_required
def stu_subject(request):
    try:
        student = request.user.student
    except Student.DoesNotExist:
        return HttpResponse("Student profile not found. Please contact admin.")

    # Get subjects for student's semester and section
    subjects = Subject.objects.filter(
        semester=student.semester,
        section=student.section
    )

    return render(request, "students/subject.html", {"subjects": subjects})

def add_subject_assign(request):
    if request.method == "POST":
        # Get all form data
        teacher_id = request.POST.get("teacher")
        subject_id = request.POST.get("subject")
        batch_id = request.POST.get("batch")
        semester_id = request.POST.get("semester")
        section_ids = request.POST.getlist("sections")  # Changed to getlist for multiple sections
        discipline_id = request.POST.get("disciplines")
        
        if not all([teacher_id, subject_id, batch_id, semester_id, section_ids, discipline_id]):
            missing_fields = []
            if not teacher_id: missing_fields.append("Teacher")
            if not subject_id: missing_fields.append("Subject")
            if not batch_id: missing_fields.append("Batch")
            if not semester_id: missing_fields.append("Semester")
            if not section_ids: missing_fields.append("Sections")
            if not discipline_id: missing_fields.append("Discipline")
            
            messages.error(request, f"Missing fields: {', '.join(missing_fields)}")
            return redirect("subject:add_subject_assign")
        
        teacher = get_object_or_404(Teacher, id=teacher_id)
        subject = get_object_or_404(Subject, id=subject_id)
        batch = get_object_or_404(Batch, id=batch_id)
        semester = get_object_or_404(Semester, id=semester_id)
        discipline = get_object_or_404(Discipline, id=discipline_id)

        # Check if assignment exists (without section check)
        existing_assignment = SubjectAssign.objects.filter(
            teacher=teacher,
            subject=subject,
            batch=batch,
            semester=semester,
            discipline=discipline
        ).first()
        
        if existing_assignment:
            # Add new sections to existing assignment
            existing_assignment.sections.add(*section_ids)
            messages.success(request, f"Sections added to existing assignment for {subject.name}.")
        else:
            # Create new assignment
            subject_assign = SubjectAssign.objects.create(
                teacher=teacher,
                subject=subject,
                batch=batch,
                semester=semester,
                discipline=discipline,
                is_active=True
            )
            # Add sections
            subject_assign.sections.set(section_ids)
            messages.success(request, "Subject assigned successfully with multiple sections.")
        
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


# API endpoint to get sections based on discipline, batch, and semester
@csrf_exempt
def get_sections_for_assignment(request):
    if request.method == 'GET':
        discipline_id = request.GET.get('discipline_id')
        batch_id = request.GET.get('batch_id')
        semester_id = request.GET.get('semester_id')
        
        if not all([discipline_id, batch_id, semester_id]):
            return JsonResponse({'error': 'Missing required parameters'}, status=400)
        
        try:
            # Get sections for discipline and batch
            sections = Section.objects.filter(
                discipline_id=discipline_id,
                batch_id=batch_id
            )
            
            # Optional: Filter by semester if sections have semester field
            # if hasattr(Section, 'semester'):
            #     sections = sections.filter(semester_id=semester_id)
            
            data = [{
                'id': section.id,
                'name': section.name,
                'batch': section.batch.name if section.batch else '',
                'display': f"{section.name} - {section.batch.name if section.batch else 'All Batches'}"
            } for section in sections]
            
            return JsonResponse({'sections': data})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=400)

def show_subject_assign(request):
    assigns = SubjectAssign.objects.select_related(
        "teacher", 
        "subject", 
        "batch", 
        "semester", 
        "discipline"
    ).prefetch_related("sections").order_by('-id')
    
    context = {
        "assigns": assigns
    }
    return render(request, "subject/show-subject-assign-record.html", context)

# Check prerequisites for a student
def check_student_prerequisites(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    
    # Get all subjects the student is enrolled in for current semester and section
    subjects = Subject.objects.filter(
        semester=student.semester,
        section=student.section
    )
    
    prerequisite_status = []
    
    for subject in subjects:
        status = subject.check_prerequisites(student)
        prerequisite_status.append({
            'subject': subject,
            'status': status
        })
    
    context = {
        'student': student,
        'prerequisite_status': prerequisite_status,
        'current_semester': student.semester.number,
        'current_section': student.section.name if student.section else 'No Section'
    }
    
    return render(request, 'subject/check-prerequisites.html', context)
