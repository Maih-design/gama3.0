from django.db import models
from django.core.validators import MaxValueValidator

from .constants import (
    CaseStatus,
    Gender,
    Branches,
    InsuranceLaw,
    ReferralStatus,
    SessionStatus,
)


class Patient(models.Model):
    national_id = models.CharField(max_length=14, unique=True)
    full_name = models.CharField(max_length=200)
    gender = models.CharField(max_length=10, choices=Gender.choices)
    insurance_law = models.CharField(max_length=10, choices=InsuranceLaw.choices)
    insurance_number = models.CharField(max_length=20)
    phone_number = models.CharField(max_length=20, blank=True)
    affiliated_branch = models.CharField(max_length=100, choices=Branches.choices)
    diagnosis = models.TextField()

    def __str__(self):
        return self.full_name


class Procedure(models.Model):
    name = models.CharField(max_length=200)
    requires_referral = models.BooleanField(default=False)
    category = models.CharField(max_length=100)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        blank=True,
        null=True
    )

    def __str__(self):
        return self.name


class Doctor(models.Model):
    full_name = models.CharField(max_length=200)

    def __str__(self):
        return self.full_name


class CommitteeSession(models.Model):
    session_date = models.DateField()
    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.PROTECT
    )
    status = models.CharField(
        max_length=20,
        choices=SessionStatus.choices,
        default=SessionStatus.PREPARING
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["session_date"],
                name="unique_session_per_day"
            )
        ]

    def __str__(self):
        return f"جلسة {self.session_date}"


class CommitteeCase(models.Model):
    committee_session = models.ForeignKey(
        CommitteeSession,
        on_delete=models.CASCADE,
        related_name="cases"
    )

    patient = models.ForeignKey(
        Patient,
        on_delete=models.PROTECT,
        related_name="committee_cases"
    )

    status = models.CharField(
        max_length=20,
        choices=CaseStatus.choices,
        default=CaseStatus.PENDING
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["committee_session", "patient"],
                name="unique_patient_per_session"
            )
        ]

    def __str__(self):
        return f"{self.patient.full_name} - {self.committee_session.session_date}"


class CommitteeRecommendation(models.Model):
    committee_case = models.OneToOneField(
        CommitteeCase,
        on_delete=models.CASCADE,
        related_name="recommendation"
    )

    procedure = models.ForeignKey(
        Procedure,
        on_delete=models.PROTECT,
        related_name="recommendations"
    )

    no_of_sessions = models.PositiveIntegerField(
        validators=[MaxValueValidator(10)],
        blank=True,
        null=True
    )

    recommendation_text = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"توصية {self.committee_case.patient.full_name}"


class ReferralCenter(models.Model):
    name = models.CharField(max_length=200, unique=True)

    def __str__(self):
        return self.name


class Referral(models.Model):
    committee_case = models.ForeignKey(
        CommitteeCase,
        on_delete=models.CASCADE,
        related_name="referrals"
    )

    referral_center = models.ForeignKey(
        ReferralCenter,
        on_delete=models.PROTECT,
        related_name="referrals"
    )

    status = models.CharField(
        max_length=20,
        choices=ReferralStatus.choices,
        default=ReferralStatus.ISSUED
    )

    issued_at = models.DateTimeField(
        auto_now_add=True
    )

    cancellation_reason = models.TextField(
        blank=True
    )

    def __str__(self):
        return (
            f"{self.committee_case.patient.full_name} "
            f"→ {self.referral_center.name}"
        )