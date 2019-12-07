# timetables/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db import models
from django.db.models import Q, Count
from django.core.paginator import Paginator
from datetime import datetime, timedelta, date, time
from calendar import day_name
import json

from .models import (
    TimeSlot, Classroom, TeacherAvailability, 
    TimetableEntry, TimetableGenerationRequest, ExamTimetable
)
from teachers.models import Teacher
from Academic.models import Section, Batch, Semester
from subject.models import Subject, SubjectAssign

# ==================== HELPER FUNCTIONS ====================
def is_admin(user):
    """Check if user is admin or superuser"""
    try:
        return user.is_superuser or (hasattr(user, 'role') and user.role == 'admin')
    except AttributeError:
        return user.is_superuser

def is_teacher(user):
    """Check if user is a teacher"""
    try:
        return hasattr(user, 'teacher') or (hasattr(user, 'role') and user.role == 'teacher')
    except AttributeError:
        return hasattr(user, 'teacher')

def is_student(user):
    """Check if user is a student"""
    try:
        return hasattr(user, 'student') or (hasattr(user, 'role') and user.role == 'student')
    except AttributeError:
        return hasattr(user, 'student')


# ==================== TEACHER TIMETABLE VIEWS ====================
@login_required
@user_passes_test(is_teacher)
def teacher_timetable_view(request, teacher_id=None):
    """View timetable for a specific teacher"""
    if teacher_id:
        teacher = get_object_or_404(Teacher, id=teacher_id)
    else:
        teacher = request.user.teacher
    
    # Get timetable entries for this teacher
    timetable_entries = TimetableEntry.objects.filter(
        teacher=teacher,
        is_active=True
    ).select_related('subject', 'section', 'batch', 'semester', 'time_slot', 'classroom')
    
    # Get all time slots for the timetable grid
    time_slots = TimeSlot.objects.filter(is_active=True).order_by('start_time')
    
    # Days of the week
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    
    context = {
        'teacher': teacher,
        'timetable_entries': timetable_entries,
        'time_slots': time_slots,
        'days': days,
    }
    
    return render(request, 'timetables/teacher_timetable.html', context)


# ==================== SECTION TIMETABLE VIEWS ====================
# timetables/views.py - Update section_timetable_view

@login_required
def section_timetable_view(request, section_id):
    """View timetable for a specific section"""
    section = get_object_or_404(Section, id=section_id)
    
    # Get timetable entries for this section (both theory and lab)
    timetable_entries = TimetableEntry.objects.filter(
        section=section,
        is_active=True
    ).select_related('teacher', 'subject', 'batch', 'semester', 'time_slot', 'classroom')
    
    # Get lab entries for this section (if any)
    from .models import Laboratory
    labs = Laboratory.objects.filter(sections=section, is_active=True)
    for lab in labs:
        lab_entries = TimetableEntry.objects.filter(
            classroom__room_number__icontains=lab.lab_code,
            is_active=True
        ).select_related('teacher', 'subject', 'batch', 'semester', 'time_slot', 'classroom')
        timetable_entries = timetable_entries | lab_entries
    
    # Organize by day
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    timetable_by_day = {}
    
    for day in days:
        timetable_by_day[day] = timetable_entries.filter(
            time_slot__day=day
        ).order_by('time_slot__start_time')
    
    # Get all time slots for the timetable grid
    time_slots = TimeSlot.objects.filter(is_active=True).order_by('start_time')
    
    # Get upcoming exams for this section
    upcoming_exams = ExamTimetable.objects.filter(
        section=section,
        is_active=True,
        exam_date__gte=date.today()
    ).select_related('subject', 'teacher', 'classroom')[:5]
    
    context = {
        'section': section,
        'timetable_entries': timetable_entries,
        'timetable_by_day': timetable_by_day,
        'time_slots': time_slots,
        'days': days,
        'upcoming_exams': upcoming_exams,
        'today': date.today(),
    }
    
    return render(request, 'timetables/section_timetable.html', context)
# ==================== TEACHER LIST FOR GENERATION ====================
@login_required
@user_passes_test(is_admin)
def teacher_list_for_generate(request):
    """Show list of all teachers with their assigned subjects for timetable generation"""
    teachers = Teacher.objects.filter(is_active=True)
    
    # Get assigned subjects for each teacher
    teachers_with_subjects = []
    for teacher in teachers:
        assigned_subjects = SubjectAssign.objects.filter(
            teacher=teacher,
            is_active=True
        ).select_related('subject', 'batch', 'semester').prefetch_related('sections')
        
        if assigned_subjects.exists():
            teachers_with_subjects.append({
                'teacher': teacher,
                'assigned_subjects': assigned_subjects,
                'subject_count': assigned_subjects.count()
            })
    
    context = {
        'teachers_with_subjects': teachers_with_subjects,
    }
    
    return render(request, 'timetables/teacher_list_for_generate.html', context)


# ==================== GENERATE TEACHER TIMETABLE ====================
@login_required
@user_passes_test(is_admin)
def generate_teacher_timetable(request, teacher_id):
    """Generate timetable for a specific teacher"""
    teacher = get_object_or_404(Teacher, id=teacher_id)
    
    if request.method == 'POST':
        # Create generation request
        first_assignment = SubjectAssign.objects.filter(
            teacher=teacher,
            is_active=True
        ).first()
        
        if not first_assignment:
            messages.error(request, f'No subjects assigned to {teacher}')
            return redirect('timetables:generate_teacher_list')
        
        # Create generation request with required fields
        generation_request = TimetableGenerationRequest.objects.create(
            teacher=teacher,
            batch=first_assignment.batch,
            semester=first_assignment.semester,
            status='pending'
        )
        
        try:
            # Get all subjects assigned to this teacher
            assigned_subjects = SubjectAssign.objects.filter(
                teacher=teacher,
                is_active=True
            ).select_related('subject', 'batch', 'semester')
            
            if not assigned_subjects.exists():
                messages.warning(request, f'No subjects assigned to {teacher}')
                generation_request.status = 'failed'
                generation_request.error_message = 'No subjects assigned'
                generation_request.save()
                return redirect('timetables:generate_teacher_list')
            
            # Generate timetable entries
            generated_count = auto_generate_timetable_for_teacher(teacher, assigned_subjects)
            
            generation_request.status = 'completed'
            generation_request.completed_at = timezone.now()
            generation_request.save()
            
            messages.success(request, f'Timetable generated successfully! {generated_count} entries created for {teacher.first_name} {teacher.last_name}.')
            
        except Exception as e:
            generation_request.status = 'failed'
            generation_request.error_message = str(e)
            generation_request.save()
            messages.error(request, f'Error generating timetable: {str(e)}')
        
        return redirect('timetables:teacher_timetable', teacher_id=teacher.id)
    
    # GET request - show confirmation page
    assigned_subjects = SubjectAssign.objects.filter(
        teacher=teacher,
        is_active=True
    ).select_related('subject', 'batch', 'semester').prefetch_related('sections')
    
    # Group subjects by batch and semester for better display
    subjects_by_batch = {}
    for assignment in assigned_subjects:
        key = f"{assignment.batch.name} - Semester {assignment.semester.number}"
        if key not in subjects_by_batch:
            subjects_by_batch[key] = []
        subjects_by_batch[key].append(assignment)
    
    context = {
        'teacher': teacher,
        'assigned_subjects': assigned_subjects,
        'subjects_by_batch': subjects_by_batch,
        'total_subjects': assigned_subjects.count(),
    }
    
    return render(request, 'timetables/generate_timetable.html', context)


