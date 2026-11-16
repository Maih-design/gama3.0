from decimal import Decimal
from django import forms
from django.core.exceptions import ValidationError

from committee.models import Patient, ReferralCenter
from .constants import MovementAction, PaymentType, RequestStatus, RequestType
from .models import BmtRequest, HospitalServicePrice
from .operations import (
    calculate_atg_dose,
    can_change_hospital,
    determine_bmt_financials,
    determine_memo_routing,
    generate_request_code,
    record_memo_movement,
)


class BaseStyledForm(forms.ModelForm):
    """تطبيق تنسيقات الحقول الموحدة للمشروع"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs["class"] = "form-select"
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs["class"] = "form-textarea"
            else:
                field.widget.attrs["class"] = "form-input"


class BmtRequestCreateForm(BaseStyledForm):
    patient = forms.ModelChoiceField(
        queryset=Patient.objects.all().order_by("full_name"),
        label="المريض",
        empty_label="-- اختر المريض --",
    )
    hospital = forms.ModelChoiceField(
        queryset=ReferralCenter.objects.filter(for_bone_marrow=True).order_by("name"),
        label="المستشفى / المركز المعالج",
        empty_label="-- اختر المستشفى --",
    )

    class Meta:
        model = BmtRequest
        fields = [
            "patient",
            "request_type",
            "hospital",
            "referring_clinic_or_committee",
            "hla_lab_name",
            "external_approval_number",
            "external_approval_date",
            "hospital_initial_cost",
            "guardian_name",
            "guardian_relation",
            "patient_weight",
            "memo_date",
            "manual_outgoing_number",
            "manual_outgoing_date",
        ]
        labels = {
            "request_type": "نوع الإجراء / الطلب",
            "referring_clinic_or_committee": "اللجنة أو العيادة المحيلة",
            "hla_lab_name": "معمل توافق الأنسجة",
            "external_approval_number": "رقم إفادة/موافقة المستشفى أو اللجنة",
            "external_approval_date": "تاريخ الإفادة أو الموافقة",
            "hospital_initial_cost": "التكلفة المبدئية بإفادة المستشفى (إن وجدت)",
            "guardian_name": "اسم ولي الأمر / القريب",
            "guardian_relation": "صلة القرابة",
            "patient_weight": "وزن المريض (كجم) - مطلوب لعقار ATG",
            "memo_date": "تاريخ العرض / المذكرة",
            "manual_outgoing_number": "رقم الصادر الدفتري (إن وجد)",
            "manual_outgoing_date": "تاريخ الصادر الدفتري (إن وجد)",
        }
        widgets = {
            "external_approval_date": forms.DateInput(attrs={"type": "date"}),
            "memo_date": forms.DateInput(attrs={"type": "date"}),
            "manual_outgoing_date": forms.DateInput(attrs={"type": "date"}),
            "patient_weight": forms.NumberInput(attrs={"step": "0.1", "placeholder": "مثال: 20"}),
            "hospital_initial_cost": forms.NumberInput(attrs={"step": "1", "placeholder": "مثال: 700000"}),
            "referring_clinic_or_committee": forms.TextInput(attrs={"placeholder": "مثال: لجنة أمراض الدم عيادة المقطم"}),
            "hla_lab_name": forms.TextInput(attrs={"placeholder": "مثال: معمل البرج"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        request_type = cleaned_data.get("request_type")
        patient_weight = cleaned_data.get("patient_weight")

        if request_type == RequestType.ATG:
            if not patient_weight or patient_weight <= Decimal("0"):
                self.add_error("patient_weight", "وزن المريض مطلوب وأكبر من صفر لحساب جرعة عقار ATG.")

        return cleaned_data

    def save(self, commit=True, user=None):
        instance = super().save(commit=False)

        if not instance.request_code:
            instance.request_code = generate_request_code()

        # احتساب الحسابات المالية والقيم التاريخية
        if instance.request_type == RequestType.ATG:
            calc = calculate_atg_dose(instance.patient_weight)
            instance.atg_total_mg = calc["total_mg"]
            instance.atg_dose_ampules = calc["ampules"]
            instance.atg_ampule_price = calc["ampule_price"]
            instance.approved_amount = calc["total_cost"]
            instance.amount_in_words = calc["cost_in_words"]
            instance.payment_type = PaymentType.SINGLE
            instance.installment_1 = calc["total_cost"]
            instance.installment_2 = Decimal("0.00")
        else:
            fin = determine_bmt_financials(instance.request_type, instance.hospital)
            instance.approved_amount = fin["approved_amount"]
            instance.amount_in_words = fin["amount_in_words"]
            instance.payment_type = fin["payment_type"]
            instance.installment_1 = fin["installment_1"]
            instance.installment_2 = fin["installment_2"]

        instance.routing_destination = determine_memo_routing(
            instance.request_type,
            instance.patient.get_affiliated_branch_display()
        )
        instance.status = RequestStatus.DRAFT

        if commit:
            instance.save()
            record_memo_movement(
                bmt_request=instance,
                action=MovementAction.CREATED,
                to_status=RequestStatus.DRAFT,
                destination=instance.routing_destination,
                notes="تم إنشاء الطلب واحتساب المذكرة المالية آلياً.",
                user=user,
            )

        return instance


class BmtRequestUpdateForm(BaseStyledForm):
    hospital = forms.ModelChoiceField(
        queryset=ReferralCenter.objects.filter(for_bone_marrow=True).order_by("name"),
        label="المستشفى / المركز المعالج",
    )

    class Meta:
        model = BmtRequest
        fields = [
            "hospital",
            "referring_clinic_or_committee",
            "hla_lab_name",
            "external_approval_number",
            "external_approval_date",
            "hospital_initial_cost",
            "guardian_name",
            "guardian_relation",
            "patient_weight",
            "memo_date",
            "manual_outgoing_number",
            "manual_outgoing_date",
            "manual_incoming_number",
            "manual_incoming_date",
        ]
        labels = {
            "hospital": "المستشفى / المركز المعالج",
            "referring_clinic_or_committee": "اللجنة أو العيادة المحيلة",
            "hla_lab_name": "معمل توافق الأنسجة",
            "external_approval_number": "رقم إفادة/موافقة المستشفى أو اللجنة",
            "external_approval_date": "تاريخ الإفادة أو الموافقة",
            "hospital_initial_cost": "التكلفة المبدئية بإفادة المستشفى",
            "guardian_name": "اسم ولي الأمر / القريب",
            "guardian_relation": "صلة القرابة",
            "patient_weight": "وزن المريض (كجم)",
            "memo_date": "تاريخ العرض / المذكرة",
            "manual_outgoing_number": "رقم الصادر الدفتري",
            "manual_outgoing_date": "تاريخ الصادر الدفتري",
            "manual_incoming_number": "رقم الوارد الدفتري",
            "manual_incoming_date": "تاريخ الوارد الدفتري",
        }
        widgets = {
            "external_approval_date": forms.DateInput(attrs={"type": "date"}),
            "memo_date": forms.DateInput(attrs={"type": "date"}),
            "manual_outgoing_date": forms.DateInput(attrs={"type": "date"}),
            "manual_incoming_date": forms.DateInput(attrs={"type": "date"}),
            "patient_weight": forms.NumberInput(attrs={"step": "0.1"}),
            "hospital_initial_cost": forms.NumberInput(attrs={"step": "1"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        if self.instance.request_type == RequestType.ATG:
            weight = cleaned_data.get("patient_weight")
            if not weight or weight <= Decimal("0"):
                self.add_error("patient_weight", "وزن المريض مطلوب لعقار ATG.")
        return cleaned_data

    def save(self, commit=True, user=None):
        instance = super().save(commit=False)
        # إذا تم تحديث وزن مريض ATG في حالة مسودة، يتم إعادة احتساب الجرعة
        if instance.request_type == RequestType.ATG and instance.status == RequestStatus.DRAFT:
            calc = calculate_atg_dose(instance.patient_weight)
            instance.atg_total_mg = calc["total_mg"]
            instance.atg_dose_ampules = calc["ampules"]
            instance.atg_ampule_price = calc["ampule_price"]
            instance.approved_amount = calc["total_cost"]
            instance.amount_in_words = calc["cost_in_words"]
            instance.installment_1 = calc["total_cost"]

        if commit:
            instance.save()
            record_memo_movement(
                bmt_request=instance,
                action=MovementAction.UPDATED,
                to_status=instance.status,
                notes="تم تحديث بيانات الطلب والمذكرة.",
                user=user,
            )

        return instance


class SendForApprovalForm(forms.Form):
    memo_date = forms.DateField(
        label="تاريخ العرض / المذكرة",
        widget=forms.DateInput(attrs={"type": "date", "class": "form-input"}),
        required=True,
    )
    manual_outgoing_number = forms.CharField(
        label="رقم الصادر الدفتري",
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "أدخل رقم الصادر في الدفاتر"}),
    )
    manual_outgoing_date = forms.DateField(
        label="تاريخ الصادر الدفتري",
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-input"}),
    )
    notes = forms.CharField(
        label="ملاحظات الإرسال",
        required=False,
        widget=forms.Textarea(attrs={"class": "form-textarea", "rows": 3, "placeholder": "ملاحظات إضافية حول الإرسال للعرض"}),
    )


class RecordReturnForm(forms.Form):
    DECISION_CHOICES = (
        ("APPROVED", "معتمدة (الموافقة على المذكرة)"),
        ("REJECTED", "مرفوضة (عدم الموافقة على المذكرة)"),
    )

    decision = forms.ChoiceField(
        choices=DECISION_CHOICES,
        label="قرار السلطة المختصة",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    manual_incoming_number = forms.CharField(
        label="رقم الوارد الدفتري",
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "أدخل رقم الوارد في الدفاتر"}),
    )
    manual_incoming_date = forms.DateField(
        label="تاريخ ورود المذكرة",
        required=True,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-input"}),
    )
    rejection_reason = forms.CharField(
        label="سبب الرفض (إلزامي في حال الرفض)",
        required=False,
        widget=forms.Textarea(attrs={"class": "form-textarea", "rows": 3, "placeholder": "اكتب سبب الرفض بالتفصيل"}),
    )
    notes = forms.CharField(
        label="ملاحظات وتأشيرة السلطة المختصة",
        required=False,
        widget=forms.Textarea(attrs={"class": "form-textarea", "rows": 3, "placeholder": "أي تأشيرات أو ملاحظات واردة مع المذكرة"}),
    )

    def clean(self):
        cleaned_data = super().clean()
        decision = cleaned_data.get("decision")
        rejection_reason = cleaned_data.get("rejection_reason")

        if decision == "REJECTED" and not rejection_reason:
            self.add_error("rejection_reason", "يجب كتابة سبب الرفض عند اختيار قرار الرفض.")

        return cleaned_data


class ChangeHospitalForm(forms.Form):
    new_hospital = forms.ModelChoiceField(
        queryset=ReferralCenter.objects.filter(for_bone_marrow=True).order_by("name"),
        label="المستشفى البديل",
        empty_label="-- اختر المستشفى البديل --",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    change_reason = forms.CharField(
        label="مبرر وملاحظات تغيير المستشفى",
        required=True,
        widget=forms.Textarea(attrs={"class": "form-textarea", "rows": 3, "placeholder": "اكتب سبب التغيير بناءً على قرار اللجنة أو رغبة المنتفع"}),
    )

    def __init__(self, *args, bmt_request=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.bmt_request = bmt_request
        if bmt_request:
            # استبعاد المستشفى الحالي من القائمة
            self.fields["new_hospital"].queryset = (
                ReferralCenter.objects
                .filter(for_bone_marrow=True)
                .exclude(pk=bmt_request.hospital_id)
                .order_by("name")
            )

    def clean_new_hospital(self):
        new_hospital = self.cleaned_data.get("new_hospital")
        if self.bmt_request:
            can_change, reason = can_change_hospital(self.bmt_request, new_hospital)
            if not can_change:
                raise ValidationError(reason)
        return new_hospital


class PatientContactForm(forms.Form):
    contacted_at = forms.DateTimeField(
        label="تاريخ ووقت التواصل مع المريض",
        widget=forms.DateTimeInput(attrs={"type": "datetime-local", "class": "form-input"}),
        required=True,
    )
    hospital_letter_number = forms.CharField(
        label="رقم الخطاب الموجه للمستشفى",
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "أدخل رقم الخطاب الرسمي"}),
    )
    hospital_letter_date = forms.DateField(
        label="تاريخ الخطاب",
        widget=forms.DateInput(attrs={"type": "date", "class": "form-input"}),
        required=True,
    )
    notes = forms.CharField(
        label="ملاحظات التواصل",
        required=False,
        widget=forms.Textarea(attrs={"class": "form-textarea", "rows": 3, "placeholder": "تفاصيل الاتصال بالمريض أو ولي أمره وتأكيد موعد استلام الخطاب"}),
    )


class LetterDeliveryForm(forms.Form):
    delivered_at = forms.DateTimeField(
        label="تاريخ ووقت تسليم الخطاب",
        widget=forms.DateTimeInput(attrs={"type": "datetime-local", "class": "form-input"}),
        required=True,
    )
    recipient_name = forms.CharField(
        label="اسم المستلم",
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "اسم المريض أو ولي الأمر المستلم"}),
    )
    recipient_relation = forms.CharField(
        label="صلة القرابة (إن وجد)",
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "نفسه / الأب / الأخ / الزوج ..."}),
    )
    notes = forms.CharField(
        label="ملاحظات التسليم",
        required=False,
        widget=forms.Textarea(attrs={"class": "form-textarea", "rows": 3, "placeholder": "أي ملاحظات إضافية أثناء التسليم"}),
    )
