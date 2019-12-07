from django.shortcuts import redirect, render,get_object_or_404
from django.contrib import messages
from .models import Discipline, Batch, Semester, Section, Department

# <-- Batches -->
def add_batch(request):
    decipline = Discipline.objects.all()

    if request.method == 'POST':
        Batch.objects.create(
            name=request.POST.get('name'),
            start_session=request.POST.get('start_session'),
            end_session=request.POST.get('end_session'),
            decipline_id=request.POST.get('discipline')
        )
        messages.success(request, "Batch added successfully!")
        return redirect('view_batch')

    return render(request, "academic_temp/add_batches.html", {
        'discipline': decipline
    })

def view_batch(request):
    batches = Batch.objects.all()
    return render(request, 'academic_temp/view_batches.html', {'batches': batches})

def edit_batch(request, batch_id):
    batch = get_object_or_404(Batch, id=batch_id)
    disciplines = Discipline.objects.all()

    if request.method == 'POST':
        batch.name = request.POST.get('name')
        batch.start_session = request.POST.get('start_session')
        batch.end_session = request.POST.get('end_session')
        discipline_id = request.POST.get('discipline')
        batch.decipline = get_object_or_404(Discipline, id=discipline_id)
        batch.save()
        messages.success(request, 'Batch updated successfully!')
        return redirect('view_batch')  

    context = {
        'batch': batch,
        'disciplines': disciplines
    }
    return render(request, 'academic_temp/edit_batch.html', context)

def delete_batch(request, batch_id):
    batch = get_object_or_404(Batch, id=batch_id)
    batch.delete()
    messages.success(request, 'Batch Deleted successfully!')
    return redirect('view_batch')  




# <-- Section -->

def add_section(request):
    disciplines = Discipline.objects.all()
    batches = Batch.objects.all()

    if request.method == 'POST':
        try:
            Section.objects.create(
                name=request.POST.get('name'),
                batches=Batch.objects.get(id=request.POST.get('batch_id')),
                discipline=Discipline.objects.get(id=request.POST.get('discipline'))
            )
            messages.success(request, "Section added successfully!")
            # return redirect('view_batch')
        except Exception as e:
            messages.error(request, f"Error: {e}")

    return render(request, "academic_temp/add_section.html", {
        'disciplines': disciplines,
        'batches': batches
    })

def view_section(request):

    sections = Section.objects.all()

    return render(request, 'academic_temp/view_section.html', {'sections': sections})

def edit_section(request, section_id):
    section = get_object_or_404(Section, id=section_id)
    batches = Batch.objects.all()
    disciplines = Discipline.objects.all()

    if request.method == 'POST':
        section.name = request.POST.get('name')

        batch_id = request.POST.get('batches')
        section.batches = get_object_or_404(Batch, id=batch_id)

        discipline_id = request.POST.get('discipline')
        section.discipline = get_object_or_404(Discipline, id=discipline_id)

        section.save()
        messages.success(request, 'Section updated successfully!')
        return redirect('view_section')

    context = {
        'section': section,
        'batch': batches,
        'disciplines': disciplines
    }

    return render(request, 'academic_temp/edit_section.html', context)

def delete_section(request, section_id):
    section = get_object_or_404(Section, id=section_id)
    section.delete()
    messages.success(request, 'section Deleted successfully!')
    return redirect('view_section')  




# <-- Semester -->

def add_semester(request):
    disciplines = Discipline.objects.all()
    batches = Batch.objects.all()

    if request.method == 'POST':
        number = request.POST.get('name')
        batch = Batch.objects.get(id=request.POST.get('batch_id'))
        discipline = Discipline.objects.get(id=request.POST.get('discipline'))

        if Semester.objects.filter(number=number).exists():
            messages.error(request, "This semester already exists.")
        else:
            Semester.objects.create(
                number=number,
                # batch=batch,
                # discipline=discipline
            )
            messages.success(request, "Semester added successfully!")
            return redirect('view_semester')

    return render(request, 'academic_temp/add_semester.html', {
        'disciplines': disciplines,
        'batches': batches
    })

def view_semester(request):
    semesters = Semester.objects.all()
    return render(request, 'academic_temp/view_semester.html', {'semesters': semesters})

def edit_semester(request, semester_id):
    semester = get_object_or_404(Semester, id=semester_id)
    disciplines = Discipline.objects.all()
    batches = Batch.objects.all()

    if request.method == 'POST':
        semester.number = request.POST.get('name')
        semester.save()
        messages.success(request, "Semester updated successfully!")
        return redirect('view_semester')

    return render(request, 'academic_temp/edit_semester.html', {
        'semester': semester,
        'disciplines': disciplines,
        'batches': batches
    })

def delete_semester(request, semester_id):
    semester = get_object_or_404(Semester, id=semester_id)

    if request.method == "POST":
        semester.delete()
        messages.success(request, "Semester deleted successfully!")
        return redirect('view_semester')

    return render(request, 'academic_temp/delete_semester.html', {
        'semester': semester
    })




# <-- Discipline -->

def add_discipline(request):
    if request.method == 'POST':
        program = request.POST.get('program')
        field = request.POST.get('field')

        if Discipline.objects.filter(program=program, field=field).exists():
            messages.error(request, "This Discipline already exists.")
        else:
            Discipline.objects.create(program=program, field=field)
            messages.success(request, "Discipline added successfully!")
            return redirect('view_discipline')

    return render(request, 'academic_temp/add_discipline.html')

def view_discipline(request):
    disciplines = Discipline.objects.all()
    return render(request, 'academic_temp/view_discipline.html', {'disciplines': disciplines})

def edit_discipline(request, discipline_id):
    discipline = get_object_or_404(Discipline, id=discipline_id)

    if request.method == 'POST':
        discipline.field = request.POST.get('field')
        discipline.save()
        messages.success(request, "Discipline updated successfully!")
        return redirect('view_discipline')

    return render(request, 'academic_temp/edit_discipline.html', {
        'discipline': discipline
    })

def delete_discipline(request, discipline_id):
    discipline = get_object_or_404(Discipline, id=discipline_id)

    if request.method == 'POST':
        discipline.delete()
        messages.success(request, "Discipline deleted successfully!")
        return redirect('view_discipline')

    return render(request, 'academic_temp/delete_discipline.html', {
        'discipline': discipline
    })