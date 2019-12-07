from django.shortcuts import render,redirect
from student.models import Student,Batch,Semester,Section,Parent


# Create your views here.
def add_student(request):
    batches = Batch.objects.all()
    semesters = Semester.objects.all()
    sections = Section.objects.all()
    parents = Parent.objects.all()
    if request.method == 'POST':
        try:
            parent=Parent(
                father_name=request.POST.get('fahter_name')  , 
                contect_no=request.POST.get('contect_no'),
                email=request.POST.get('email'),
                address=request.POST.get('address'),
                         )
            parent.save()
            student=Student(
                first_name =request.POST.get('first_name'),           
                last_name=request.POST.get('last_name'),
                roll_no =request.POST.get('roll_no'),
               student_phone  =request.POST.get('student_phone'),
               matric_marks=request.POST.get('matric_marks'),
               fsc_marks=request.POST.get('fsc_marks'),






            )
            student.save()
            return redirect('add_student')
        except Exception as e:
            error =str(e)
    return render(request,'add_student')



            
        


    
      
         

