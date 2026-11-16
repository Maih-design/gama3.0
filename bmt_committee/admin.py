from django.contrib import admin
from .models import HospitalServicePrice, AtgSetting, BmtRequest, MemoMovement


class MemoMovementInline(admin.TabularInline):
    model = MemoMovement
    extra = 0
    readonly_fields = ("action", "from_status", "to_status", "destination", "notes", "moved_at", "created_by")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(HospitalServicePrice)
class HospitalServicePriceAdmin(admin.ModelAdmin):
    list_display = (
        "hospital",
        "service_type",
        "price",
        "payment_type",
        "installment_1",
        "installment_2",
        "is_active",
    )
    list_filter = ("service_type", "payment_type", "is_active")
    search_fields = ("hospital__name",)
    list_editable = ("is_active",)


@admin.register(AtgSetting)
class AtgSettingAdmin(admin.ModelAdmin):
    list_display = (
        "current_ampule_price",
        "base_price",
        "tax_percentage",
        "dose_per_kg_mg",
        "ampule_strength_mg",
        "updated_at",
    )


@admin.register(BmtRequest)
class BmtRequestAdmin(admin.ModelAdmin):
    list_display = (
        "request_code",
        "patient",
        "request_type",
        "hospital",
        "approved_amount",
        "status",
        "manual_outgoing_number",
        "manual_incoming_number",
        "created_at",
    )
    list_filter = ("request_type", "status", "hospital")
    search_fields = (
        "request_code",
        "patient__full_name",
        "patient__national_id",
        "manual_outgoing_number",
        "manual_incoming_number",
    )
    inlines = [MemoMovementInline]
    readonly_fields = ("request_code", "created_at", "updated_at")


@admin.register(MemoMovement)
class MemoMovementAdmin(admin.ModelAdmin):
    list_display = (
        "request",
        "action",
        "from_status",
        "to_status",
        "destination",
        "moved_at",
        "created_by",
    )
    list_filter = ("action", "to_status", "moved_at")
    search_fields = (
        "request__request_code",
        "request__patient__full_name",
        "destination",
        "notes",
    )
    readonly_fields = ("moved_at",)
