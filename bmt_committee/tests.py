import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from committee.constants import Branches, Gender, InsuranceLaw
from committee.models import Patient, ReferralCenter

from .constants import MovementAction, RequestStatus, RequestType
from .models import BmtRequest, MemoMovement
from .operations import determine_memo_routing, generate_request_code


User = get_user_model()


class BmtWorkflowAndMemoTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="tester",
            password="test-password-123",
            first_name="أحمد",
            last_name="محمود",
        )
        self.client.force_login(self.user)

        self.patient = Patient.objects.create(
            national_id="29901010101010",
            full_name="مريض اختبار النظام",
            gender=Gender.MALE,
            insurance_law=InsuranceLaw.EMPLOYE,
            insurance_number="12345678",
            phone_number="01000000000",
            affiliated_branch=Branches.CAIRO,
            diagnosis="فقر دم لا تنسجي",
        )
        self.hospital = ReferralCenter.objects.create(
            name="مستشفى اختبار زرع النخاع",
            for_gamma=False,
            for_bone_marrow=True,
        )

    def _create_request(self, request_type, memo_date=None):
        routing = determine_memo_routing(
            request_type,
            self.patient.get_affiliated_branch_display(),
        )
        return BmtRequest.objects.create(
            request_code=generate_request_code(),
            patient=self.patient,
            request_type=request_type,
            hospital=self.hospital,
            status=RequestStatus.DRAFT,
            approved_amount=Decimal("150000.00"),
            amount_in_words="مائة وخمسون ألف جنيه فقط لا غير",
            routing_destination=routing,
            memo_date=memo_date,
        )

    def test_landing_and_committee_pages_load(self):
        for url in [
            reverse("landing"),
            reverse("gamma_home"),
            reverse("bmt_committee:bmt_home"),
            reverse("bmt_committee:dashboard"),
            reverse("bmt_committee:request_list"),
        ]:
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200, f"Failed for {url}")

    def test_memo_print_formatting_and_user_footer(self):
        req_with_date = self._create_request(
            RequestType.AUTOLOGOUS,
            memo_date=datetime.date(2026, 11, 20),
        )
        resp = self.client.get(reverse("bmt_committee:memo_print", args=[req_with_date.pk]))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode("utf-8")

        self.assertNotIn("أ/ غادة", html)
        self.assertIn("<div>جهة العرض: - الإدارة العامة للخدمات الطبية.</div>", html)
        self.assertIn("<div>تاريخ العرض: - 2026/11/20</div>", html)
        self.assertIn(f"أحمد محمود - {req_with_date.request_code}", html)

        req_without_date = self._create_request(RequestType.FULLY_MATCHED, memo_date=None)
        resp2 = self.client.get(reverse("bmt_committee:memo_print", args=[req_without_date.pk]))
        self.assertEqual(resp2.status_code, 200)
        today_str = datetime.date.today().strftime("%Y/%m/%d")
        self.assertIn(f"<div>تاريخ العرض: - {today_str}</div>", resp2.content.decode("utf-8"))

    def test_bmt_approved_memo_routing_workflow(self):
        bmt_req = self._create_request(RequestType.HAPLOIDENTICAL)
        detail_url = reverse("bmt_committee:request_detail", args=[bmt_req.pk])
        route_url = reverse("bmt_committee:route_memo", args=[bmt_req.pk])

        # Cannot route while still DRAFT
        resp_guard = self.client.get(route_url)
        self.assertRedirects(resp_guard, detail_url)

        # Send for approval
        self.client.post(
            reverse("bmt_committee:send_for_approval", args=[bmt_req.pk]),
            {
                "memo_date": "2026-11-20",
                "manual_outgoing_number": "OUT-100",
                "manual_outgoing_date": "2026-11-20",
                "notes": "إرسال للاعتماد",
            },
        )
        bmt_req.refresh_from_db()
        self.assertEqual(bmt_req.status, RequestStatus.SENT_FOR_APPROVAL)

        # Record return as APPROVED
        self.client.post(
            reverse("bmt_committee:record_return", args=[bmt_req.pk]),
            {
                "decision": "APPROVED",
                "manual_incoming_number": "IN-200",
                "manual_incoming_date": "2026-11-21",
                "notes": "تم الاعتماد",
            },
        )
        bmt_req.refresh_from_db()
        self.assertEqual(bmt_req.status, RequestStatus.APPROVED)

        # Detail page should now display route_memo action button
        detail_resp = self.client.get(detail_url)
        self.assertContains(detail_resp, route_url)

        # Dashboard and home show 1 pending routing
        dash_resp = self.client.get(reverse("bmt_committee:dashboard"))
        self.assertEqual(dash_resp.context["stats"]["bmt_pending_routing"], 1)

        # Submit route_memo with new dispatch outgoing number
        route_get = self.client.get(route_url)
        self.assertEqual(route_get.status_code, 200)
        self.assertContains(route_get, bmt_req.routing_destination)

        route_post = self.client.post(
            route_url,
            {
                "dispatch_outgoing_number": "DISP-999",
                "dispatch_outgoing_date": "2026-11-23",
                "notes": "أرسلت بالحافظة رقم 5",
            },
        )
        self.assertRedirects(route_post, detail_url)

        bmt_req.refresh_from_db()
        self.assertEqual(bmt_req.status, RequestStatus.COMPLETED)
        self.assertEqual(bmt_req.dispatch_outgoing_number, "DISP-999")
        self.assertEqual(bmt_req.dispatch_outgoing_date, datetime.date(2026, 11, 23))

        # Verify MemoMovement recorded ROUTED
        last_mov = MemoMovement.objects.filter(request=bmt_req).order_by("-moved_at").first()
        self.assertEqual(last_mov.action, MovementAction.ROUTED)
        self.assertEqual(last_mov.to_status, RequestStatus.COMPLETED)
        self.assertIn("DISP-999", last_mov.notes)

        # Detail page displays dispatch_outgoing_number and hides route button
        after_detail = self.client.get(detail_url)
        self.assertContains(after_detail, "DISP-999")
        self.assertNotContains(after_detail, route_url)

        # Search in request_list by dispatch_outgoing_number
        search_resp = self.client.get(reverse("bmt_committee:request_list"), {"search": "DISP-999"})
        self.assertContains(search_resp, bmt_req.request_code)

    def test_atg_workflow_ends_at_social_services_handover(self):
        atg_req = self._create_request(RequestType.ATG)
        detail_url = reverse("bmt_committee:request_detail", args=[atg_req.pk])
        handover_url = reverse("bmt_committee:handover_social_services", args=[atg_req.pk])
        route_url = reverse("bmt_committee:route_memo", args=[atg_req.pk])

        self.client.post(
            reverse("bmt_committee:send_for_approval", args=[atg_req.pk]),
            {
                "memo_date": "2026-11-20",
                "manual_outgoing_number": "OUT-300",
                "manual_outgoing_date": "2026-11-20",
            },
        )
        self.client.post(
            reverse("bmt_committee:record_return", args=[atg_req.pk]),
            {
                "decision": "APPROVED",
                "manual_incoming_number": "IN-301",
                "manual_incoming_date": "2026-11-21",
            },
        )
        atg_req.refresh_from_db()
        self.assertEqual(atg_req.status, RequestStatus.PENDING_SOCIAL_SERVICES)

        # ATG must show handover button, NOT route_memo button
        detail_resp = self.client.get(detail_url)
        self.assertContains(detail_resp, handover_url)
        self.assertNotContains(detail_resp, route_url)

        # Route memo URL redirects safely for ATG
        self.assertRedirects(self.client.get(route_url), detail_url)

        # Handover completes ATG request
        self.client.post(
            handover_url,
            {
                "handover_date": "2026-11-22",
                "social_worker_name": "أخصائي اجتماعي",
                "notes": "تم التسليم",
            },
        )
        atg_req.refresh_from_db()
        self.assertEqual(atg_req.status, RequestStatus.COMPLETED)