# ==================== GENERATE SECTION TIMETABLE ====================
@login_required
@user_passes_test(is_admin)
def generate_section_timetable(request, section_id):
    """Generate timetable for a specific section"""
    section = get_object_or_404(Section, id=section_id)
    
    if request.method == 'POST':
        batch_id = request.POST.get('batch')
        semester_id = request.POST.get('semester')
        
        batch = get_object_or_404(Batch, id=batch_id)
        semester = get_object_or_404(Semester, id=semester_id)
        
        # Create generation request
        generation_request = TimetableGenerationRequest.objects.create(
            section=section,
            batch=batch,
            semester=semester,
            status='pending'
        )
        
        try:
            # Get subjects for this section
            subjects = Subject.objects.filter(
                section=section,
                semester=semester,
                is_active=True
            ).select_related('desciplain')
            
            if not subjects.exists():
                messages.warning(request, f'No subjects assigned to section {section}')
                generation_request.status = 'failed'
                generation_request.error_message = 'No subjects assigned'
                generation_request.save()
                return redirect('section_detail', section_id=section.id)
            
            # Generate timetable entries
            generated_count = auto_generate_timetable_for_section(section, batch, semester, subjects)
            
            generation_request.status = 'completed'
            generation_request.completed_at = timezone.now()
            generation_request.save()
            
            messages.success(request, f'Timetable generated successfully! {generated_count} entries created.')
            
        except Exception as e:
            generation_request.status = 'failed'
            generation_request.error_message = str(e)
            generation_request.save()
            messages.error(request, f'Error generating timetable: {str(e)}')
        
        return redirect('section_timetable', section_id=section.id)
    
    # Get batches and semesters for this section
    batches = Batch.objects.filter(section__id=section_id).distinct()
    semesters = Semester.objects.all()
    
    context = {
        'section': section,
        'batches': batches,
        'semesters': semesters,
    }
    
    return render(request, 'timetables/generate_section_timetable.html', context)


# timetables/views.py - Add this function

@login_required
@user_passes_test(is_admin)
def edit_timetable_entry(request, entry_id):
    """Edit an existing timetable entry"""
    entry = get_object_or_404(TimetableEntry, id=entry_id)
    
    if request.method == 'POST':
        # Get form data
        teacher_id = request.POST.get('teacher')
        subject_id = request.POST.get('subject')
        section_id = request.POST.get('section')
        batch_id = request.POST.get('batch')
        semester_id = request.POST.get('semester')
        time_slot_id = request.POST.get('time_slot')
        classroom_id = request.POST.get('classroom')
        is_exam = request.POST.get('is_exam') == 'on'
        exam_type = request.POST.get('exam_type', '')
        is_active = request.POST.get('is_active') == 'on'
        
        # Get objects
        teacher = get_object_or_404(Teacher, id=teacher_id)
        subject = get_object_or_404(Subject, id=subject_id)
        section = get_object_or_404(Section, id=section_id)
        batch = get_object_or_404(Batch, id=batch_id)
        semester = get_object_or_404(Semester, id=semester_id)
        time_slot = get_object_or_404(TimeSlot, id=time_slot_id)
        classroom = get_object_or_404(Classroom, id=classroom_id)
        
        # Check for conflicts (excluding current entry)
        if TimetableEntry.objects.filter(
            teacher=teacher, time_slot=time_slot, is_active=True
        ).exclude(id=entry.id).exists():
            messages.error(request, 'Teacher already has a class at this time slot!')
            return redirect('timetables:edit_timetable_entry', entry_id=entry.id)
        
        if TimetableEntry.objects.filter(
            section=section, time_slot=time_slot, is_active=True
        ).exclude(id=entry.id).exists():
            messages.error(request, 'Section already has a class at this time slot!')
            return redirect('timetables:edit_timetable_entry', entry_id=entry.id)
        
        if TimetableEntry.objects.filter(
            classroom=classroom, time_slot=time_slot, is_active=True
        ).exclude(id=entry.id).exists():
            messages.error(request, 'Classroom is already booked at this time slot!')
            return redirect('timetables:edit_timetable_entry', entry_id=entry.id)
        
        # Update entry
        entry.teacher = teacher
        entry.subject = subject
        entry.section = section
        entry.batch = batch
        entry.semester = semester
        entry.time_slot = time_slot
        entry.classroom = classroom
        entry.is_exam = is_exam
        entry.exam_type = exam_type if is_exam else ''
        entry.is_active = is_active
        entry.save()
        
        messages.success(request, 'Timetable entry updated successfully!')
        return redirect('timetables:teacher_timetable', teacher_id=teacher.id)
    
    # GET request - show edit form
    teachers = Teacher.objects.filter(is_active=True)
    subjects = Subject.objects.filter(is_active=True)
    sections = Section.objects.all()
    batches = Batch.objects.all()
    semesters = Semester.objects.all()
    time_slots = TimeSlot.objects.filter(is_active=True)
    classrooms = Classroom.objects.filter(is_active=True)
    
    context = {
        'entry': entry,
        'teachers': teachers,
        'subjects': subjects,
        'sections': sections,
        'batches': batches,
        'semesters': semesters,
        'time_slots': time_slots,
        'classrooms': classrooms,
    }
    
    return render(request, 'timetables/edit_timetable_entry.html', context)
    # ==================== AUTO GENERATION FUNCTIONS ====================

