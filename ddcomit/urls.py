from django.contrib import admin
from django.urls import path,include
from . import views

urlpatterns = [
    path("cases/", views.case_list, name="case_list"),
    path("cases/<int:case_id>/", views.case_detail, name="case_detail"),
    path("cases/add/", views.add_case, name="add_case"),
]
