from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .constants import MovementAction, RequestStatus, RequestType
from .forms import (
    BmtRequestCreateForm,
    BmtRequestUpdateForm,
    ChangeHospitalForm,
    LetterDeliveryForm,
    PatientContactForm,
    RecordReturnForm,
    SendForApprovalForm,
)
from .models import BmtRequest, MemoMovement
from .operations import can_change_hospital, record_memo_movement


@login_required
def dashboard(request):
    """
    لوحة تحكم لجنة زرع النخاع وعقار ATG
    تعرض إحصائيات سريعة للطلبات وسجل الحركات الأخيرة
    """
    requests_qs = BmtRequest.objects.all()

    stats = {
        "total": requests_qs.count(),
        "draft": requests_qs.filter(status=RequestStatus.DRAFT).count(),
        "sent_for_approval": requests_qs.filter(status=RequestStatus.SENT_FOR_APPROVAL).count(),
        "approved": requests_qs.filter(
            status__in=[
                RequestStatus.APPROVED,
                RequestStatus.PENDING_PATIENT_CONTACT,
                RequestStatus.PATIENT_CONTACTED,
                RequestStatus.LETTER_DELIVERED,
                RequestStatus.COMPLETED,
            ]
        ).count(),
        "rejected": requests_qs.filter(status=RequestStatus.REJECTED).count(),
        "atg_pending_contact": requests_qs.filter(
            request_type=RequestType.ATG,
            status=RequestStatus.PENDING_PATIENT_CONTACT
        ).count(),
        "atg_pending_delivery": requests_qs.filter(
            request_type=RequestType.ATG,
            status=RequestStatus.PATIENT_CONTACTED
        ).count(),
        "completed": requests_qs.filter(
            status__in=[RequestStatus.COMPLETED, RequestStatus.LETTER_DELIVERED]
        ).count(),
    }

    recent_requests = (
        requests_qs
        .select_related("patient", "hospital")
        .order_by("-created_at")[:8]
    )

    recent_movements = (
        MemoMovement.objects
        .select_related("request__patient", "created_by")
        .order_by("-moved_at")[:10]
    )

    return render(
        request,
        "bmt_committee/dashboard.html",
        {
            "stats": stats,
            "recent_requests": recent_requests,
            "recent_movements": recent_movements,
        }
    )


@login_required
def request_list(request):
    """
    قائمة طلبات ومذكرات زرع النخاع و ATG مع فلاتر وبحث متقدم
    """
    queryset = (
        BmtRequest.objects
        .select_related("patient", "hospital")
        .order_by("-created_at")
    )

    search = request.GET.get("search", "").strip()
    request_type = request.GET.get("type", "").strip()
    status = request.GET.get("status", "").strip()

    if search:
        queryset = queryset.filter(
            Q(patient__full_name__icontains=search)
            | Q(patient__national_id__icontains=search)
            | Q(request_code__icontains=search)
            | Q(manual_outgoing_number__icontains=search)
            | Q(manual_incoming_number__icontains=search)
        )

    if request_type and request_type in RequestType.values:
        queryset = queryset.filter(request_type=request_type)

    if status and status in RequestStatus.values:
        queryset = queryset.filter(status=status)

    paginator = Paginator(queryset, 25)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "bmt_committee/request_list.html",
        {
            "requests": page_obj,
            "page_obj": page_obj,
            "search": search,
            "selected_type": request_type,
            "selected_status": status,
            "request_types": RequestType.choices,
            "request_statuses": RequestStatus.choices,
        }
    )