def auto_generate_timetable_for_teacher(teacher, assigned_subjects):
    """Automatically generate timetable for a teacher with proper lab support"""
    generated_count = 0
    
    # Get all time slots
    all_time_slots = list(TimeSlot.objects.filter(is_active=True).order_by('day', 'start_time'))
    
    # Get teacher's availability
    teacher_availability = TeacherAvailability.objects.filter(
        teacher=teacher,
        is_available=True
    )
    
    # Get existing timetable entries to avoid conflicts
    existing_entries = TimetableEntry.objects.filter(teacher=teacher)
    
    # Get all laboratories
    from .models import Laboratory
    all_labs = list(Laboratory.objects.filter(is_active=True))
    print(f"Available laboratories: {len(all_labs)}")
    for lab in all_labs:
        print(f"  - {lab.lab_code}: {lab.lab_name} (Capacity: {lab.capacity}, Computers: {lab.computer_count})")
    
    for assignment in assigned_subjects:
        subject = assignment.subject
        batch = assignment.batch
        semester = assignment.semester
        sections = assignment.sections.all()
        
        # Calculate number of classes needed based on credit hours
        credit_hours = subject.credit_hours
        
        # Determine theory and lab split
        if credit_hours == 6:
            theory_classes = 3
            lab_classes = 3
            needs_lab = True
        elif credit_hours == 4:
            theory_classes = 3
            lab_classes = 1
            needs_lab = True
        elif credit_hours == 3:
            theory_classes = 3
            lab_classes = 0
            needs_lab = False
        elif credit_hours == 2:
            theory_classes = 2
            lab_classes = 0
            needs_lab = False
        elif credit_hours == 1:
            theory_classes = 1
            lab_classes = 0
            needs_lab = False
        else:
            theory_classes = credit_hours
            lab_classes = 0
            needs_lab = False
        
        print(f"\nProcessing {subject.code} - Credit Hours: {credit_hours}, Theory: {theory_classes}, Lab: {lab_classes}")
        
        for section in sections:
            # ========== GET THEORY CLASSROOM ==========
            theory_classroom = Classroom.objects.filter(
                section=section,
                is_active=True,
                is_lab=False
            ).first()
            
            if not theory_classroom:
                theory_classroom = Classroom.objects.filter(
                    batch=section.batch,
                    is_active=True,
                    is_lab=False
                ).first()
            
            if not theory_classroom:
                theory_classroom = Classroom.objects.filter(is_active=True, is_lab=False).first()
            
            if not theory_classroom:
                print(f"Warning: No theory classroom available for section {section.name}")
                continue
            
            # ========== GET LABORATORY FOR LAB CLASSES ==========
            selected_lab = None
            
            if needs_lab and lab_classes > 0:
                # Try to get lab associated with this section
                selected_lab = Laboratory.objects.filter(
                    sections=section,
                    is_active=True
                ).first()
                
                # Try lab associated with batch
                if not selected_lab:
                    selected_lab = Laboratory.objects.filter(
                        batches=section.batch,
                        is_active=True
                    ).first()
                
                # Try lab associated with discipline
                if not selected_lab:
                    selected_lab = Laboratory.objects.filter(
                        disciplines=section.discipline,
                        is_active=True
                    ).first()
                
                # Try primary lab for section
                if not selected_lab:
                    selected_lab = Laboratory.objects.filter(
                        primary_section=section,
                        is_active=True
                    ).first()
                
                # Try any lab
                if not selected_lab:
                    selected_lab = Laboratory.objects.filter(is_active=True).first()
                
                if selected_lab:
                    print(f"  Using LABORATORY: {selected_lab.lab_code} - {selected_lab.lab_name} for {subject.code}")
                else:
                    print(f"  Warning: No laboratory available for {subject.code}, using theory classroom")
            
            # ========== FIND AVAILABLE TIME SLOTS ==========
            available_slots = []
            for time_slot in all_time_slots:
                if teacher_availability.exists():
                    is_available = teacher_availability.filter(
                        day=time_slot.day,
                        start_time__lte=time_slot.start_time,
                        end_time__gte=time_slot.end_time
                    ).exists()
                    if not is_available:
                        continue
                
                if existing_entries.filter(time_slot=time_slot).exists():
                    continue
                
                if TimetableEntry.objects.filter(section=section, time_slot=time_slot).exists():
                    continue
                
                if TimetableEntry.objects.filter(classroom=theory_classroom, time_slot=time_slot).exists():
                    continue
                
                available_slots.append(time_slot)
            
            import random
            random.shuffle(available_slots)
            
            used_slots = []
            theory_created = 0
            lab_created = 0
            
            # Create theory classes
            for time_slot in available_slots:
                if theory_created >= theory_classes:
                    break
                if time_slot.id in used_slots:
                    continue
                
                TimetableEntry.objects.create(
                    teacher=teacher,
                    subject=subject,
                    section=section,
                    batch=batch,
                    semester=semester,
                    time_slot=time_slot,
                    classroom=theory_classroom,
                    is_exam=False,
                    is_active=True
                )
                used_slots.append(time_slot.id)
                theory_created += 1
                generated_count += 1
                print(f"  Theory: {subject.code} on {time_slot.day} at {time_slot.start_time} in {theory_classroom.room_number}")
            
            # Create lab classes using Laboratory model
            if selected_lab and lab_classes > 0:
                # Get or create a classroom representation for the lab
                lab_classroom = Classroom.objects.filter(
                    room_number=selected_lab.lab_code
                ).first()
                
                if not lab_classroom:
                    # Create a temporary classroom for the lab
                    lab_classroom = Classroom.objects.create(
                        room_number=selected_lab.lab_code,
                        building=selected_lab.building,
                        capacity=selected_lab.capacity,
                        has_projector=selected_lab.has_projector,
                        has_smartboard=selected_lab.has_smartboard,
                        is_lab=True,
                        is_active=True
                    )
                    print(f"  Created classroom record for lab: {lab_classroom.room_number}")
                
                # Prefer afternoon slots for labs
                lab_available_slots = []
                for time_slot in available_slots:
                    if time_slot.id in used_slots:
                        continue
                    if time_slot.start_time.hour >= 12:
                        lab_available_slots.insert(0, time_slot)
                    else:
                        lab_available_slots.append(time_slot)
                
                for time_slot in lab_available_slots:
                    if lab_created >= lab_classes:
                        break
                    if time_slot.id in used_slots:
                        continue
                    
                    if TimetableEntry.objects.filter(classroom=lab_classroom, time_slot=time_slot).exists():
                        continue
                    
                    TimetableEntry.objects.create(
                        teacher=teacher,
                        subject=subject,
                        section=section,
                        batch=batch,
                        semester=semester,
                        time_slot=time_slot,
                        classroom=lab_classroom,
                        is_exam=False,
                        is_active=True
                    )
                    used_slots.append(time_slot.id)
                    lab_created += 1
                    generated_count += 1
                    print(f"  LAB: {subject.code} on {time_slot.day} at {time_slot.start_time} in {selected_lab.lab_code} - {selected_lab.lab_name}")
            
            print(f"Summary for {subject.code} in {section.name}: {theory_created} theory, {lab_created} lab classes")
    
    return generated_count
def get_lab_for_section(section):
    """Get the appropriate lab for a section based on associations"""
    from .models import Laboratory
    
    # Check if section has a directly assigned lab
    lab = Laboratory.objects.filter(
        sections=section,
        is_active=True
    ).first()
    
    if lab:
        return lab
    
    # Check if section's batch has an assigned lab
    lab = Laboratory.objects.filter(
        batches=section.batch,
        is_active=True
    ).first()
    
    if lab:
        return lab
    
    # Check if section's discipline has an assigned lab
    lab = Laboratory.objects.filter(
        disciplines=section.discipline,
        is_active=True
    ).first()
    
    if lab:
        return lab
    
    # Check if section is primary for any lab
    lab = Laboratory.objects.filter(
        primary_section=section,
        is_active=True
    ).first()
    
    if lab:
        return lab
    
    # Return any available lab
    return Laboratory.objects.filter(is_active=True).first()
