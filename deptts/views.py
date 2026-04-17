from django.shortcuts import render
from django.http import HttpResponse

def index(request):
    return render(request, "authentication/login.html")
    #  return render(request, "Home/index.html")

def admin_dashboard(request):
    return render(request, "Home/index.html")


def student_dashboard(request):
    return render(request,"students/student-dashboard.html")

def teacher_dashboard(request):
    return render(request,"teacher/teacher_dashboard.html")