@login_required
def request_create(request):
    """
    إنشاء طلب ومذكرة جديدة (زرع نخاع أو ATG)
    """
    if request.method == "POST":
        form = BmtRequestCreateForm(request.POST)
        if form.is_valid():
            bmt_request = form.save(user=request.user)
            messages.success(
                request,
                f"تم إنشاء طلب المذكرة بنجاح بكود: {bmt_request.request_code} للمريض {bmt_request.patient.full_name}."
            )
            return redirect("bmt_committee:request_detail", pk=bmt_request.pk)
    else:
        form = BmtRequestCreateForm()

    return render(
        request,
        "bmt_committee/request_form.html",
        {
            "form": form,
            "title": "إعداد طلب ومذكرة جديدة",
            "is_create": True,
        }
    )


@login_required
def request_detail(request, pk):
    """
    استعراض تفاصيل طلب ومذكرة زرع النخاع / ATG مع الخط الزمني للحركات
    """
    bmt_request = get_object_or_404(
        BmtRequest.objects
        .select_related("patient", "hospital")
        .prefetch_related("movements__created_by"),
        pk=pk
    )

    # التحقق من إمكانية تغيير المستشفى بناءً على القواعد
    can_change_hosp = False
    if bmt_request.request_type in [RequestType.AUTOLOGOUS, RequestType.FULLY_MATCHED]:
        can_change_hosp = True

    return render(
        request,
        "bmt_committee/request_detail.html",
        {
            "request_obj": bmt_request,
            "can_change_hosp": can_change_hosp,
            "RequestStatus": RequestStatus,
            "RequestType": RequestType,
        }
    )


@login_required
def request_update(request, pk):
    """
    تعديل بيانات طلب ومذكرة قائمة
    """
    bmt_request = get_object_or_404(BmtRequest, pk=pk)

    if request.method == "POST":
        form = BmtRequestUpdateForm(request.POST, instance=bmt_request)
        if form.is_valid():
            form.save(user=request.user)
            messages.success(request, "تم تحديث بيانات الطلب والمذكرة بنجاح.")
            return redirect("bmt_committee:request_detail", pk=bmt_request.pk)
    else:
        form = BmtRequestUpdateForm(instance=bmt_request)

    return render(
        request,
        "bmt_committee/request_form.html",
        {
            "form": form,
            "bmt_request": bmt_request,
            "title": f"تعديل بيانات الطلب {bmt_request.request_code}",
            "is_create": False,
        }
    )


@login_required
def send_for_approval(request, pk):
    """
    تسجيل إرسال المذكرة للاعتماد من السلطة المختصة
    """
    bmt_request = get_object_or_404(BmtRequest, pk=pk)

    if request.method == "POST":
        form = SendForApprovalForm(request.POST)
        if form.is_valid():
            bmt_request.memo_date = form.cleaned_data["memo_date"]
            if form.cleaned_data["manual_outgoing_number"]:
                bmt_request.manual_outgoing_number = form.cleaned_data["manual_outgoing_number"]
            if form.cleaned_data["manual_outgoing_date"]:
                bmt_request.manual_outgoing_date = form.cleaned_data["manual_outgoing_date"]
            bmt_request.save(update_fields=[
                "memo_date",
                "manual_outgoing_number",
                "manual_outgoing_date",
                "updated_at",
            ])

            record_memo_movement(
                bmt_request=bmt_request,
                action=MovementAction.SENT_FOR_APPROVAL,
                to_status=RequestStatus.SENT_FOR_APPROVAL,
                destination="رئيس الإدارة المركزية للشئون الطبية",
                notes=form.cleaned_data["notes"] or "تم إرسال المذكرة للاعتماد.",
                user=request.user,
            )

            messages.success(request, "تم تسجيل إرسال المذكرة للاعتماد بنجاح.")
            return redirect("bmt_committee:request_detail", pk=bmt_request.pk)
    else:
        initial = {
            "memo_date": bmt_request.memo_date,
            "manual_outgoing_number": bmt_request.manual_outgoing_number,
            "manual_outgoing_date": bmt_request.manual_outgoing_date,
        }
        form = SendForApprovalForm(initial=initial)

    return render(
        request,
        "bmt_committee/actions/send_for_approval.html",
        {
            "form": form,
            "bmt_request": bmt_request,
        }
    )