def auto_generate_timetable_for_section(section, batch, semester, subjects):
    """Automatically generate timetable for a section"""
    generated_count = 0
    
    # Get all time slots
    time_slots = TimeSlot.objects.filter(is_active=True)
    
    # Get existing timetable entries for this section
    existing_entries = TimetableEntry.objects.filter(section=section)
    
    for subject in subjects:
        # Get teacher assigned to this subject
        subject_assign = SubjectAssign.objects.filter(
            subject=subject,
            batch=batch,
            semester=semester,
            sections=section,
            is_active=True
        ).first()
        
        if not subject_assign or not subject_assign.teacher:
            continue
        
        teacher = subject_assign.teacher
        
        # Check teacher availability
        teacher_availability = TeacherAvailability.objects.filter(
            teacher=teacher,
            is_available=True
        )
        
        for time_slot in time_slots:
            # Check teacher availability
            if teacher_availability.exists():
                is_available = teacher_availability.filter(
                    day=time_slot.day,
                    start_time__lte=time_slot.start_time,
                    end_time__gte=time_slot.end_time
                ).exists()
                
                if not is_available:
                    continue
            
            # Check if teacher already has class
            teacher_busy = TimetableEntry.objects.filter(
                teacher=teacher,
                time_slot=time_slot
            ).exists()
            
            if teacher_busy:
                continue
            
            # Check if section already has class at this time
            section_busy = existing_entries.filter(
                time_slot=time_slot
            ).exists()
            
            if section_busy:
                continue
            
            # Find available classroom
            classroom = Classroom.objects.filter(is_active=True).first()
            
            if not classroom:
                continue
            
            # Create timetable entry
            TimetableEntry.objects.create(
                teacher=teacher,
                subject=subject,
                section=section,
                batch=batch,
                semester=semester,
                time_slot=time_slot,
                classroom=classroom,
                is_active=True
            )
            
            generated_count += 1
            break
    
    return generated_count

def get_lab_display_name(lab):
    """Get display name for laboratory"""
    if lab:
        return f"{lab.lab_code} - {lab.lab_name} ({lab.building})"
    return "No Lab Assigned"

# ==================== AJAX ENDPOINTS ====================
@login_required
@user_passes_test(is_admin)
def get_teacher_subjects(request):
    """AJAX endpoint to get teacher subjects for selected batch and semester"""
    teacher_id = request.GET.get('teacher_id')
    batch_id = request.GET.get('batch_id')
    semester_id = request.GET.get('semester_id')
    
    if teacher_id and batch_id and semester_id:
        assignments = SubjectAssign.objects.filter(
            teacher_id=teacher_id,
            batch_id=batch_id,
            semester_id=semester_id,
            is_active=True
        ).select_related('subject')
        
        subjects_data = []
        for assignment in assignments:
            sections_data = [{'id': s.id, 'name': s.name} for s in assignment.sections.all()]
            subjects_data.append({
                'id': assignment.subject.id,
                'code': assignment.subject.code,
                'name': assignment.subject.name,
                'sections': sections_data
            })
        
        return JsonResponse({'subjects': subjects_data})
    
    return JsonResponse({'subjects': []})


# ==================== TIME SLOT MANAGEMENT ====================
@login_required
@user_passes_test(is_admin)
def time_slot_list(request):
    """List all time slots"""
    time_slots = TimeSlot.objects.all().order_by('day', 'start_time')
    
    # Group by day for better display
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    time_slots_by_day = {}
    for day in days:
        time_slots_by_day[day] = time_slots.filter(day=day)
    
    context = {
        'time_slots': time_slots,
        'time_slots_by_day': time_slots_by_day,
        'days': days,
    }
    
    return render(request, 'timetables/time_slot_list.html', context)


@login_required
@user_passes_test(is_admin)
def time_slot_create(request):
    """Create a new time slot"""
    if request.method == 'POST':
        day = request.POST.get('day')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        is_active = request.POST.get('is_active') == 'on'
        
        # Convert time strings to time objects
        start = time.fromisoformat(start_time)
        end = time.fromisoformat(end_time)
        
        # Calculate duration in minutes
        duration = (end.hour * 60 + end.minute) - (start.hour * 60 + start.minute)
        
        try:
            time_slot = TimeSlot.objects.create(
                day=day,
                start_time=start,
                end_time=end,
                duration_minutes=duration,
                is_active=is_active
            )
            messages.success(request, f'Time slot {day} {start_time} - {end_time} created successfully!')
            return redirect('timetables:time_slot_list')
        except Exception as e:
            messages.error(request, f'Error creating time slot: {str(e)}')
    
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    context = {
        'days': days,
    }
    
    return render(request, 'timetables/time_slot_form.html', context)


@login_required
@user_passes_test(is_admin)
def time_slot_edit(request, slot_id):
    """Edit an existing time slot"""
    time_slot = get_object_or_404(TimeSlot, id=slot_id)
    
    if request.method == 'POST':
        day = request.POST.get('day')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        is_active = request.POST.get('is_active') == 'on'
        
        # Convert time strings to time objects
        start = time.fromisoformat(start_time)
        end = time.fromisoformat(end_time)
        
        # Calculate duration in minutes
        duration = (end.hour * 60 + end.minute) - (start.hour * 60 + start.minute)
        
        try:
            time_slot.day = day
            time_slot.start_time = start
            time_slot.end_time = end
            time_slot.duration_minutes = duration
            time_slot.is_active = is_active
            time_slot.save()
            
            messages.success(request, f'Time slot updated successfully!')
            return redirect('timetables:time_slot_list')
        except Exception as e:
            messages.error(request, f'Error updating time slot: {str(e)}')
    
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    context = {
        'time_slot': time_slot,
        'days': days,
    }
    
    return render(request, 'timetables/time_slot_form.html', context)


@login_required
@user_passes_test(is_admin)
def time_slot_delete(request, slot_id):
    """Delete a time slot"""
    time_slot = get_object_or_404(TimeSlot, id=slot_id)
    
    if request.method == 'POST':
        try:
            time_slot.delete()
            messages.success(request, 'Time slot deleted successfully!')
        except Exception as e:
            messages.error(request, f'Error deleting time slot: {str(e)}')
        return redirect('timetables:time_slot_list')
    
    context = {
        'time_slot': time_slot,
    }
    
    return render(request, 'timetables/time_slot_confirm_delete.html', context)


@login_required
@user_passes_test(is_admin)
def time_slot_toggle_status(request, slot_id):
    """Toggle time slot active status"""
    time_slot = get_object_or_404(TimeSlot, id=slot_id)
    time_slot.is_active = not time_slot.is_active
    time_slot.save()
    
    status = "activated" if time_slot.is_active else "deactivated"
    messages.success(request, f'Time slot {status} successfully!')
    
    return redirect('timetables:time_slot_list')


