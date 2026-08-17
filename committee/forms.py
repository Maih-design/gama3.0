from django import forms

from .models import (
    Patient,
    Procedure,
    Doctor,
    CommitteeSession,
    CommitteeRecommendation,
    ReferralCenter,
    Referral,
)


class PatientForm(forms.ModelForm):

    class Meta:
        model = Patient

        fields = [
            "national_id",
            "full_name",
            "gender",
            "insurance_law",
            "insurance_number",
            "phone_number",
            "affiliated_branch",
            "diagnosis",
        ]

        labels = {
            "national_id": "الرقم القومي",
            "full_name": "اسم المريض",
            "gender": "النوع",
            "insurance_law": "قانون التأمين",
            "insurance_number": "الرقم التأميني",
            "phone_number": "رقم الهاتف",
            "affiliated_branch": "الفرع التابع له",
            "diagnosis": "التشخيص",
        }

        widgets = {
            "national_id": forms.TextInput(
                attrs={
                    "placeholder": "أدخل الرقم القومي",
                }
            ),
            "full_name": forms.TextInput(
                attrs={
                    "placeholder": "أدخل اسم المريض",
                }
            ),
            "insurance_number": forms.TextInput(
                attrs={
                    "placeholder": "أدخل الرقم التأميني",
                }
            ),
            "phone_number": forms.TextInput(
                attrs={
                    "placeholder": "أدخل رقم الهاتف",
                }
            ),
            "diagnosis": forms.Textarea(
                attrs={
                    "placeholder": "أدخل التشخيص",
                    "rows": 4,
                }
            ),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():

            if isinstance(field.widget, forms.Select):
                field.widget.attrs["class"] = "form-select"

            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs["class"] = "form-textarea"

            else:
                field.widget.attrs["class"] = "form-input"


class ProcedureForm(forms.ModelForm):

    class Meta:
        model = Procedure

        fields = [
            "name",
            "category",
            "requires_referral",
            "price",
        ]

        labels = {
            "name": "اسم الإجراء",
            "category": "الفئة",
            "requires_referral": "يتطلب تحويل",
            "price": "السعر",
        }


class DoctorForm(forms.ModelForm):

    class Meta:
        model = Doctor

        fields = [
            "full_name",
        ]

        labels = {
            "full_name": "اسم الطبيب",
        }

        widgets = {
            "full_name": forms.TextInput(
                attrs={
                    "placeholder": "أدخل اسم الطبيب",
                }
            ),
        }


class CommitteeSessionForm(forms.ModelForm):

    class Meta:
        model = CommitteeSession

        fields = [
            "session_date",
            "doctor",
        ]

        labels = {
            "session_date": "تاريخ الجلسة",
            "doctor": "الطبيب الاستشاري",
        }

        widgets = {
            "session_date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "form-input",
                }
            ),

            "doctor": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
        }


class CommitteeRecommendationForm(forms.ModelForm):
    procedure = forms.ModelChoiceField(
        queryset=Procedure.objects.all(),
        required=False,
        label="الإجراء",
    )
    class Meta:
        model = CommitteeRecommendation

        fields = [
            "procedure",
            "no_of_sessions",
            "recommendation_text",
        ]

        labels = {
            "procedure": "الإجراء",
            "no_of_sessions": "عدد الجلسات",
            "recommendation_text": "توصية اللجنة",
        }

        widgets = {
            "no_of_sessions": forms.NumberInput(
                attrs={
                    "min": 1,
                    "max": 10,
                }
            ),
            "recommendation_text": forms.Textarea(
                attrs={
                    "rows": 5,
                    "placeholder": "اكتب توصية اللجنة",
                }
            ),
        }


class ReferralCenterForm(forms.ModelForm):

    class Meta:
        model = ReferralCenter

        fields = [
            "name",
        ]

        labels = {
            "name": "اسم جهة التحويل",
        }

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "placeholder": "أدخل اسم جهة التحويل",
                }
            ),
        }


class ReferralForm(forms.ModelForm):

    class Meta:
        model = Referral

        fields = [
            "referral_center",
        ]

        labels = {
            "referral_center": "جهة التحويل",
        }
        
class ReferralCancelForm(forms.ModelForm):

    class Meta:
        model = Referral

        fields = [
            "cancellation_reason",
        ]

        labels = {
            "cancellation_reason": "سبب الإلغاء",
        }

        widgets = {
            "cancellation_reason": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "اكتب سبب إلغاء خطاب التحويل",
                }
            ),
        }