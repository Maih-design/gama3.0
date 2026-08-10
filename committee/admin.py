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
admin.site.register(ReferralCenter)
admin.site.register(Referral)