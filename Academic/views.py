from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Discipline, Batch, Semester, Section

# ============= DASHBOARD =============

def academic_dashboard(request):
    """Academic Management Dashboard - Main landing page"""
    
    # Get counts for statistics cards
    total_disciplines = Discipline.objects.count()
    total_batches = Batch.objects.count()
    total_semesters = Semester.objects.count()
    total_sections = Section.objects.count()
    
    # Get recent items (last 5)
    recent_batches = Batch.objects.all().order_by('-id')[:5]
    recent_semesters = Semester.objects.all().order_by('-id')[:5]
    recent_sections = Section.objects.all().order_by('-id')[:5]
    recent_disciplines = Discipline.objects.all().order_by('-id')[:5]
    
    context = {
        'total_disciplines': total_disciplines,
        'total_batches': total_batches,
        'total_semesters': total_semesters,
        'total_sections': total_sections,
        'recent_batches': recent_batches,
        'recent_semesters': recent_semesters,
        'recent_sections': recent_sections,
        'recent_disciplines': recent_disciplines,
    }
    return render(request, 'academic/dashboard.html', context)


# ============= BATCH MANAGEMENT =============

def add_batch(request):
    disciplines = Discipline.objects.all()
    if request.method == 'POST':
        name = request.POST.get('name')
        start_session = request.POST.get('start_session')
        end_session = request.POST.get('end_session')
        discipline_id = request.POST.get('discipline')
        
        if Batch.objects.filter(name=name).exists():
            messages.error(request, f'Batch "{name}" already exists!')
        else:
            Batch.objects.create(
                name=name,
                start_session=start_session,
                end_session=end_session,
                decipline_id=discipline_id
            )
            messages.success(request, f'Batch "{name}" added successfully!')
            return redirect('view_batch')
    
    return render(request, 'academic/add_batch.html', {'disciplines': disciplines})


def view_batch(request):
    batches = Batch.objects.all().select_related('decipline')
    return render(request, 'academic/view_batch.html', {'batches': batches})


def edit_batch(request, batch_id):
    batch = get_object_or_404(Batch, id=batch_id)
    disciplines = Discipline.objects.all()
    
    if request.method == 'POST':
        batch.name = request.POST.get('name')
        batch.start_session = request.POST.get('start_session')
        batch.end_session = request.POST.get('end_session')
        batch.decipline_id = request.POST.get('discipline')
        batch.save()
        messages.success(request, 'Batch updated successfully!')
        return redirect('view_batch')
    
    return render(request, 'academic/edit_batch.html', {'batch': batch, 'disciplines': disciplines})


def delete_batch(request, batch_id):
    batch = get_object_or_404(Batch, id=batch_id)
    if request.method == 'POST':
        batch.delete()
        messages.success(request, 'Batch deleted successfully!')
        return redirect('view_batch')
    return render(request, 'academic/delete_batch.html', {'batch': batch})


# ============= SECTION MANAGEMENT =============

def add_section(request):
    disciplines = Discipline.objects.all()
    batches = Batch.objects.all()
    
    if request.method == 'POST':
        name = request.POST.get('name')
        batch_id = request.POST.get('batch_id')
        discipline_id = request.POST.get('discipline')
        
        Section.objects.create(
            name=name,
            batches_id=batch_id,
            discipline_id=discipline_id
        )
        messages.success(request, 'Section added successfully!')
        return redirect('view_section')
    
    return render(request, 'academic/add_section.html', {
        'disciplines': disciplines,
        'batches': batches
    })


def view_section(request):
    sections = Section.objects.all().select_related('batches', 'discipline')
    return render(request, 'academic/view_section.html', {'sections': sections})


def edit_section(request, section_id):
    section = get_object_or_404(Section, id=section_id)
    batches = Batch.objects.all()
    disciplines = Discipline.objects.all()
    
    if request.method == 'POST':
        section.name = request.POST.get('name')
        section.batches_id = request.POST.get('batches')
        section.discipline_id = request.POST.get('discipline')
        section.save()
        messages.success(request, 'Section updated successfully!')
        return redirect('view_section')
    
    return render(request, 'academic/edit_section.html', {
        'section': section,
        'batches': batches,
        'disciplines': disciplines
    })


def delete_section(request, section_id):
    section = get_object_or_404(Section, id=section_id)
    if request.method == 'POST':
        section.delete()
        messages.success(request, 'Section deleted successfully!')
        return redirect('view_section')
    return render(request, 'academic/delete_section.html', {'section': section})


# ============= SEMESTER MANAGEMENT =============

def add_semester(request):
    disciplines = Discipline.objects.all()
    batches = Batch.objects.all()
    
    if request.method == 'POST':
        number = request.POST.get('name')
        batch_id = request.POST.get('batch_id')
        discipline_id = request.POST.get('discipline')
        
        Semester.objects.create(
            number=number,
            batch_id=batch_id,
            discipline_id=discipline_id
        )
        messages.success(request, 'Semester added successfully!')
        return redirect('view_semester')
    
    return render(request, 'academic/add_semester.html', {
        'disciplines': disciplines,
        'batches': batches
    })


def view_semester(request):
    semesters = Semester.objects.all().select_related('batch', 'discipline')
    return render(request, 'academic/view_semester.html', {'semesters': semesters})


def edit_semester(request, semester_id):
    semester = get_object_or_404(Semester, id=semester_id)
    disciplines = Discipline.objects.all()
    batches = Batch.objects.all()
    
    if request.method == 'POST':
        semester.number = request.POST.get('name')
        semester.batch_id = request.POST.get('batch_id')
        semester.discipline_id = request.POST.get('discipline')
        semester.save()
        messages.success(request, 'Semester updated successfully!')
        return redirect('view_semester')
    
    return render(request, 'academic/edit_semester.html', {
        'semester': semester,
        'disciplines': disciplines,
        'batches': batches
    })


def delete_semester(request, semester_id):
    semester = get_object_or_404(Semester, id=semester_id)
    if request.method == 'POST':
        semester.delete()
        messages.success(request, 'Semester deleted successfully!')
        return redirect('view_semester')
    return render(request, 'academic/delete_semester.html', {'semester': semester})


# ============= DISCIPLINE MANAGEMENT =============

def add_discipline(request):
    if request.method == 'POST':
        program = request.POST.get('program')
        field = request.POST.get('field')
        
        Discipline.objects.create(program=program, field=field)
        messages.success(request, 'Discipline added successfully!')
        return redirect('view_discipline')
    
    return render(request, 'academic/add_discipline.html')


def view_discipline(request):
    disciplines = Discipline.objects.all()
    return render(request, 'academic/view_discipline.html', {'disciplines': disciplines})


def edit_discipline(request, discipline_id):
    discipline = get_object_or_404(Discipline, id=discipline_id)
    
    if request.method == 'POST':
        discipline.field = request.POST.get('field')
        discipline.save()
        messages.success(request, 'Discipline updated successfully!')
        return redirect('view_discipline')
    
    return render(request, 'academic/edit_discipline.html', {'discipline': discipline})


def delete_discipline(request, discipline_id):
    discipline = get_object_or_404(Discipline, id=discipline_id)
    if request.method == 'POST':
        discipline.delete()
        messages.success(request, 'Discipline deleted successfully!')
        return redirect('view_discipline')
    return render(request, 'academic/delete_discipline.html', {'discipline': discipline})