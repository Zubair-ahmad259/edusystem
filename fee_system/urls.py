
from django.urls import path
from . import views

urlpatterns = [
    path("upload/", views.upload_fee, name="upload_fee"),
    path("clear/<int:fee_id>/", views.clear_fee, name="clear_fees"),
    path("list/", views.fee_list, name="fee_list"),
     path("defaulter_student/", views.defaulter_student, name="defaulter_student"),  
     path('student-fee-detail/<int:student_id>/', views.student_fee_detail,  name='student_fee_detail'),

    path('edit/<int:fee_id>/', views.edit_fee, name='edit_fee'),
    path('delete/<int:fee_id>/', views.delete_fee, name='delete_fee'),
    path('delete-ajax/<int:fee_id>/', views.delete_fee_ajax, name='delete_fee_ajax'),
    path('bulk-delete/', views.bulk_delete_fees, name='bulk_delete_fees'),
    path('export-fees-excel/', views.export_fees_excel, name='export_fees_excel'),
    path('export-defaulter-excel/', views.export_defaulter_excel, name='export_defaulter_excel'),

]