# ==================== CLASSROOM MANAGEMENT ====================
@login_required
@user_passes_test(is_admin)
def classroom_list(request):
    """List all classrooms"""
    classrooms = Classroom.objects.all()
    
    context = {
        'classrooms': classrooms,
    }
    
    return render(request, 'timetables/classroom_list.html', context)

# timetables/views.py - Add this view

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import Classroom
from Academic.models import Discipline, Batch, Semester, Section

@login_required
@user_passes_test(is_admin)
def classroom_create(request):
    """Create a new classroom"""
    if request.method == 'POST':
        # Get form data
        room_number = request.POST.get('room_number')
        building = request.POST.get('building')
        capacity = request.POST.get('capacity')
        has_projector = request.POST.get('has_projector') == 'on'
        has_smartboard = request.POST.get('has_smartboard') == 'on'
        is_lab = request.POST.get('is_lab') == 'on'
        is_active = request.POST.get('is_active') == 'on'
        
        # Get optional association fields
        discipline_id = request.POST.get('discipline')
        batch_id = request.POST.get('batch')
        semester_id = request.POST.get('semester')
        section_id = request.POST.get('section')
        
        # Validate required fields
        if not room_number or not building or not capacity:
            messages.error(request, 'Please fill all required fields.')
            return redirect('timetables:classroom_create')
        
        try:
            # Create classroom
            classroom = Classroom.objects.create(
                room_number=room_number,
                building=building,
                capacity=capacity,
                has_projector=has_projector,
                has_smartboard=has_smartboard,
                is_lab=is_lab,
                is_active=is_active,
                discipline_id=discipline_id if discipline_id else None,
                batch_id=batch_id if batch_id else None,
                semester_id=semester_id if semester_id else None,
                section_id=section_id if section_id else None
            )
            
            messages.success(request, f'Classroom {classroom.room_number} created successfully!')
            return redirect('timetables:classroom_list')
            
        except Exception as e:
            messages.error(request, f'Error creating classroom: {str(e)}')
            return redirect('timetables:classroom_create')
    
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
    }
    
    return render(request, 'timetables/classroom_form.html', context)


@login_required
@user_passes_test(is_admin)
def classroom_edit(request, classroom_id):
    """Edit an existing classroom"""
    classroom = get_object_or_404(Classroom, id=classroom_id)
    
    if request.method == 'POST':
        # Get form data
        room_number = request.POST.get('room_number')
        building = request.POST.get('building')
        capacity = request.POST.get('capacity')
        has_projector = request.POST.get('has_projector') == 'on'
        has_smartboard = request.POST.get('has_smartboard') == 'on'
        is_lab = request.POST.get('is_lab') == 'on'
        is_active = request.POST.get('is_active') == 'on'
        
        # Get optional association fields
        discipline_id = request.POST.get('discipline')
        batch_id = request.POST.get('batch')
        semester_id = request.POST.get('semester')
        section_id = request.POST.get('section')
        
        try:
            # Update classroom
            classroom.room_number = room_number
            classroom.building = building
            classroom.capacity = capacity
            classroom.has_projector = has_projector
            classroom.has_smartboard = has_smartboard
            classroom.is_lab = is_lab
            classroom.is_active = is_active
            classroom.discipline_id = discipline_id if discipline_id else None
            classroom.batch_id = batch_id if batch_id else None
            classroom.semester_id = semester_id if semester_id else None
            classroom.section_id = section_id if section_id else None
            classroom.save()
            
            messages.success(request, f'Classroom {classroom.room_number} updated successfully!')
            return redirect('timetables:classroom_list')
            
        except Exception as e:
            messages.error(request, f'Error updating classroom: {str(e)}')
            return redirect('timetables:classroom_edit', classroom_id=classroom.id)
    
    # GET request - show form with existing data
    disciplines = Discipline.objects.all()
    batches = Batch.objects.all()
    semesters = Semester.objects.all()
    sections = Section.objects.all()
    
    context = {
        'classroom': classroom,
        'disciplines': disciplines,
        'batches': batches,
        'semesters': semesters,
        'sections': sections,
    }
    
    return render(request, 'timetables/classroom_form.html', context)


@login_required
@user_passes_test(is_admin)
def classroom_delete(request, classroom_id):
    """Delete a classroom"""
    classroom = get_object_or_404(Classroom, id=classroom_id)
    
    if request.method == 'POST':
        try:
            room_number = classroom.room_number
            classroom.delete()
            messages.success(request, f'Classroom {room_number} deleted successfully!')
        except Exception as e:
            messages.error(request, f'Error deleting classroom: {str(e)}')
        return redirect('timetables:classroom_list')
    
    context = {
        'classroom': classroom,
    }
    
    return render(request, 'timetables/classroom_confirm_delete.html', context)
# timetables/views.py - Add this for dynamic section filtering

@login_required
def get_sections_by_batch(request):
    """AJAX endpoint to get sections for a specific batch"""
    batch_id = request.GET.get('batch_id')
    if batch_id:
        sections = Section.objects.filter(batch_id=batch_id).values('id', 'name')
        return JsonResponse({'sections': list(sections)})
    return JsonResponse({'sections': []})
# ==================== TEACHER AVAILABILITY ====================
@login_required
def teacher_availability_view(request):
    """View and manage teacher availability"""
    if is_teacher(request.user):
        teacher = request.user.teacher
    else:
        teacher_id = request.GET.get('teacher_id')
        teacher = get_object_or_404(Teacher, id=teacher_id)
    
    availabilities = TeacherAvailability.objects.filter(
        teacher=teacher
    ).order_by('day', 'start_time')
    
    if request.method == 'POST':
        # Add new availability
        day = request.POST.get('day')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        is_available = request.POST.get('is_available') == 'on'
        reason = request.POST.get('reason', '')
        
        TeacherAvailability.objects.create(
            teacher=teacher,
            day=day,
            start_time=start_time,
            end_time=end_time,
            is_available=is_available,
            reason=reason
        )
        
        messages.success(request, 'Availability added successfully!')
        return redirect('teacher_availability')
    
    context = {
        'teacher': teacher,
        'availabilities': availabilities,
        'days': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'],
    }
    
    return render(request, 'timetables/teacher_availability.html', context)


# ==================== CONFLICT CHECK ====================
@login_required
@user_passes_test(is_admin)
def check_conflicts(request):
    """Check for timetable conflicts"""
    # Check for teacher conflicts
    teacher_conflicts = TimetableEntry.objects.filter(
        is_active=True
    ).values('teacher', 'time_slot__day', 'time_slot__start_time').annotate(
        count=Count('id')
    ).filter(count__gt=1)
    
    # Check for section conflicts
    section_conflicts = TimetableEntry.objects.filter(
        is_active=True
    ).values('section', 'time_slot__day', 'time_slot__start_time').annotate(
        count=Count('id')
    ).filter(count__gt=1)
    
    # Check for classroom conflicts
    classroom_conflicts = TimetableEntry.objects.filter(
        is_active=True
    ).values('classroom', 'time_slot__day', 'time_slot__start_time').annotate(
        count=Count('id')
    ).filter(count__gt=1)
    
    context = {
        'teacher_conflicts': teacher_conflicts,
        'section_conflicts': section_conflicts,
        'classroom_conflicts': classroom_conflicts,
    }
    
    return render(request, 'timetables/conflicts.html', context)


