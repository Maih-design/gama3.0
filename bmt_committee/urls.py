from django.urls import path
from . import views

app_name = "bmt_committee"

urlpatterns = [
    path("", views.bmt_home, name="bmt_home"),
    path("home/", views.bmt_home, name="bmt_home_alt"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("requests/", views.request_list, name="request_list"),
    path("requests/create/", views.request_create, name="request_create"),
    path("requests/<int:pk>/", views.request_detail, name="request_detail"),
    path("requests/<int:pk>/edit/", views.request_update, name="request_update"),
    path("requests/<int:pk>/send/", views.send_for_approval, name="send_for_approval"),
    path("requests/<int:pk>/return/", views.record_return, name="record_return"),
    path("requests/<int:pk>/change-hospital/", views.change_hospital, name="change_hospital"),
    path("requests/<int:pk>/handover-social-services/", views.handover_to_social_services, name="handover_social_services"),
    path("requests/<int:pk>/route-memo/", views.route_memo, name="route_memo"),
    path("requests/<int:pk>/print/memo/", views.memo_print, name="memo_print"),
    path("api/patient-lookup/", views.patient_lookup, name="patient_lookup"),
]
