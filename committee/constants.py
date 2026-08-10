from django.db import models
from django.utils.translation import gettext_lazy as _

class Gender(models.TextChoices):
    MALE = 'M', _('ذكر')
    FEMALE = 'F', _('أنثى')
    
class Branches(models.TextChoices):
    ASSIUT = 'AST', _('فرع اسيوط')
    BEHEIRA = 'BHR', _('فرع البحيرة')
    GIZA = 'GIZ', _('فرع الجيزة')
    DAKAHLIA = 'DKH', _('فرع الدقهلية')
    SHARQIA = 'SHR', _('فرع الشرقية')
    GHARBIA = 'GHB', _('فرع الغربية')
    FAYOUM = 'FYM', _('فرع الفيوم')
    CAIRO = 'CAI', _('فرع القاهرة')
    QALYUBIA = 'QLY', _('فرع القليوبية')
    MENOFIA = 'MNF', _('فرع المنوفية')
    MINYA = 'MNY', _('فرع المنيا')
    BENI_SUEF = 'BNS', _('فرع بنى سويف')
    DAMIETTA = 'DMT', _('فرع دمياط')
    SOHAG = 'SHG', _('فرع سوهاج')
    NORTH_SINAI = 'NSN', _('فرع شمال سيناء')
    NW_DELTA = 'NWD', _('فرع شمال غرب الدلتا')
    QENA = 'QNA', _('فرع قنا')
    KAFR_EL_SHEIKH = 'KSH', _('فرع كفر الشيخ')
    RED_SEA = 'RDS', _('منطقة البحر الاحمر')
    NEW_VALLEY = 'NWV', _('منطقة الوادى الجديد')
    MATROUH = 'MTR', _('منطقة مطروح')
    
class InsuranceLaw(models.TextChoices):
    RETAIRED = 'RET', _('معاش ق79')
    STUDENT = 'STD', _('طلبة')
    CHILD = 'CID', _('مواليد ق99')
    EMPLOYE = 'EMP', _('موظف ق79')
    
class SessionStatus(models.TextChoices):
        PREPARING = "PREPARING", "قيد التجهيز"
        COMPLETED = "COMPLETED", "مكتملة"
        
class CaseStatus(models.TextChoices):
        PENDING = "PENDING", "قيد المراجعة"
        APPROVED = "APPROVED", "معتمد"
        
class ReferralStatus(models.TextChoices):
        ISSUED = "ISSUED", "صادر"
        CANCELLED = "CANCELLED", "ملغي"