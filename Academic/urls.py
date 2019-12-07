from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('',views.add_batch,name='add_batch'),
    path('add_section',views.add_section,name='add_section'),
    path('add_semester',views.add_semester,name='add_semester'),
    path('view_semester',views.view_semester,name='view_semester'),
    path('view_batch',views.view_batch,name='view_batch'),
    path('edit_batch/<int:batch_id>/', views.edit_batch, name='edit_batch'),
    path('delete_batch/<int:batch_id>/', views.delete_batch, name='delete_batch'),
    path('add_section', views.add_section, name='add_section'),
    path('view_section', views.view_section, name='view_section'),
    path('add_discipline', views.add_discipline, name='add_discipline'),
    path('view_discipline/', views.view_discipline, name='view_discipline'),
    path('edit_section/<int:section_id>/', views.edit_section, name='edit_section'),
    path('delete_section/<int:section_id>/', views.delete_section, name='delete_section'),
    path('edit_semester/<int:semester_id>/', views.edit_semester, name='edit_semester'),
    path('delete_semester/<int:semester_id>/', views.delete_semester, name='delete_semester'),
    path('edit_discipline/<int:discipline_id>/', views.edit_discipline, name='edit_discipline'),
    path('delete_discipline/<int:discipline_id>/', views.delete_discipline, name='delete_discipline'),



]
