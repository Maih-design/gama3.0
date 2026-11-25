from decimal import Decimal
from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction

from committee.constants import Branches, Gender, InsuranceLaw
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
    # National ID lookup & registration
    national_id = forms.CharField(
        max_length=14,
        min_length=14,
        label="الرقم القومي للمريض (14 رقماً)",
        widget=forms.TextInput(attrs={
            "placeholder": "أدخل الرقم القومي للمريض المكون من 14 رقماً",
            "maxlength": "14",
            "autocomplete": "off",
        }),
    )
    existing_patient_id = forms.IntegerField(
        widget=forms.HiddenInput,
        required=False
    )

    # New patient registration fields (used if patient is not already registered)
    full_name = forms.CharField(
        max_length=200,
        label="اسم المريض بالكامل",
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "اسم المريض رباعياً"}),
    )
    gender = forms.ChoiceField(
        choices=[("", "-- اختر النوع --")] + list(Gender.choices),
        label="النوع",
        required=False,
    )
    insurance_law = forms.ChoiceField(
        choices=[("", "-- اختر قانون التأمين --")] + list(InsuranceLaw.choices),
        label="قانون التأمين",
        required=False,
    )
    insurance_number = forms.CharField(
        max_length=20,
        label="الرقم التأميني",
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "الرقم التأميني للمريض"}),
    )
    affiliated_branch = forms.ChoiceField(
        choices=[("", "-- اختر الفرع التابع له --")] + list(Branches.choices),
        label="الفرع التابع له",
        required=False,
    )
    phone_number = forms.CharField(
        max_length=20,
        label="رقم الهاتف",
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "رقم هاتف المريض أو ولي الأمر"}),
    )
    diagnosis = forms.CharField(
        label="التشخيص الطبي",
        required=False,
        widget=forms.Textarea(attrs={"placeholder": "التشخيص الطبي وتفاصيل الحالة", "rows": 2}),
    )

    hospital = forms.ModelChoiceField(
        queryset=ReferralCenter.objects.filter(for_bone_marrow=True).order_by("name"),
        label="المستشفى / المركز المعالج",
        empty_label="-- اختر المستشفى --",
    )

    class Meta:
        model = BmtRequest
        fields = [
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
        national_id = (cleaned_data.get("national_id") or "").strip()
        request_type = cleaned_data.get("request_type")
        patient_weight = cleaned_data.get("patient_weight")

        if not national_id:
            self.add_error("national_id", "الرقم القومي للمريض إلزامي.")
        elif len(national_id) != 14 or not national_id.isdigit():
            self.add_error("national_id", "الرقم القومي يجب أن يتكون من 14 رقماً صحيحاً.")
        else:
            # التحقق هل المريض مسجل مسبقاً بالنظام
            patient = Patient.objects.filter(national_id=national_id).first()
            if patient:
                self.patient_instance = patient
                self.is_new_patient = False
            else:
                self.patient_instance = None
                self.is_new_patient = True

                # التحقق من إدخال بيانات المريض الجديد الإلزامية
                new_patient_checks = [
                    ("full_name", "اسم المريض بالكامل إلزامي لتسجيل المريض الجديد."),
                    ("gender", "النوع إلزامي لتسجيل المريض الجديد."),
                    ("insurance_law", "قانون التأمين إلزامي لتسجيل المريض الجديد."),
                    ("insurance_number", "الرقم التأميني إلزامي لتسجيل المريض الجديد."),
                    ("affiliated_branch", "الفرع التابع له المريض إلزامي."),
                    ("diagnosis", "التشخيص الطبي إلزامي."),
                ]
                for f_name, f_err in new_patient_checks:
                    if not cleaned_data.get(f_name):
                        self.add_error(f_name, f_err)

        if request_type == RequestType.ATG:
            if not patient_weight or patient_weight <= Decimal("0"):
                self.add_error("patient_weight", "وزن المريض مطلوب وأكبر من صفر لحساب جرعة عقار ATG.")

        return cleaned_data

    def save(self, commit=True, user=None):
        instance = super().save(commit=False)

        with transaction.atomic():
            if getattr(self, "patient_instance", None):
                patient = self.patient_instance
            else:
                # إنشاء مريض جديد مشترك في قاعدة البيانات
                patient = Patient.objects.create(
                    national_id=self.cleaned_data["national_id"].strip(),
                    full_name=self.cleaned_data["full_name"].strip(),
                    gender=self.cleaned_data["gender"],
                    insurance_law=self.cleaned_data["insurance_law"],
                    insurance_number=self.cleaned_data["insurance_number"].strip(),
                    affiliated_branch=self.cleaned_data["affiliated_branch"],
                    phone_number=(self.cleaned_data.get("phone_number") or "").strip(),
                    diagnosis=self.cleaned_data["diagnosis"].strip(),
                )

            instance.patient = patient

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


class SocialServicesHandoverForm(forms.Form):
    handover_date = forms.DateField(
        label="تاريخ تسليم المذكرة للخدمة الاجتماعية",
        widget=forms.DateInput(attrs={"type": "date", "class": "form-input"}),
        required=True,
    )
    social_worker_name = forms.CharField(
        label="اسم مستلم الخدمة الاجتماعية / الأخصائي",
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "اسم الأخصائي الاجتماعي المستلم للإجراء"}),
    )
    notes = forms.CharField(
        label="ملاحظات التسليم",
        required=False,
        widget=forms.Textarea(attrs={"class": "form-textarea", "rows": 3, "placeholder": "أي ملاحظات إضافية حول تسليم المذكرة للخدمة الاجتماعية"}),
    )


class RouteMemoForm(forms.Form):
    dispatch_outgoing_number = forms.CharField(
        label="رقم صادر التوجيه (رقم الصادر الجديد)",
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            "class": "form-input",
            "placeholder": "أدخل رقم الصادر الجديد للمذكرة المتجهة للفرع أو الهيئة"
        }),
    )
    dispatch_outgoing_date = forms.DateField(
        label="تاريخ صادر التوجيه",
        required=True,
        widget=forms.DateInput(attrs={
            "type": "date",
            "class": "form-input"
        }),
    )
    notes = forms.CharField(
        label="ملاحظات وتفاصيل التوجيه",
        required=False,
        widget=forms.Textarea(attrs={
            "class": "form-textarea",
            "rows": 3,
            "placeholder": "رقم الحافظة، اسم المستلم، أو أي ملاحظات إدارية حول توجيه المذكرة"
        }),
    )

