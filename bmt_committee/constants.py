from decimal import Decimal
from django.db import models
from django.utils.translation import gettext_lazy as _


class RequestType(models.TextChoices):
    AUTOLOGOUS = "AUTOLOGOUS", _("زرع نخاع عظمي ذاتي")
    FULLY_MATCHED = "FULLY_MATCHED", _("زرع نخاع عظمي من متبرع متوافق كلياً")
    HAPLOIDENTICAL = "HAPLOIDENTICAL", _("زرع نخاع عظمي من متبرع نصف متوافق")
    ATG = "ATG", _("علاج تحضيري بعقار ATG")


class RequestStatus(models.TextChoices):
    DRAFT = "DRAFT", _("قيد التجهيز / مسودة")
    SENT_FOR_APPROVAL = "SENT_FOR_APPROVAL", _("مرسلة للاعتماد")
    RETURNED = "RETURNED", _("واردة من الاعتماد")
    APPROVED = "APPROVED", _("معتمدة")
    REJECTED = "REJECTED", _("مرفوضة")
    PENDING_PATIENT_CONTACT = "PENDING_PATIENT_CONTACT", _("معتمدة - بانتظار التواصل مع المريض")
    PATIENT_CONTACTED = "PATIENT_CONTACTED", _("تم التواصل وتجهيز الخطاب")
    LETTER_DELIVERED = "LETTER_DELIVERED", _("تم تسليم الخطاب للمريض")
    COMPLETED = "COMPLETED", _("مكتملة وموجهة")


class PaymentType(models.TextChoices):
    SINGLE = "SINGLE", _("دفعة واحدة")
    TWO_INSTALLMENTS = "TWO_INSTALLMENTS", _("على دفعتين")


class MovementAction(models.TextChoices):
    CREATED = "CREATED", _("إنشاء الطلب وإعداد المذكرة")
    SENT_FOR_APPROVAL = "SENT_FOR_APPROVAL", _("إرسال المذكرة للاعتماد")
    RETURNED = "RETURNED", _("ورود المذكرة من السلطة المختصة")
    APPROVED = "APPROVED", _("تسجيل قرار الاعتماد")
    REJECTED = "REJECTED", _("تسجيل قرار الرفض")
    HOSPITAL_CHANGED = "HOSPITAL_CHANGED", _("تعديل المستشفى المعالج")
    PATIENT_CONTACTED = "PATIENT_CONTACTED", _("التواصل مع المريض")
    LETTER_PREPARED = "LETTER_PREPARED", _("تجهيز الخطاب الموجه للمستشفى")
    LETTER_DELIVERED = "LETTER_DELIVERED", _("تسليم الخطاب للمريض")
    ROUTED = "ROUTED", _("توجيه المذكرة والأرشفة")
    UPDATED = "UPDATED", _("تحديث بيانات الطلب")


# Default financial and calculation settings
DEFAULT_ATG_BASE_PRICE = Decimal("14694.00")
DEFAULT_ATG_TAX_PERCENT = Decimal("7.00")
DEFAULT_ATG_AMPULE_PRICE = Decimal("15722.50")
DEFAULT_ATG_DOSE_FACTOR = Decimal("21.00")  # 21 mg per kg
DEFAULT_ATG_AMPULE_STRENGTH = 100           # 100 mg per ampule

# BMT Standard Amounts
BMT_HAPLOIDENTICAL_AMOUNT = Decimal("280000.00")
BMT_STANDARD_150K = Decimal("150000.00")
BMT_STANDARD_175K = Decimal("175000.00")
BMT_150K_INSTALLMENT_1 = Decimal("40000.00")
BMT_150K_INSTALLMENT_2 = Decimal("110000.00")

# Default Signatories and Official Headers
DEFAULT_PRESENTING_DEPT = "الإدارة العامة للخدمات الطبية"
DEFAULT_ADDRESSED_TO = "السيد الدكتور / رئيس الإدارة المركزية للشئون الطبية"