# ==================== EXAM TIMETABLE ====================
@login_required
def exam_timetable_view(request):
    """View exam timetable"""
    exam_type = request.GET.get('type', 'all')
    
    exam_timetables = ExamTimetable.objects.filter(is_active=True)
    
    if exam_type != 'all':
        exam_timetables = exam_timetables.filter(exam_type=exam_type)
    
    # Group by date
    exam_by_date = {}
    for exam in exam_timetables.order_by('exam_date', 'start_time'):
        date_str = exam.exam_date.strftime('%Y-%m-%d')
        if date_str not in exam_by_date:
            exam_by_date[date_str] = []
        exam_by_date[date_str].append(exam)
    
    context = {
        'exam_by_date': exam_by_date,
        'current_type': exam_type,
    }
    
    return render(request, 'timetables/exam_timetable.html', context)


@login_required
@user_passes_test(is_admin)
def create_exam_timetable(request):
    """Create exam timetable entry"""
    if request.method == 'POST':
        subject_id = request.POST.get('subject')
        teacher_id = request.POST.get('teacher')
        section_id = request.POST.get('section')
        batch_id = request.POST.get('batch')
        semester_id = request.POST.get('semester')
        exam_type = request.POST.get('exam_type')
        exam_date = request.POST.get('exam_date')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        classroom_id = request.POST.get('classroom')
        total_marks = request.POST.get('total_marks')
        duration_minutes = request.POST.get('duration_minutes')
        
        # Calculate duration if not provided
        if not duration_minutes and start_time and end_time:
            start = datetime.strptime(start_time, '%H:%M')
            end = datetime.strptime(end_time, '%H:%M')
            duration_minutes = (end - start).seconds // 60
        
        ExamTimetable.objects.create(
            subject_id=subject_id,
            teacher_id=teacher_id,
            section_id=section_id,
            batch_id=batch_id,
            semester_id=semester_id,
            exam_type=exam_type,
            exam_date=exam_date,
            start_time=start_time,
            end_time=end_time,
            classroom_id=classroom_id,
            total_marks=total_marks,
            duration_minutes=duration_minutes,
            is_active=True
        )
        
        messages.success(request, 'Exam timetable created successfully!')
        return redirect('exam_timetable')
    
    subjects = Subject.objects.filter(is_active=True)
    teachers = Teacher.objects.filter(is_active=True)
    sections = Section.objects.all()
    batches = Batch.objects.all()
    semesters = Semester.objects.all()
    classrooms = Classroom.objects.filter(is_active=True)
    
    context = {
        'subjects': subjects,
        'teachers': teachers,
        'sections': sections,
        'batches': batches,
        'semesters': semesters,
        'classrooms': classrooms,
    }
    
    return render(request, 'timetables/create_exam_timetable.html', context)


# ==================== DASHBOARD ====================
def timetable_dashboard(request):
    """Main dashboard for timetables"""
    today = date.today()
    today_name = today.strftime('%A')
    
    # Statistics
    total_classes = TimetableEntry.objects.filter(is_active=True).count()
    total_exams = ExamTimetable.objects.filter(is_active=True).count()
    active_teachers = Teacher.objects.filter(is_active=True).count()
    active_sections = Section.objects.all().count()
    
    # Today's schedule
    today_schedule = TimetableEntry.objects.filter(
        is_active=True,
        time_slot__day=today_name
    ).select_related('teacher', 'subject', 'section', 'classroom', 'time_slot')
    
    # Upcoming exams (next 7 days)
    upcoming_exams = ExamTimetable.objects.filter(
        is_active=True,
        exam_date__gte=today,
        exam_date__lte=today + timedelta(days=7)
    ).select_related('teacher', 'subject', 'section')[:10]
    
    # Teacher availability for today
    teacher_availability = []
    teachers = Teacher.objects.filter(is_active=True)[:10]
    for teacher in teachers:
        availability = TeacherAvailability.objects.filter(
            teacher=teacher,
            day=today_name,
            is_available=True
        ).exists()
        teacher.is_available_today = availability
        teacher_availability.append(teacher)
    
    # Weekly statistics
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    weekly_stats = {}
    for day in days:
        classes = TimetableEntry.objects.filter(
            is_active=True,
            time_slot__day=day
        )
        exams = ExamTimetable.objects.filter(
            is_active=True,
            exam_date__week_day=days.index(day) + 2
        )
        
        # Calculate busy hours
        busy_hours = 0
        for entry in classes:
            duration = (entry.time_slot.end_time.hour * 60 + entry.time_slot.end_time.minute) - \
                      (entry.time_slot.start_time.hour * 60 + entry.time_slot.start_time.minute)
            busy_hours += duration / 60
        
        # Find most active section
        most_active = classes.values('section__name').annotate(
            count=Count('id')
        ).order_by('-count').first()
        
        weekly_stats[day] = {
            'total_classes': classes.count(),
            'total_exams': exams.count(),
            'busy_hours': round(busy_hours, 1),
            'most_active_section': most_active['section__name'] if most_active else None
        }
    
    # Classroom utilization
    classrooms = Classroom.objects.filter(is_active=True)
    classroom_utilization = []
    for classroom in classrooms:
        classes_count = TimetableEntry.objects.filter(
            classroom=classroom,
            is_active=True
        ).count()
        
        utilization = min(100, (classes_count / 40) * 100)
        
        classroom_utilization.append({
            'room_number': classroom.room_number,
            'capacity': classroom.capacity,
            'class_count': classes_count,
            'utilization': round(utilization)
        })
    
    # Recent generation requests
    recent_requests = TimetableGenerationRequest.objects.all().order_by('-created_at')[:5]
    
    # Check for conflicts
    teacher_conflicts_count = TimetableEntry.objects.filter(
        is_active=True
    ).values('teacher', 'time_slot__day', 'time_slot__start_time').annotate(
        count=Count('id')
    ).filter(count__gt=1).count()
    
    section_conflicts_count = TimetableEntry.objects.filter(
        is_active=True
    ).values('section', 'time_slot__day', 'time_slot__start_time').annotate(
        count=Count('id')
    ).filter(count__gt=1).count()
    
    classroom_conflicts_count = TimetableEntry.objects.filter(
        is_active=True
    ).values('classroom', 'time_slot__day', 'time_slot__start_time').annotate(
        count=Count('id')
    ).filter(count__gt=1).count()
    
    conflicts_exist = teacher_conflicts_count > 0 or section_conflicts_count > 0 or classroom_conflicts_count > 0
    
    context = {
        'total_classes': total_classes,
        'total_exams': total_exams,
        'active_teachers': active_teachers,
        'active_sections': active_sections,
        'today': today,
        'today_schedule': today_schedule,
        'upcoming_exams': upcoming_exams,
        'teacher_availability': teacher_availability,
        'weekly_stats': weekly_stats,
        'classroom_utilization': classroom_utilization,
        'recent_requests': recent_requests,
        'teacher_conflicts_count': teacher_conflicts_count,
        'section_conflicts_count': section_conflicts_count,
        'classroom_conflicts_count': classroom_conflicts_count,
        'conflicts_exist': conflicts_exist,
    }
    
    return render(request, 'timetables/dashboard.html', context)

    # timetables/views.py - Add these views

