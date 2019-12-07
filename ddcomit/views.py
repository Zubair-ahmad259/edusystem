from django.shortcuts import render, get_object_or_404, redirect
from .models import Cases
from django import forms


class CaseForm(forms.ModelForm):
    class Meta:
        model = Cases
        fields = ['case_type', 'student', 'teacher', 'subject', 'batch', 'semester', 'section','Disciplines','fine','status']

def case_list(request):
    cases = Cases.objects.all()
    return render(request, "cases/case_list.html", {"cases": cases})

def case_detail(request, case_id):
    case = get_object_or_404(Cases, id=case_id)
    return render(request, "cases/case_detail.html", {"case": case})
def add_case(request):
    if request.method == "POST":
        form = CaseForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("case_list")
    else:
        form = CaseForm()
    return render(request, "cases/add_case.html", {"form": form})
