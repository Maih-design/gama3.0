from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.views.generic import ListView, UpdateView, CreateView, DetailView
from .models import Patient, CommitteeSession, CommitteeCase, CommitteeRecommendation, ReferralCenter, Referral
from .forms import PatientForm, CommitteeSessionForm, ReferralForm, CommitteeRecommendationForm, ReferralCancelForm
from .constants import SessionStatus, CaseStatus, ReferralStatus
from django.db.models import Q
from django.db import transaction


def home(request):
    return render(request, "home.html")


class PatientListView(LoginRequiredMixin, ListView):
    model = Patient
    template_name = "patients/patient_list.html"
    context_object_name = "patients"
    paginate_by = 25

    def get_queryset(self):
        queryset = Patient.objects.all().order_by("full_name")

        search = self.request.GET.get("search", "").strip()

        if search:
            queryset = queryset.filter(
                Q(full_name__icontains=search)
                | Q(national_id__icontains=search)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        preparing_session = (
            CommitteeSession.objects
            .filter(status=SessionStatus.PREPARING)
            .first()
        )

        context["preparing_session"] = preparing_session

        if preparing_session:
            context["patients_in_session"] = set(
                preparing_session.cases.values_list(
                    "patient_id",
                    flat=True
                )
            )
        else:
            context["patients_in_session"] = set()

        return context


@login_required
def patient_create(request):
    if request.method == "POST":
        form = PatientForm(request.POST)

        if form.is_valid():
            patient = form.save()

            messages.success(
                request,
                f"تم إضافة المريض {patient.full_name} بنجاح."
            )

            return redirect("patient_detail", pk=patient.pk)

    else:
        form = PatientForm()

    return render(
        request,
        "patients/patient_form.html",
        {
            "form": form,
            "title": "إضافة مريض جديد",
        }
    )


@login_required
def patient_detail(request, pk):
    patient = get_object_or_404(Patient, pk=pk)

    return render(
        request,
        "patients/patient_detail.html",
        {
            "patient": patient,
        }
    )
    
class PatientUpdateView(LoginRequiredMixin, UpdateView):
    model = Patient
    form_class = PatientForm
    template_name = "patients/patient_form.html"

    def get_success_url(self):
        return reverse(
            "patient_detail",
            kwargs={"pk": self.object.pk}
        )
        
class CommitteeSessionListView(LoginRequiredMixin, ListView):
    model = CommitteeSession
    template_name = "sessions/session_list.html"
    context_object_name = "sessions"

    def get_queryset(self):
        return (
            CommitteeSession.objects
            .select_related("doctor")
            .order_by("-session_date")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["preparing_session"] = (
            CommitteeSession.objects
            .filter(status=SessionStatus.PREPARING)
            .select_related("doctor")
            .first()
        )

        return context
    
class CommitteeSessionCreateView(LoginRequiredMixin, CreateView):
    model = CommitteeSession
    form_class = CommitteeSessionForm
    template_name = "sessions/session_create.html"

    def form_valid(self, form):
        form.instance.status = SessionStatus.PREPARING

        messages.success(
            self.request,
            "تم إنشاء الجلسة بنجاح."
        )

        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            "session_detail",
            kwargs={"pk": self.object.pk}
        )
        
class CommitteeSessionDetailView(LoginRequiredMixin, DetailView):
    model = CommitteeSession
    template_name = "sessions/session_detail.html"
    context_object_name = "session"

    def get_queryset(self):
        return CommitteeSession.objects.select_related("doctor")
        
        
@login_required
def add_patient_to_session(request, pk):
    patient = get_object_or_404(Patient, pk=pk)

    session = CommitteeSession.objects.filter(
        status=SessionStatus.PREPARING
    ).first()

    if not session:
        messages.error(
            request,
            "لا توجد جلسة قيد التجهيز حاليًا."
        )
        return redirect("patient_detail", pk=patient.pk)

    CommitteeCase.objects.get_or_create(
        committee_session=session,
        patient=patient,
        defaults={
            "status": CaseStatus.PENDING
        }
    )

    messages.success(
        request,
        "تمت إضافة المريض إلى الجلسة المفتوحة."
    )

    return redirect(
        "patient_detail",
        pk=patient.pk
    )
    
@login_required
def session_recommendations(request, pk):

    session = get_object_or_404(
        CommitteeSession,
        pk=pk
    )

    cases = (
        session.cases
        .select_related(
            "patient",
            "recommendation",
        )
        .order_by("patient__full_name")
    )

    if request.method == "POST":

        saved_count = 0
        incomplete_count = 0

        for case in cases:

            prefix = f"case_{case.pk}"

            procedure_id = request.POST.get(
                f"{prefix}-procedure"
            )

            # لا يوجد إجراء → تجاهل الحالة
            if not procedure_id:
                incomplete_count += 1
                continue

            recommendation = getattr(
                case,
                "recommendation",
                None
            )

            form = CommitteeRecommendationForm(
                request.POST,
                instance=recommendation,
                prefix=prefix
            )

            if form.is_valid():

                recommendation = form.save(
                    commit=False
                )

                recommendation.committee_case = case
                recommendation.save()

                case.status = CaseStatus.APPROVED
                case.save(update_fields=["status"])

                saved_count += 1

        if incomplete_count:
            messages.warning(
                request,
                f"تم حفظ {saved_count} قرار، "
                f"وتوجد {incomplete_count} حالات لم يتم إدخال الإجراء لها."
            )
        else:
            messages.success(
                request,
                f"تم حفظ جميع القرارات ({saved_count} حالة) بنجاح."
            )

        return redirect(
            "session_recommendations",
            pk=session.pk
        )

    recommendation_forms = []

    for case in cases:

        recommendation = getattr(
            case,
            "recommendation",
            None
        )

        form = CommitteeRecommendationForm(
            instance=recommendation,
            prefix=f"case_{case.pk}"
        )

        recommendation_forms.append(
            {
                "case": case,
                "form": form,
            }
        )

    return render(
        request,
        "sessions/session_recommendations.html",
        {
            "session": session,
            "recommendation_forms": recommendation_forms,
        }
    )
    
@login_required
def pending_referrals(request):

    pending_cases = (
        CommitteeCase.objects
        .filter(
            recommendation__procedure__requires_referral=True,
            referrals__isnull=True,
        )
        .select_related(
            "patient",
            "committee_session",
            "recommendation",
            "recommendation__procedure",
        )
        .order_by(
            "committee_session__session_date",
            "patient__full_name",
        )
    )

    referrals = (
    Referral.objects
    .select_related(
        "committee_case__patient",
        "committee_case__committee_session",
        "committee_case__recommendation__procedure",
    )
    .order_by("-issued_at")
)

    return render(
    request,
    "referrals/pending_referrals.html",
    {
        "pending_cases": pending_cases,
        "referrals": referrals,
    }
)
    
@login_required
def referral_create(request, case_pk):

    case = get_object_or_404(
        CommitteeCase.objects.select_related(
            "patient",
            "committee_session",
            "recommendation",
            "recommendation__procedure",
        ),
        pk=case_pk
    )

    recommendation = getattr(
        case,
        "recommendation",
        None
    )

    if recommendation is None:
        messages.error(
            request,
            "لا يمكن إصدار خطاب تحويل قبل تسجيل توصية اللجنة."
        )

        return redirect(
            "patient_detail",
            pk=case.patient.pk
        )

    if request.method == "POST":

        form = ReferralForm(request.POST)

        if form.is_valid():

            referral = form.save(commit=False)

            referral.committee_case = case

            referral.save()

            messages.success(
                request,
                "تم إصدار خطاب التحويل بنجاح."
            )

            return redirect(
                "referral_detail",
                pk=referral.pk
            )

    else:

        form = ReferralForm()

    return render(
        request,
        "referrals/referral_create.html",
        {
            "case": case,
            "recommendation": recommendation,
            "form": form,
        }
    )    
    
@login_required
def referral_detail(request, pk):

    referral = get_object_or_404(
        Referral.objects.select_related(
            "committee_case",
            "committee_case__patient",
            "committee_case__recommendation",
            "committee_case__recommendation__procedure",
        ),
        pk=pk
    )

    return render(
        request,
        "referrals/referral_detail.html",
        {
            "referral": referral,
        }
    )
    
@login_required
def referral_print(request, pk):

    referral = get_object_or_404(
        Referral.objects.select_related(
            "committee_case",
            "committee_case__patient",
            "committee_case__recommendation",
            "committee_case__recommendation__procedure",
        ),
        pk=pk
    )

    return render(
        request,
        "referrals/referral_print.html",
        {
            "referral": referral,
        }
    )
    
@login_required
def recommendation_print(request, case_pk):

    case = get_object_or_404(
        CommitteeCase.objects.select_related(
            "patient",
            "committee_session",
            "recommendation",
            "recommendation__procedure",
        ),
        pk=case_pk
    )

    recommendation = getattr(
        case,
        "recommendation",
        None
    )

    if recommendation is None:

        messages.error(
            request,
            "لا توجد توصية مسجلة لهذه الحالة."
        )

        return redirect(
            "patient_detail",
            pk=case.patient.pk
        )

    return render(
        request,
        "sessions/recommendation_print.html",
        {
            "case": case,
            "recommendation": recommendation,
        }
    )

@login_required
def referral_update(request, pk):

    referral = get_object_or_404(
        Referral.objects.select_related(
            "committee_case",
            "committee_case__patient",
            "committee_case__recommendation",
            "committee_case__recommendation__procedure",
        ),
        pk=pk
    )

    if request.method == "POST":

        form = ReferralForm(
            request.POST,
            instance=referral
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "تم تعديل خطاب التحويل بنجاح."
            )

            return redirect(
                "referral_detail",
                pk=referral.pk
            )

    else:

        form = ReferralForm(
            instance=referral
        )

    return render(
        request,
        "referrals/referral_update.html",
        {
            "referral": referral,
            "form": form,
        }
    )
    
@login_required
def referral_cancel(request, pk):

    referral = get_object_or_404(
        Referral.objects.select_related(
            "committee_case",
            "committee_case__patient",
        ),
        pk=pk
    )

    if request.method == "POST":

        form = ReferralCancelForm(request.POST)

        if form.is_valid():

            referral.cancellation_reason = (
                form.cleaned_data["cancellation_reason"]
            )

            referral.status = ReferralStatus.CANCELLED

            referral.save(
                update_fields=[
                    "status",
                    "cancellation_reason",
                ]
            )

            messages.success(
                request,
                "تم إلغاء خطاب التحويل."
            )

            return redirect(
                "referral_detail",
                pk=referral.pk
            )

    else:

        form = ReferralCancelForm()

    return render(
        request,
        "referrals/referral_cancel.html",
        {
            "referral": referral,
            "form": form,
        }
    )
    
@login_required
def session_print(request, pk):

    session = get_object_or_404(
        CommitteeSession.objects
        .select_related("doctor")
        .prefetch_related(
            "cases__patient",
            "cases__recommendation__procedure",
        ),
        pk=pk
    )

    return render(
        request,
        "sessions/session_print.html",
        {
            "session": session,
        }
    )

@login_required
def session_complete(request, pk):

    session = get_object_or_404(
        CommitteeSession,
        pk=pk
    )

    cases = (
        session.cases
        .select_related(
            "patient",
            "recommendation",
            "recommendation__procedure",
        )
    )

    incomplete_cases = []

    for case in cases:

        recommendation = getattr(
            case,
            "recommendation",
            None
        )

        if (
            recommendation is None
            or recommendation.procedure_id is None
        ):
            incomplete_cases.append(case)


    if incomplete_cases:

        messages.error(
            request,
            f"لا يمكن إغلاق الجلسة. "
            f"هناك {len(incomplete_cases)} حالات لم يتم تسجيل الإجراء لها."
        )

        return redirect(
            "session_detail",
            pk=session.pk
        )


    session.status = SessionStatus.COMPLETED

    session.save(
        update_fields=["status"]
    )

    messages.success(
        request,
        "تم إغلاق الجلسة بنجاح."
    )

    return redirect(
        "session_detail",
        pk=session.pk
    )