# ==================== CLASSROOM TIMETABLE VIEW ====================
@login_required
def classroom_timetable_view(request, classroom_id=None):
    """View timetable for a specific classroom"""
    if classroom_id:
        classroom = get_object_or_404(Classroom, id=classroom_id)
    else:
        # Show list of classrooms if no ID provided
        classrooms = Classroom.objects.filter(is_active=True)
        context = {
            'classrooms': classrooms,
        }
        return render(request, 'timetables/classroom_list_timetable.html', context)
    
    # Get timetable entries for this classroom
    timetable_entries = TimetableEntry.objects.filter(
        classroom=classroom,
        is_active=True
    ).select_related('teacher', 'subject', 'section', 'batch', 'semester', 'time_slot')
    
    # Organize by day
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    timetable_by_day = {}
    
    for day in days:
        timetable_by_day[day] = timetable_entries.filter(
            time_slot__day=day
        ).order_by('time_slot__start_time')
    
    # Get all time slots for the timetable grid
    time_slots = TimeSlot.objects.filter(is_active=True).order_by('start_time')
    
    context = {
        'classroom': classroom,
        'timetable_entries': timetable_entries,
        'timetable_by_day': timetable_by_day,
        'time_slots': time_slots,
        'days': days,
    }
    
    return render(request, 'timetables/classroom_timetable.html', context)

# timetables/views.py - Add these views

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from datetime import date

from .models import Laboratory, TimetableEntry
from Academic.models import Batch, Section, Semester, Discipline

# ==================== LABORATORY MANAGEMENT VIEWS ====================

@login_required
@user_passes_test(is_admin)
def laboratory_list(request):
    """List all laboratories"""
    laboratories = Laboratory.objects.filter(is_active=True).select_related(
        'primary_batch', 'primary_section', 'primary_semester', 'primary_discipline'
    ).prefetch_related('batches', 'sections', 'semesters', 'disciplines')
    
    context = {
        'laboratories': laboratories,
    }
    return render(request, 'timetables/laboratory_list.html', context)


@login_required
@user_passes_test(is_admin)
def laboratory_create(request):
    """Create a new laboratory"""
    if request.method == 'POST':
        try:
            # Basic Information
            lab_code = request.POST.get('lab_code')
            lab_name = request.POST.get('lab_name')
            building = request.POST.get('building')
            floor = request.POST.get('floor', '')
            capacity = request.POST.get('capacity')
            
            # Computer Details
            computer_count = request.POST.get('computer_count', 0)
            computer_config = request.POST.get('computer_config', '')
            operating_system = request.POST.get('operating_system', '')
            
            # Software
            software_installed = request.POST.get('software_installed', '')
            
            # Facilities
            has_projector = request.POST.get('has_projector') == 'on'
            has_smartboard = request.POST.get('has_smartboard') == 'on'
            has_ac = request.POST.get('has_ac') == 'on'
            has_generator = request.POST.get('has_generator') == 'on'
            has_wifi = request.POST.get('has_wifi') == 'on'
            has_printer = request.POST.get('has_printer') == 'on'
            has_whiteboard = request.POST.get('has_whiteboard') == 'on'
            
            # Network
            internet_speed = request.POST.get('internet_speed', '')
            network_type = request.POST.get('network_type', '')
            
            # Primary Associations
            primary_batch_id = request.POST.get('primary_batch')
            primary_section_id = request.POST.get('primary_section')
            primary_semester_id = request.POST.get('primary_semester')
            primary_discipline_id = request.POST.get('primary_discipline')
            
            # Multiple Associations
            batch_ids = request.POST.getlist('batches')
            section_ids = request.POST.getlist('sections')
            semester_ids = request.POST.getlist('semesters')
            discipline_ids = request.POST.getlist('disciplines')
            
            # Maintenance
            is_active = request.POST.get('is_active') == 'on'
            last_maintenance = request.POST.get('last_maintenance') or None
            next_maintenance = request.POST.get('next_maintenance') or None
            
            # Create laboratory
            lab = Laboratory.objects.create(
                lab_code=lab_code,
                lab_name=lab_name,
                building=building,
                floor=floor,
                capacity=capacity,
                computer_count=computer_count,
                computer_config=computer_config,
                operating_system=operating_system,
                software_installed=software_installed,
                has_projector=has_projector,
                has_smartboard=has_smartboard,
                has_ac=has_ac,
                has_generator=has_generator,
                has_wifi=has_wifi,
                has_printer=has_printer,
                has_whiteboard=has_whiteboard,
                internet_speed=internet_speed,
                network_type=network_type,
                primary_batch_id=primary_batch_id if primary_batch_id else None,
                primary_section_id=primary_section_id if primary_section_id else None,
                primary_semester_id=primary_semester_id if primary_semester_id else None,
                primary_discipline_id=primary_discipline_id if primary_discipline_id else None,
                is_active=is_active,
                last_maintenance=last_maintenance,
                next_maintenance=next_maintenance,
            )
            
            # Add many-to-many relationships
            if batch_ids:
                lab.batches.set(batch_ids)
            if section_ids:
                lab.sections.set(section_ids)
            if semester_ids:
                lab.semesters.set(semester_ids)
            if discipline_ids:
                lab.disciplines.set(discipline_ids)
            
            messages.success(request, f'Laboratory {lab.lab_code} created successfully!')
            return redirect('timetables:laboratory_list')
            
        except Exception as e:
            messages.error(request, f'Error creating laboratory: {str(e)}')
            return redirect('timetables:laboratory_create')
    
    # GET request - show form
    batches = Batch.objects.all()
    sections = Section.objects.all()
    semesters = Semester.objects.all()
    disciplines = Discipline.objects.all()
    
    context = {
        'batches': batches,
        'sections': sections,
        'semesters': semesters,
        'disciplines': disciplines,
    }
    return render(request, 'timetables/laboratory_form.html', context)


