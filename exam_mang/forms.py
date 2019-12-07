# exam/forms.py\
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.db.models import Avg, Sum, Q, Count
from django.views.decorators.http import require_POST
from datetime import datetime, timedelta
from django.contrib.auth import get_user_model

from .models import (
    SubjectMarkComponents, Exam, ExamResult, 
    SubjectComprehensiveResult, Transcript
)
from student.models import Student
from Academic.models import Batch, Semester, Section, Discipline
from subject.models import Subject
from teachers.models import Teacher

from django import forms
from django.db.models import Q

class ComprehensiveResultFilterForm(forms.Form):
    batch = forms.ModelChoiceField(
        queryset=Batch.objects.none(),
        required=False,
        empty_label="All Batches",
        widget=forms.Select(attrs={'class': 'form-control select2'})
    )
    
    semester = forms.ModelChoiceField(
        queryset=Semester.objects.none(),
        required=False,
        empty_label="All Semesters",
        widget=forms.Select(attrs={'class': 'form-control select2'})
    )
    
    student = forms.ModelChoiceField(
        queryset=Student.objects.none(),
        required=False,
        empty_label="All Students",
        widget=forms.Select(attrs={'class': 'form-control select2'})
    )
    
    subject = forms.ModelChoiceField(
        queryset=Subject.objects.none(),
        required=False,
        empty_label="All Subjects",
        widget=forms.Select(attrs={'class': 'form-control select2'})
    )
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by name, ID, or subject...'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['batch'].queryset = Batch.objects.all().order_by('-start_year')
        self.fields['semester'].queryset = Semester.objects.all().order_by('number')
        self.fields['student'].queryset = Student.objects.all().order_by('student_id')
        self.fields['subject'].queryset = Subject.objects.all().order_by('code')