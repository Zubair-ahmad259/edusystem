from django.contrib import admin
from django.urls import include, path
from . import  views

urlpatterns = [
      path('', views.add_student,name='add_student'),
      path('students/',views.student_list,name="student_list"),
      path('edit-student/<int:student_id>/', views.edit_student, name="edit_student"),
      path('view-student/<int:student_id>/', views.view_student, name="view_student"),
      path('delete-student/<int:student_id>/', views.delete_student, name="delete_student"),
      path('promote/<int:student_id>/', views.promote_student, name='promote_student'),

]
