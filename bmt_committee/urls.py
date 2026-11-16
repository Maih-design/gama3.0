from django.urls import path
from . import views

app_name = "bmt_committee"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("requests/", views.request_list, name="request_list"),
    path("requests/create/", views.request_create, name="request_create"),
    path("requests/<int:pk>/", views.request_detail, name="request_detail"),
    path("requests/<int:pk>/edit/", views.request_update, name="request_update"),
    path("requests/<int:pk>/send/", views.send_for_approval, name="send_for_approval"),
    path("requests/<int:pk>/return/", views.record_return, name="record_return"),
    path("requests/<int:pk>/change-hospital/", views.change_hospital, name="change_hospital"),
    path("requests/<int:pk>/contact-patient/", views.record_patient_contact, name="record_patient_contact"),
    path("requests/<int:pk>/deliver-letter/", views.record_letter_delivery, name="record_letter_delivery"),
]