@login_required
@user_passes_test(is_admin)
def laboratory_edit(request, lab_id):
    """Edit an existing laboratory"""
    lab = get_object_or_404(Laboratory, id=lab_id)
    
    if request.method == 'POST':
        try:
            # Update basic information
            lab.lab_code = request.POST.get('lab_code')
            lab.lab_name = request.POST.get('lab_name')
            lab.building = request.POST.get('building')
            lab.floor = request.POST.get('floor', '')
            lab.capacity = request.POST.get('capacity')
            lab.computer_count = request.POST.get('computer_count', 0)
            lab.computer_config = request.POST.get('computer_config', '')
            lab.operating_system = request.POST.get('operating_system', '')
            lab.software_installed = request.POST.get('software_installed', '')
            
            # Facilities
            lab.has_projector = request.POST.get('has_projector') == 'on'
            lab.has_smartboard = request.POST.get('has_smartboard') == 'on'
            lab.has_ac = request.POST.get('has_ac') == 'on'
            lab.has_generator = request.POST.get('has_generator') == 'on'
            lab.has_wifi = request.POST.get('has_wifi') == 'on'
            lab.has_printer = request.POST.get('has_printer') == 'on'
            lab.has_whiteboard = request.POST.get('has_whiteboard') == 'on'
            
            # Network
            lab.internet_speed = request.POST.get('internet_speed', '')
            lab.network_type = request.POST.get('network_type', '')
            
            # Primary Associations
            lab.primary_batch_id = request.POST.get('primary_batch') or None
            lab.primary_section_id = request.POST.get('primary_section') or None
            lab.primary_semester_id = request.POST.get('primary_semester') or None
            lab.primary_discipline_id = request.POST.get('primary_discipline') or None
            
            # Multiple Associations
            batch_ids = request.POST.getlist('batches')
            section_ids = request.POST.getlist('sections')
            semester_ids = request.POST.getlist('semesters')
            discipline_ids = request.POST.getlist('disciplines')
            
            # Maintenance
            lab.is_active = request.POST.get('is_active') == 'on'
            lab.last_maintenance = request.POST.get('last_maintenance') or None
            lab.next_maintenance = request.POST.get('next_maintenance') or None
            
            lab.save()
            
            # Update many-to-many relationships
            lab.batches.set(batch_ids)
            lab.sections.set(section_ids)
            lab.semesters.set(semester_ids)
            lab.disciplines.set(discipline_ids)
            
            messages.success(request, f'Laboratory {lab.lab_code} updated successfully!')
            return redirect('timetables:laboratory_list')
            
        except Exception as e:
            messages.error(request, f'Error updating laboratory: {str(e)}')
            return redirect('timetables:laboratory_edit', lab_id=lab.id)
    
    # GET request - show form with existing data
    batches = Batch.objects.all()
    sections = Section.objects.all()
    semesters = Semester.objects.all()
    disciplines = Discipline.objects.all()
    
    context = {
        'lab': lab,
        'batches': batches,
        'sections': sections,
        'semesters': semesters,
        'disciplines': disciplines,
        'selected_batches': lab.batches.values_list('id', flat=True),
        'selected_sections': lab.sections.values_list('id', flat=True),
        'selected_semesters': lab.semesters.values_list('id', flat=True),
        'selected_disciplines': lab.disciplines.values_list('id', flat=True),
    }
    return render(request, 'timetables/laboratory_form.html', context)


@login_required
@user_passes_test(is_admin)
def laboratory_delete(request, lab_id):
    """Delete a laboratory"""
    lab = get_object_or_404(Laboratory, id=lab_id)
    
    if request.method == 'POST':
        try:
            lab_code = lab.lab_code
            lab.delete()
            messages.success(request, f'Laboratory {lab_code} deleted successfully!')
        except Exception as e:
            messages.error(request, f'Error deleting laboratory: {str(e)}')
        return redirect('timetables:laboratory_list')
    
    context = {'lab': lab}
    return render(request, 'timetables/laboratory_confirm_delete.html', context)


@login_required
def laboratory_timetable(request, lab_id):
    """View timetable for a specific laboratory"""
    lab = get_object_or_404(Laboratory, id=lab_id)
    
    # Get timetable entries for this laboratory
    timetable_entries = TimetableEntry.objects.filter(
        classroom__room_number__icontains=lab.lab_code,
        is_active=True
    ).select_related('teacher', 'subject', 'section', 'batch', 'semester', 'time_slot', 'classroom')
    
    # If no entries found with classroom, try to get entries where subject requires lab
    if not timetable_entries.exists():
        # Get subjects that have lab classes (credit hours 4 or 6)
        lab_subjects = Subject.objects.filter(
            Q(credit_hours=4) | Q(credit_hours=6),
            is_active=True
        )
        timetable_entries = TimetableEntry.objects.filter(
            subject__in=lab_subjects,
            section__in=lab.sections.all(),
            is_active=True
        ).select_related('teacher', 'subject', 'section', 'batch', 'semester', 'time_slot', 'classroom')
    
    # Organize by day
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    timetable_by_day = {}
    
    for day in days:
        timetable_by_day[day] = timetable_entries.filter(
            time_slot__day=day
        ).order_by('time_slot__start_time')
    
    # Get all time slots
    time_slots = TimeSlot.objects.filter(is_active=True).order_by('start_time')
    
    context = {
        'lab': lab,
        'timetable_entries': timetable_entries,
        'timetable_by_day': timetable_by_day,
        'time_slots': time_slots,
        'days': days,
        'today': date.today(),
    }
    return render(request, 'timetables/laboratory_timetable.html', context)

# ==================== SECTION TIMETABLE VIEW (Enhanced) ====================
@login_required
def section_timetable_view(request, section_id=None):
    """View timetable for a specific section"""
    if section_id:
        section = get_object_or_404(Section, id=section_id)
    else:
        # Show list of sections if no ID provided
        sections = Section.objects.all().select_related('batch', 'discipline')
        context = {
            'sections': sections,
        }
        return render(request, 'timetables/section_list_timetable.html', context)
    
    # Get timetable entries for this section
    timetable_entries = TimetableEntry.objects.filter(
        section=section,
        is_active=True
    ).select_related('teacher', 'subject', 'batch', 'semester', 'time_slot', 'classroom')
    
    # Organize by day
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    timetable_by_day = {}
    
    for day in days:
        timetable_by_day[day] = timetable_entries.filter(
            time_slot__day=day
        ).order_by('time_slot__start_time')
    
    # Get all time slots for the timetable grid
    time_slots = TimeSlot.objects.filter(is_active=True).order_by('start_time')
    
    # Get upcoming exams for this section
    upcoming_exams = ExamTimetable.objects.filter(
        section=section,
        is_active=True,
        exam_date__gte=date.today()
    ).select_related('subject', 'teacher', 'classroom')[:5]
    
    context = {
        'section': section,
        'timetable_entries': timetable_entries,
        'timetable_by_day': timetable_by_day,
        'time_slots': time_slots,
        'days': days,
        'upcoming_exams': upcoming_exams,
        'today': date.today(),
    }
    
    return render(request, 'timetables/section_timetable.html', context)