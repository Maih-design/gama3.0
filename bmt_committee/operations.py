import math
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from .constants import (
    BMT_150K_INSTALLMENT_1,
    BMT_150K_INSTALLMENT_2,
    BMT_HAPLOIDENTICAL_AMOUNT,
    BMT_STANDARD_150K,
    BMT_STANDARD_175K,
    MovementAction,
    PaymentType,
    RequestStatus,
    RequestType,
)


def tafqeet_egyptian_pounds(amount):
    """
    تحويل الأرقام المالية إلى كلمات عربية بالجنيه المصري والقرش
    مثال: 150000 -> مائة وخمسون ألف جنيه فقط لا غير
    مثال: 78612.50 -> ثمانية وسبعون ألفاً وستمائة واثنا عشر جنيهاً وخمسون قرشاً فقط لا غير
    """
    if amount is None:
        return ""

    amount = Decimal(str(amount)).quantize(Decimal("0.01"))
    integer_part = int(amount)
    fraction_part = int(round((amount - integer_part) * 100))

    if integer_part == 0 and fraction_part == 0:
        return "صفر جنيه"

    ones = ["", "واحد", "اثنان", "ثلاثة", "أربعة", "خمسة", "ستة", "سبعة", "ثمانية", "تسعة", "عشرة",
            "أحد عشر", "اثنا عشر", "ثلاثة عشر", "أربعة عشر", "خمسة عشر", "ستة عشر", "سبعة عشر", "ثمانية عشر", "تسعة عشر"]
    tens = ["", "", "عشرون", "ثلاثون", "أربعون", "خمسون", "ستون", "سبعون", "ثمانون", "تسعون"]
    hundreds = ["", "مائة", "مئتان", "ثلاثمائة", "أربعمائة", "خمسمائة", "ستمائة", "سبعمائة", "ثمانمائة", "تسعمائة"]

    def convert_below_thousand(n):
        if n == 0:
            return ""
        c = n // 100
        rem = n % 100
        parts = []
        if c > 0:
            parts.append(hundreds[c])
        if rem > 0:
            if rem < 20:
                parts.append(ones[rem])
            else:
                unit = rem % 10
                ten = rem // 10
                if unit > 0:
                    parts.append(f"{ones[unit]} و{tens[ten]}")
                else:
                    parts.append(tens[ten])
        return " و".join(parts)

    words = []

    # معالجة الملايين
    millions = (integer_part // 1_000_000) % 1000
    if millions > 0:
        if millions == 1:
            words.append("مليون")
        elif millions == 2:
            words.append("مليونان")
        elif 3 <= millions <= 10:
            words.append(f"{convert_below_thousand(millions)} ملايين")
        else:
            words.append(f"{convert_below_thousand(millions)} مليوناً")

    # معالجة الآلاف
    thousands = (integer_part // 1000) % 1000
    if thousands > 0:
        if thousands == 1:
            words.append("ألف")
        elif thousands == 2:
            words.append("ألفان")
        elif 3 <= thousands <= 10:
            words.append(f"{convert_below_thousand(thousands)} آلاف")
        else:
            words.append(f"{convert_below_thousand(thousands)} ألفاً")

    # معالجة الآحاد والعشرات والمئات
    remainder = integer_part % 1000
    if remainder > 0:
        words.append(convert_below_thousand(remainder))

    result_p = " و".join(words) if words else ""
    currency_str = f"{result_p} جنيه" if result_p else ""

    # معالجة القروش
    if fraction_part > 0:
        p_text = convert_below_thousand(fraction_part)
        fraction_str = f"{p_text} قرشاً"
        if currency_str:
            return f"{currency_str} و{fraction_str} فقط لا غير"
        else:
            return f"{fraction_str} فقط لا غير"

    return f"{currency_str} فقط لا غير" if currency_str else ""


def generate_request_code():
    """
    توليد كود مميز للطلب بصيغة: BMT-YYYY-XXXX
    """
    from .models import BmtRequest

    year = timezone.now().year
    prefix = f"BMT-{year}-"
    last_req = (
        BmtRequest.objects
        .filter(request_code__startswith=prefix)
        .order_by("-request_code")
        .first()
    )

    if last_req and last_req.request_code:
        try:
            seq = int(last_req.request_code.split("-")[-1]) + 1
        except (ValueError, IndexError):
            seq = 1
    else:
        seq = 1

    return f"{prefix}{seq:04d}"


def calculate_atg_dose(weight_kg, ampule_price=None):
    """
    حساب جرعة عقار ATG وتكلفته:
    - إجمالي المجم = الوزن × معدل الجرعة (21 مجم/كجم)
    - عدد الأمبولات = سقف (إجمالي المجم / تركيز الأمبول 100 مجم)
    - إجمالي التكلفة = عدد الأمبولات × سعر الأمبول (15,722.50 ج.م)
    """
    from .models import AtgSetting

    if weight_kg is None or weight_kg <= 0:
        return {
            "weight_kg": Decimal("0.00"),
            "total_mg": Decimal("0.00"),
            "ampules": 0,
            "ampule_price": Decimal("0.00"),
            "total_cost": Decimal("0.00"),
            "cost_in_words": "",
        }

    settings_obj = AtgSetting.get_settings()
    weight = Decimal(str(weight_kg)).quantize(Decimal("0.01"))
    total_mg = (weight * settings_obj.dose_per_kg_mg).quantize(Decimal("0.01"))
    ampules = math.ceil(total_mg / Decimal(settings_obj.ampule_strength_mg))

    price = ampule_price if ampule_price is not None else settings_obj.current_ampule_price
    price = Decimal(str(price)).quantize(Decimal("0.01"))
    total_cost = (Decimal(ampules) * price).quantize(Decimal("0.01"))
    cost_in_words = tafqeet_egyptian_pounds(total_cost)

    return {
        "weight_kg": weight,
        "total_mg": total_mg,
        "ampules": ampules,
        "ampule_price": price,
        "total_cost": total_cost,
        "cost_in_words": cost_in_words,
    }


def determine_bmt_financials(request_type, hospital=None):
    """
    تحديد المبالغ والدفعات لزرع النخاع استناداً لنوع الإجراء والمستشفى:
    - نصف متطابق: 280,000 ج.م دفعة واحدة
    - ذاتي / متطابق كلياً:
      - فحص جدول HospitalServicePrice لمعرفة سعر المستشفى (150 ألف أو 175 ألف)
      - إذا 150 ألف: دفعتين (40 ألف و 110 ألف)
      - إذا 175 ألف: دفعة واحدة (175 ألف)
    """
    from .models import HospitalServicePrice

    if request_type == RequestType.HAPLOIDENTICAL:
        amount = BMT_HAPLOIDENTICAL_AMOUNT
        payment_type = PaymentType.SINGLE
        installment_1 = amount
        installment_2 = Decimal("0.00")
    else:
        # البحث عن سعر تعاقدي مسجل لهذا المستشفى والخدمة
        service_price = None
        if hospital:
            service_price = (
                HospitalServicePrice.objects
                .filter(hospital=hospital, service_type=request_type, is_active=True)
                .first()
            )

        if service_price:
            amount = service_price.price
            payment_type = service_price.payment_type
            installment_1 = service_price.installment_1
            installment_2 = service_price.installment_2
        else:
            # القيمة الافتراضية للذاتي والمتطابق كلياً هي 150,000 ج.م على دفعتين
            amount = BMT_STANDARD_150K
            payment_type = PaymentType.TWO_INSTALLMENTS
            installment_1 = BMT_150K_INSTALLMENT_1
            installment_2 = BMT_150K_INSTALLMENT_2

    amount_in_words = tafqeet_egyptian_pounds(amount)

    return {
        "approved_amount": amount,
        "amount_in_words": amount_in_words,
        "payment_type": payment_type,
        "installment_1": installment_1,
        "installment_2": installment_2,
    }


def determine_memo_routing(request_type, patient_branch_display):
    """
    تحديد جهة توجيه المذكرة الرسمية:
    - نصف متطابق: رئاسة الهيئة (الإدارة المركزية للشئون المالية)
    - ذاتي / متطابق: فرع التأمين التابع له المريض (خصماً على حساب الفرع)
    - ATG: فرع التأمين التابع له المريض (خصماً على حساب الفرع)
    """
    if request_type == RequestType.HAPLOIDENTICAL:
        return "رئاسة الهيئة - الإدارة المركزية للشئون المالية"
    else:
        branch = patient_branch_display or "فرع المريض"
        return f"{branch}"


def can_change_hospital(bmt_request, new_hospital):
    """
    التحقق من إمكانية تغيير المستشفى المعالج:
    - نصف متطابق: غير مسموح بتعديل المستشفى بعد اعتماد المذكرة
    - ذاتي / متطابق: مسموح بشرط أن يكون المستشفى البديل بنفس القيمة التعاقدية المعتمدة
    """
    from .models import HospitalServicePrice

    if not new_hospital:
        return False, "يجب اختيار مستشفى بديل صالح."

    if new_hospital.pk == bmt_request.hospital_id:
        return False, "المستشفى المختار هو نفس المستشفى المسجل بالطلب حالياً."

    # حظر التغيير لنصف المتطابق بعد الاعتماد
    if (
        bmt_request.request_type == RequestType.HAPLOIDENTICAL
        and bmt_request.status in [RequestStatus.APPROVED, RequestStatus.COMPLETED]
    ):
        return False, "لا يجوز تعديل المستشفى في حالات زرع النخاع نصف المتوافق بعد اعتماد المذكرة."

    # فحص سعر الخدمة في المستشفى الجديد ومطابقته بالسعر المعتمد
    if bmt_request.request_type in [RequestType.AUTOLOGOUS, RequestType.FULLY_MATCHED]:
        new_pricing = (
            HospitalServicePrice.objects
            .filter(hospital=new_hospital, service_type=bmt_request.request_type, is_active=True)
            .first()
        )
        # إذا تم تحديد السعر في المستشفى الجديد
        if new_pricing and new_pricing.price != bmt_request.approved_amount:
            return (
                False,
                f"سعر الخدمة بالمستشفى الجديد ({new_pricing.price:,.2f} ج.م) يختلف عن المبلغ المعتمد ({bmt_request.approved_amount:,.2f} ج.م). التغيير متاح فقط للمستشفيات بنفس القيمة."
            )

    return True, ""


@transaction.atomic
def record_memo_movement(bmt_request, action, to_status=None, destination="", notes="", user=None):
    """
    تسجيل حركة في سجل حركات المذكرة وتحديث حالة الطلب
    """
    from .models import MemoMovement

    old_status = bmt_request.status
    new_status = to_status if to_status else old_status

    movement = MemoMovement.objects.create(
        request=bmt_request,
        action=action,
        from_status=old_status,
        to_status=new_status,
        destination=destination or bmt_request.routing_destination,
        notes=notes,
        created_by=user,
    )

    if to_status and to_status != old_status:
        bmt_request.status = to_status
        bmt_request.save(update_fields=["status", "updated_at"])

    return movement
