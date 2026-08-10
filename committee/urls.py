from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("patients/", views.PatientListView.as_view(), name="patient_list"),
    path("patients/add/", views.patient_create, name="patient_create"),
    path("patients/<int:pk>/", views.patient_detail, name="patient_detail"),
    path("patients/<int:pk>/edit/", views.PatientUpdateView.as_view(), name="patient_update"),
    path("sessions/", views.CommitteeSessionListView.as_view(), name="session_list"),
    path("sessions/create/", views.CommitteeSessionCreateView.as_view(), name="session_create"),
    path("session/<int:pk>", views.CommitteeSessionDetailView.as_view(), name="session_detail"),
    path("patients/<int:pk>/add-to-session/", views.add_patient_to_session, name="add_patient_to_session"),
    path("sessions/<int:pk>/recommendations/", views.session_recommendations, name="session_recommendations"),
    path("referrals/pending/", views.pending_referrals, name="pending_referrals"),
    path("referrals/create/<int:case_pk>/", views.referral_create, name="referral_create"),
    path("referrals/<int:pk>/", views.referral_detail, name="referral_detail"),
    path("referrals/<int:pk>/print/", views.referral_print, name="referral_print"),
    path("cases/<int:case_pk>/recommendation/print/", views.recommendation_print, name="recommendation_print"),
    path("referrals/<int:pk>/edit/", views.referral_update, name="referral_update"),
    path("referrals/<int:pk>/cancel/", views.referral_cancel, name="referral_cancel"),
    path("sessions/<int:pk>/print/", views.session_print, name="session_print"),
    path("sessions/<int:pk>/complete/", views.session_complete, name="session_complete"),
]