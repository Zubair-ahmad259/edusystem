from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Batch, Semester, Section, Parent, Student ,Discipline
from datetime import datetime
from .models import Student, Semester


def add_student(request):
    batches = Batch.objects.all()
    semesters = Semester.objects.all()
    sections = Section.objects.all()
    parents = Parent.objects.all()
    disciplines=Discipline.objects.all()
    
    if request.method == 'POST':
        try:
            # Handle parent data (optional)
            parent = None
            if request.POST.get('father_name'):
                parent = Parent.objects.create(
                    father_name=request.POST.get('father_name'),
                    mother_name=request.POST.get('mother_name', ''),
                    father_email=request.POST.get('father_email', ''),
                    father_contact=request.POST.get('father_contact', ''),
                    address=request.POST.get('parent_address', '')
                )
            
            # Create Student
            student = Student(
                first_name=request.POST.get('first_name'),
                last_name=request.POST.get('last_name'),
                student_id=request.POST.get('student_id'),
                admission_number=request.POST.get('admission_number'),
                gender=request.POST.get('gender'),
                dob=request.POST.get('dob'),
                email=request.POST.get('email'),
                contact_number=request.POST.get('contact_number'),
                batch=Batch.objects.get(id=request.POST.get('batch')),
                semester=Semester.objects.get(id=request.POST.get('semester')),
                section=Section.objects.get(id=request.POST.get('section')),
                discipline=Discipline.objects.get(id=request.POST.get('discipline')),

                parent=parent,
                address=request.POST.get('address'),
                


            )

            
            # Handle image upload
            if 'image' in request.FILES:
                student.image = request.FILES['image']
            
            student.save()
            
            messages.success(request, 'Student created successfully!')
            return redirect('student_list')
            
        except Exception as e:
            messages.error(request, f'Error creating student: {str(e)}')
            print(f"Error: {str(e)}")
    
    return render(request, 'students/add-student.html', {
        'batches': batches,
        'semesters': semesters,
        'sections': sections,
        'parents': parents,
        'disciplines':disciplines,
        'gender_choices': Student.GENDER_CHOICES
    })

def student_list(request):
    # Get all data from database
    batches = Batch.objects.all()
    all_sections = Section.objects.all()
    semesters = Semester.objects.all()
    disciplines = Discipline.objects.all()

    # Store user selection
    selected_discipline = None
    selected_batch = None
    selected_section = None
    selected_semester = None

    # Get all students first
    students = Student.objects.all().order_by('last_name')

    # Filter by Discipline
    discipline_id = request.GET.get('discipline')
    if discipline_id:
        selected_discipline = get_object_or_404(Discipline, id=discipline_id)
        students = students.filter(discipline=selected_discipline)

    # Filter by Batch
    batch_id = request.GET.get('batch')
    if batch_id:
        selected_batch = get_object_or_404(Batch, id=batch_id)
        students = students.filter(batch=selected_batch)
        sections = all_sections.filter(batch=selected_batch)
    else:
        sections = all_sections

    # Filter by Section
    section_id = request.GET.get('section')
    if section_id:
        selected_section = get_object_or_404(Section, id=section_id)
        students = students.filter(section=selected_section)

    # Filter by Semester
    semester_id = request.GET.get('semester')
    if semester_id:
        selected_semester = get_object_or_404(Semester, id=semester_id)
        students = students.filter(semester=selected_semester)

    # Send all data to template
    context = {
        'students': students,
        'batches': batches,
        'sections': sections,
        'semesters': semesters,
        'disciplines': disciplines,
        'selected_discipline': selected_discipline,
        'selected_batch': selected_batch,
        'selected_section': selected_section,
        'selected_semester': selected_semester,
    }
    return render(request, 'students/students.html', context)

def view_student(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    return render(request, 'students/student-details.html', {'student': student})
def edit_student(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    batches = Batch.objects.all()
    semesters = Semester.objects.all()
    sections = Section.objects.all()
    
    if request.method == 'POST':
        try:
            # Update student fields
            student.first_name = request.POST.get('first_name')
            student.last_name = request.POST.get('last_name')
            student.student_id = request.POST.get('student_id')
            student.admission_number = request.POST.get('admission_number')
            student.gender = request.POST.get('gender')
            student.dob = request.POST.get('dob')
            student.email = request.POST.get('email')
            student.contact_number = request.POST.get('contact_number')
            student.batch = Batch.objects.get(id=request.POST.get('batch'))
            student.semester = Semester.objects.get(id=request.POST.get('semester'))
            student.section = Section.objects.get(id=request.POST.get('section'))
            student.address = request.POST.get('address')

            
            # Handle parent update
            if student.parent:
                student.parent.father_name = request.POST.get('father_name', '')
                student.parent.mother_name = request.POST.get('mother_name', '')
                student.parent.father_email = request.POST.get('father_email', '')
                student.parent.father_contact = request.POST.get('father_contact', '')
                student.parent.address = request.POST.get('parent_address', '')
                student.parent.save()
                
            
            # Handle image upload
            if 'image' in request.FILES:
                student.image = request.FILES['image']
            
            student.save()
            messages.success(request, 'Student updated successfully!')
            return redirect('student_list')
            
        except Exception as e:
            messages.error(request, f'Error updating student: {str(e)}')
            print(f"Error: {str(e)}")
    
    return render(request, 'students/edit-student.html', {
        'student': student,
        'batches': batches,
        'semesters': semesters,
        'sections': sections,
        'gender_choices': Student.GENDER_CHOICES
    })

def delete_student(request, student_id):

    student = get_object_or_404(Student, id=student_id)
    if request.method == 'POST':
        try:
            # Delete parent if exists and no other students are linked
            if student.parent:
                student.parent.delete()
            student.delete()
            messages.success(request, 'Student deleted successfully!')
        except Exception as e:
            messages.error(request, f'Error deleting student: {str(e)}')
    return redirect('student_list')


def promote_student(request, student_id):
    student = get_object_or_404(Student, id=student_id)

    if request.method == 'POST':
        current_semester = student.semester

        if not current_semester:
            messages.error(request, 'Student has no current semester assigned.')
            return redirect('student_list')

        next_semester_number = current_semester.number + 1
        next_semester = Semester.objects.filter(number=next_semester_number).first()

        if next_semester:
            student.semester = next_semester
            student.save()
            messages.success(
                request,
                f'{student.first_name} {student.last_name} promoted to Semester {next_semester.number}.'
            )
        else:
            messages.warning(
                request,
                'No higher semester found. Promotion not possible.'
            )

    return redirect('student_list')
