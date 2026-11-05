from django.contrib import admin

from .models import (
    Patient,
    Procedure,
    Doctor,
    CommitteeSession,
    CommitteeCase,
    CommitteeRecommendation,
    ReferralCenter,
    Referral,
)

admin.site.register(Patient)
admin.site.register(Procedure)
admin.site.register(Doctor)
admin.site.register(CommitteeSession)
admin.site.register(CommitteeCase)
admin.site.register(CommitteeRecommendation)
@admin.register(ReferralCenter)
class ReferralCenterAdmin(admin.ModelAdmin):
    list_display = ("name", "for_gamma", "for_bone_marrow")
    list_filter = ("for_gamma", "for_bone_marrow")
    list_editable = ("for_gamma", "for_bone_marrow")
admin.site.register(Referral)