@login_required
def record_return(request, pk):
    """
    تسجيل ورود المذكرة من السلطة المختصة (معتمدة أو مرفوضة)
    """
    bmt_request = get_object_or_404(BmtRequest, pk=pk)

    if request.method == "POST":
        form = RecordReturnForm(request.POST)
        if form.is_valid():
            decision = form.cleaned_data["decision"]
            incoming_no = form.cleaned_data["manual_incoming_number"]
            incoming_date = form.cleaned_data["manual_incoming_date"]
            rejection_reason = form.cleaned_data["rejection_reason"]
            notes = form.cleaned_data["notes"]

            if incoming_no:
                bmt_request.manual_incoming_number = incoming_no
            bmt_request.manual_incoming_date = incoming_date

            if decision == "APPROVED":
                # مسار ATG ينتقل لحالة بانتظار التواصل مع المريض
                if bmt_request.request_type == RequestType.ATG:
                    to_status = RequestStatus.PENDING_PATIENT_CONTACT
                    action = MovementAction.APPROVED
                    action_msg = "تم اعتماد المذكرة. الحالة الآن بانتظار التواصل مع المريض."
                else:
                    # مسار زرع النخاع
                    to_status = RequestStatus.APPROVED
                    action = MovementAction.APPROVED
                    action_msg = f"تم اعتماد المذكرة وتوجيهها إلى: {bmt_request.routing_destination}."
            else:
                to_status = RequestStatus.REJECTED
                action = MovementAction.REJECTED
                bmt_request.rejection_reason = rejection_reason
                action_msg = "تم تسجيل رفض المذكرة."

            bmt_request.save(update_fields=[
                "manual_incoming_number",
                "manual_incoming_date",
                "rejection_reason",
                "updated_at",
            ])

            record_memo_movement(
                bmt_request=bmt_request,
                action=action,
                to_status=to_status,
                destination=bmt_request.routing_destination if decision == "APPROVED" else "",
                notes=notes or rejection_reason or "تم تسجيل قرار المذكرة.",
                user=request.user,
            )

            messages.success(request, action_msg)
            return redirect("bmt_committee:request_detail", pk=bmt_request.pk)
    else:
        initial = {
            "manual_incoming_number": bmt_request.manual_incoming_number,
            "manual_incoming_date": bmt_request.manual_incoming_date,
        }
        form = RecordReturnForm(initial=initial)

    return render(
        request,
        "bmt_committee/actions/record_return.html",
        {
            "form": form,
            "bmt_request": bmt_request,
        }
    )


@login_required
def change_hospital(request, pk):
    """
    تعديل المستشفى المعالج للحالات المسموح بها (ذاتي ومتطابق كلياً)
    مع التحقق من تطابق السعر وتوثيق الحركة بالسجل
    """
    bmt_request = get_object_or_404(BmtRequest, pk=pk)

    if request.method == "POST":
        form = ChangeHospitalForm(request.POST, bmt_request=bmt_request)
        if form.is_valid():
            old_hospital_name = bmt_request.hospital.name
            new_hospital = form.cleaned_data["new_hospital"]
            reason = form.cleaned_data["change_reason"]

            bmt_request.hospital = new_hospital
            bmt_request.save(update_fields=["hospital", "updated_at"])

            record_memo_movement(
                bmt_request=bmt_request,
                action=MovementAction.HOSPITAL_CHANGED,
                to_status=bmt_request.status,
                notes=f"تم تعديل المستشفى من [{old_hospital_name}] إلى [{new_hospital.name}]. السبب: {reason}",
                user=request.user,
            )

            messages.success(
                request,
                f"تم تعديل المستشفى المعالج بنجاح إلى: {new_hospital.name} وتوثيق الحركة بالسجل."
            )
            return redirect("bmt_committee:request_detail", pk=bmt_request.pk)
    else:
        form = ChangeHospitalForm(bmt_request=bmt_request)

    return render(
        request,
        "bmt_committee/actions/change_hospital.html",
        {
            "form": form,
            "bmt_request": bmt_request,
        }
    )


