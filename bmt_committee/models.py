from decimal import Decimal
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from .constants import (
    DEFAULT_ATG_AMPULE_PRICE,
    DEFAULT_ATG_AMPULE_STRENGTH,
    DEFAULT_ATG_BASE_PRICE,
    DEFAULT_ATG_DOSE_FACTOR,
    DEFAULT_ATG_TAX_PERCENT,
    MovementAction,
    PaymentType,
    RequestStatus,
    RequestType,
)


class HospitalServicePrice(models.Model):
    """
    تعريف أسعار الخدمات التعاقدية لزرع النخاع لكل مستشفى
    (مثل 150 ألف أو 175 ألف للذاتي/المتطابق، و 280 ألف لنصف المتطابق)
    """
    hospital = models.ForeignKey(
        "committee.ReferralCenter",
        on_delete=models.CASCADE,
        related_name="bmt_service_prices",
        verbose_name="المستشفى / المركز المعالج"
    )
    service_type = models.CharField(
        max_length=30,
        choices=RequestType.choices,
        verbose_name="نوع الخدمة"
    )
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="السعر التعاقدي المعتمد"
    )
    payment_type = models.CharField(
        max_length=20,
        choices=PaymentType.choices,
        default=PaymentType.SINGLE,
        verbose_name="طريقة الصرف"
    )
    installment_1 = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="قيمة الدفعة الأولى"
    )
    installment_2 = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="قيمة الدفعة الثانية"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="التعاقد سارٍ"
    )
    notes = models.TextField(
        blank=True,
        verbose_name="ملاحظات التعاقد"
    )

    class Meta:
        verbose_name = "سعر خدمة بمستشفى"
        verbose_name_plural = "أسعار خدمات المستشفيات"
        constraints = [
            models.UniqueConstraint(
                fields=["hospital", "service_type"],
                name="unique_hospital_service_price"
            )
        ]

    def __str__(self):
        return f"{self.hospital.name} - {self.get_service_type_display()} ({self.price:,.2f} ج.م)"


class AtgSetting(models.Model):
    """
    إعدادات عقار ATG الوارد من هيئة الشراء الموحد
    لحساب الجرعات والتكلفة تلقائياً
    """
    current_ampule_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=DEFAULT_ATG_AMPULE_PRICE,
        verbose_name="سعر الأمبول بعد الضريبة (ج.م)"
    )
    base_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=DEFAULT_ATG_BASE_PRICE,
        verbose_name="سعر الأمبول الأساسي (ج.م)"
    )
    tax_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=DEFAULT_ATG_TAX_PERCENT,
        verbose_name="نسبة الضريبة (%)"
    )
    dose_per_kg_mg = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=DEFAULT_ATG_DOSE_FACTOR,
        verbose_name="معدل الجرعة (مجم / كجم)"
    )
    ampule_strength_mg = models.PositiveIntegerField(
        default=DEFAULT_ATG_AMPULE_STRENGTH,
        verbose_name="تركيز الأمبول (مجم)"
    )
    notes = models.TextField(
        blank=True,
        verbose_name="ملاحظات توريد الشراء الموحد"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="تاريخ آخر تحديث"
    )

    class Meta:
        verbose_name = "إعدادات عقار ATG"
        verbose_name_plural = "إعدادات عقار ATG"

    def __str__(self):
        return f"تسعير ATG الحالي: {self.current_ampule_price} ج.م"

    @classmethod
    def get_settings(cls):
        settings_obj = cls.objects.first()
        if not settings_obj:
            settings_obj = cls.objects.create(
                current_ampule_price=DEFAULT_ATG_AMPULE_PRICE,
                base_price=DEFAULT_ATG_BASE_PRICE,
                tax_percentage=DEFAULT_ATG_TAX_PERCENT,
                dose_per_kg_mg=DEFAULT_ATG_DOSE_FACTOR,
                ampule_strength_mg=DEFAULT_ATG_AMPULE_STRENGTH,
            )
        return settings_obj


