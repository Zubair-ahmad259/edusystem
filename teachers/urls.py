from django.contrib import admin
from django.urls import path,include
from . import views

urlpatterns = [
  path("", views.teacher_list, name="teacher_list"),
  path("add/",views.add_teacher, name="add_teacher"),
  path('view-teacher/<int:teacher_id>/', views.view_teacher, name="view_teacher"),
  path("edit/<str:teacher_id>/", views.edit_teacher, name="edit_teacher"),
      #  path("edit/<str:slug>/", views.edit_teacher, name="edit_teacher")
    #  path("delete/<str:slug>/",views.delete_student, name="delete_student")

  



]