@login_required
def record_patient_contact(request, pk):
    """
    تسجيل التواصل مع مريض ATG وتجهيز الخطاب الموجه للمستشفى
    """
    bmt_request = get_object_or_404(
        BmtRequest,
        pk=pk,
        request_type=RequestType.ATG
    )

    if request.method == "POST":
        form = PatientContactForm(request.POST)
        if form.is_valid():
            bmt_request.patient_contacted_at = form.cleaned_data["contacted_at"]
            bmt_request.hospital_letter_number = form.cleaned_data["hospital_letter_number"]
            bmt_request.hospital_letter_date = form.cleaned_data["hospital_letter_date"]
            bmt_request.save(update_fields=[
                "patient_contacted_at",
                "hospital_letter_number",
                "hospital_letter_date",
                "updated_at",
            ])

            record_memo_movement(
                bmt_request=bmt_request,
                action=MovementAction.PATIENT_CONTACTED,
                to_status=RequestStatus.PATIENT_CONTACTED,
                notes=f"تم التواصل وتجهيز خطاب المستشفى برقم {bmt_request.hospital_letter_number}. ملاحظات: {form.cleaned_data['notes']}",
                user=request.user,
            )

            messages.success(request, "تم تسجيل التواصل مع المريض وتجهيز بيانات الخطاب بنجاح.")
            return redirect("bmt_committee:request_detail", pk=bmt_request.pk)
    else:
        initial = {
            "patient_contacted_at": bmt_request.patient_contacted_at,
            "hospital_letter_number": bmt_request.hospital_letter_number,
            "hospital_letter_date": bmt_request.hospital_letter_date,
        }
        form = PatientContactForm(initial=initial)

    return render(
        request,
        "bmt_committee/actions/record_patient_contact.html",
        {
            "form": form,
            "bmt_request": bmt_request,
        }
    )


@login_required
def record_letter_delivery(request, pk):
    """
    تسجيل تسليم الخطاب الرسمي للمريض / ولي أمره (عقار ATG)
    """
    bmt_request = get_object_or_404(
        BmtRequest,
        pk=pk,
        request_type=RequestType.ATG
    )

    if request.method == "POST":
        form = LetterDeliveryForm(request.POST)
        if form.is_valid():
            delivered_at = form.cleaned_data["delivered_at"]
            recipient = form.cleaned_data["recipient_name"]
            rel = form.cleaned_data["recipient_relation"]
            notes = form.cleaned_data["notes"]

            bmt_request.letter_delivered_at = delivered_at
            bmt_request.save(update_fields=["letter_delivered_at", "updated_at"])

            rel_text = f" ({rel})" if rel else ""
            notes_full = f"تم تسليم الخطاب إلى: {recipient}{rel_text}. {notes}".strip()

            record_memo_movement(
                bmt_request=bmt_request,
                action=MovementAction.LETTER_DELIVERED,
                to_status=RequestStatus.LETTER_DELIVERED,
                destination="المريض / ولي الأمر",
                notes=notes_full,
                user=request.user,
            )

            messages.success(request, "تم تسجيل تسليم الخطاب للمريض بنجاح واكتمال الدورة.")
            return redirect("bmt_committee:request_detail", pk=bmt_request.pk)
    else:
        initial = {
            "delivered_at": bmt_request.letter_delivered_at,
            "recipient_name": bmt_request.guardian_name or bmt_request.patient.full_name,
            "recipient_relation": bmt_request.guardian_relation or "نفسه",
        }
        form = LetterDeliveryForm(initial=initial)

    return render(
        request,
        "bmt_committee/actions/record_letter_delivery.html",
        {
            "form": form,
            "bmt_request": bmt_request,
        }
    )