class BmtRequest(models.Model):
    """
    طلب ومذكرة الموافقة المالية لزرع النخاع أو علاج ATG
    """
    request_code = models.CharField(
        max_length=50,
        unique=True,
        editable=False,
        verbose_name="كود الطلب"
    )
    patient = models.ForeignKey(
        "committee.Patient",
        on_delete=models.PROTECT,
        related_name="bmt_requests",
        verbose_name="المريض"
    )
    request_type = models.CharField(
        max_length=30,
        choices=RequestType.choices,
        verbose_name="نوع الإجراء / الطلب"
    )
    hospital = models.ForeignKey(
        "committee.ReferralCenter",
        on_delete=models.PROTECT,
        related_name="bmt_requests",
        verbose_name="المستشفى المعالج"
    )
    status = models.CharField(
        max_length=30,
        choices=RequestStatus.choices,
        default=RequestStatus.DRAFT,
        verbose_name="حالة الطلب والمذكرة"
    )

    # السياق الطبي والموافقات السابقة الواردة بملف المريض
    referring_clinic_or_committee = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="اللجنة / العيادة المحيلة"
    )
    hla_lab_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="معمل توافق الأنسجة"
    )
    external_approval_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="رقم إفادة المستشفى / الموافقة السابقة"
    )
    external_approval_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="تاريخ إفادة المستشفى / الموافقة"
    )
    hospital_initial_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="التكلفة المبدئية بإفادة المستشفى"
    )
    guardian_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="اسم ولي الأمر / القريب"
    )
    guardian_relation = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="صلة القرابة"
    )

    # الحسابات المالية والقيم التاريخية (Snapshot)
    approved_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="المبلغ المعتمد"
    )
    amount_in_words = models.CharField(
        max_length=500,
        blank=True,
        verbose_name="المبلغ بالحروف"
    )
    payment_type = models.CharField(
        max_length=20,
        choices=PaymentType.choices,
        default=PaymentType.SINGLE,
        verbose_name="طريقة الصرف"
    )
    installment_1 = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="الدفعة الأولى"
    )
    installment_2 = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="الدفعة الثانية"
    )

    # حقول خاصة بعقار ATG
    patient_weight = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="وزن المريض (كجم)"
    )
    atg_total_mg = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="إجمالي الجرعة (مجم)"
    )
    atg_dose_ampules = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="عدد أمبولات ATG"
    )
    atg_ampule_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="سعر أمبول ATG عند الاعتماد"
    )
    patient_contacted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="تاريخ ووقت التواصل مع المريض"
    )
    hospital_letter_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="رقم خطاب المستشفى"
    )
    hospital_letter_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="تاريخ خطاب المستشفى"
    )
    letter_delivered_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="تاريخ تسليم الخطاب للمريض"
    )

    # بيانات المذكرة والتتبع الدفتري
    memo_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="تاريخ العرض / المذكرة"
    )
    manual_outgoing_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="رقم الصادر الدفتري"
    )
    manual_outgoing_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="تاريخ الصادر الدفتري"
    )
    manual_incoming_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="رقم الوارد الدفتري"
    )
    manual_incoming_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="تاريخ الوارد الدفتري"
    )
    dispatch_outgoing_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="رقم صادر توجيه المذكرة"
    )
    dispatch_outgoing_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="تاريخ صادر توجيه المذكرة"
    )
    routing_destination = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="جهة التوجيه النهائية"
    )
    rejection_reason = models.TextField(
        blank=True,
        verbose_name="سبب الرفض إن وجد"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاريخ الإنشاء"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="تاريخ آخر تعديل"
    )

    class Meta:
        verbose_name = "طلب ومذكرة زرع نخاع / ATG"
        verbose_name_plural = "طلبات ومذكرات زرع النخاع و ATG"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.request_code} - {self.patient.full_name} ({self.get_request_type_display()})"


class MemoMovement(models.Model):
    """
    سجل تتبع حركة المذكرة خطوة بخطوة
    (إعداد، إرسال، ورود، اعتماد/رفض، توجيه، تسليم)
    """
    request = models.ForeignKey(
        BmtRequest,
        on_delete=models.CASCADE,
        related_name="movements",
        verbose_name="الطلب"
    )
    action = models.CharField(
        max_length=50,
        choices=MovementAction.choices,
        verbose_name="نوع الإجراء"
    )
    from_status = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="من حالة"
    )
    to_status = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="إلى حالة"
    )
    destination = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="الجهة الموجه إليها"
    )
    notes = models.TextField(
        blank=True,
        verbose_name="ملاحظات الحركة"
    )
    moved_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاريخ ووقت الحركة"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="المستخدم المسؤول"
    )

    class Meta:
        verbose_name = "حركة تتبع المذكرة"
        verbose_name_plural = "سجل حركات وتتبع المذكرات"
        ordering = ["-moved_at"]

    def __str__(self):
        return f"{self.request.request_code} - {self.get_action_display()} ({self.moved_at.strftime('%Y-%m-%d %H:%M')})"
