"""
HR Policy API tests - covers all 5 real-world content scenarios plus the
granular section / subtitle / point endpoints.

Runs on Django's isolated test database (each test is rolled back), so no
real/production data is created, modified or deleted.
"""
import json
import shutil
import tempfile

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import CustomUser
from hr_section.models import HRPolicy, HRPolicySection, HRPolicySubtitle, HRPolicyPoint

TEMP_MEDIA_ROOT = tempfile.mkdtemp()

LIST_URL = reverse('hr-policy-list')


def detail_url(pk):
    return reverse('hr-policy-detail', kwargs={'pk': pk})


ALL_SCENARIOS_PAYLOAD = {
    "title": "Company HR Handbook 2026",
    "policy_code": "POL-TEST-ALL",
    "description": "All 5 scenarios in one document.",
    "status": "active",
    "effective_date": "2026-01-01",
    "sections": [
        {   # Scenario 1 - paragraph only
            "title": "Scope & Disclaimer",
            "content": "This policy applies to all employees and contractors.",
        },
        {   # Scenario 2 - direct points, no subtitles
            "title": "Security Dos and Don'ts",
            "direct_points": [
                {"content": "Badges must be worn at all times."},
                {"content": "Tailgating through secure doors is prohibited."},
            ],
        },
        {   # Scenario 3 - section -> subtitles -> points
            "title": "Leave Entitlements",
            "subtitles": [
                {"title": "Sick Leave", "points": [
                    {"content": "8 sick days per year."},
                    {"content": "Medical note needed beyond 2 days."},
                ]},
                {"title": "Casual Leave", "points": [
                    {"content": "12 casual leaves per year."},
                ]},
            ],
        },
        {   # Scenario 4 - intro paragraph + subtitles + points
            "title": "Annual Performance Review",
            "content": "Reviews take place every April.",
            "subtitles": [
                {"title": "Self Appraisal", "points": [
                    {"content": "Submit self-ratings by April 10."},
                ]},
            ],
        },
        {   # Scenario 5 - key-value style points
            "title": "Travel Allowances",
            "direct_points": [
                {"title": "Cab Reimbursement", "content": "Up to 1500 per day after 8 PM."},
                {"title": "Meal Stipend", "content": "350 per day on client visits."},
            ],
        },
    ],
}


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT, ALLOWED_HOSTS=["*"])
class HRPolicyAPITests(TestCase):

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    @classmethod
    def setUpTestData(cls):
        cls.hr_user = CustomUser.objects.create_user(
            first_name="HR",
            last_name="Manager",
            email="hr.policy.test@pokaktechnologies.com",
            password="testpassword123",
            is_staff=True,
            is_superuser=True,
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.hr_user)

    def _create(self, payload):
        response = self.client.post(LIST_URL, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        return response.data

    # ------------------------------------------------------------------ auth
    def test_unauthenticated_access_denied(self):
        response = APIClient().get(LIST_URL)
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    # ------------------------------------------------------------- scenarios
    def test_create_policy_without_sections(self):
        data = self._create({"title": "Simple Policy"})
        self.assertEqual(data['sections'], [])
        self.assertEqual(data['status'], 'active')
        self.assertEqual(data['created_by'], self.hr_user.id)

    def test_all_five_scenarios_round_trip(self):
        data = self._create(ALL_SCENARIOS_PAYLOAD)
        sections = data['sections']
        self.assertEqual(len(sections), 5)
        self.assertEqual(data['sections_count'], 5)

        # Order preserved as created
        self.assertEqual([s['title'] for s in sections],
                         [s['title'] for s in ALL_SCENARIOS_PAYLOAD['sections']])

        s1, s2, s3, s4, s5 = sections
        # Scenario 1
        self.assertEqual(s1['content'], "This policy applies to all employees and contractors.")
        self.assertEqual(s1['direct_points'], [])
        self.assertEqual(s1['subtitles'], [])
        # Scenario 2
        self.assertEqual(len(s2['direct_points']), 2)
        self.assertEqual(s2['subtitles'], [])
        self.assertEqual(s2['direct_points'][0]['content'], "Badges must be worn at all times.")
        # Scenario 3
        self.assertEqual([st['title'] for st in s3['subtitles']], ["Sick Leave", "Casual Leave"])
        self.assertEqual(len(s3['subtitles'][0]['points']), 2)
        self.assertEqual(s3['direct_points'], [])
        # Scenario 4
        self.assertEqual(s4['content'], "Reviews take place every April.")
        self.assertEqual(s4['subtitles'][0]['points'][0]['content'], "Submit self-ratings by April 10.")
        # Scenario 5
        self.assertEqual(s5['direct_points'][0]['title'], "Cab Reimbursement")
        self.assertEqual(s5['direct_points'][1]['title'], "Meal Stipend")

        # DB integrity: each point has exactly one parent
        self.assertEqual(HRPolicyPoint.objects.filter(section__isnull=False).count(), 4)
        self.assertEqual(HRPolicyPoint.objects.filter(subtitle__isnull=False).count(), 4)

    def test_retrieve_returns_full_tree(self):
        created = self._create(ALL_SCENARIOS_PAYLOAD)
        response = self.client.get(detail_url(created['id']))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, created)

    def test_list_is_lightweight(self):
        self._create(ALL_SCENARIOS_PAYLOAD)
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rows = response.data['results'] if isinstance(response.data, dict) else response.data
        self.assertEqual(len(rows), 1)
        self.assertNotIn('sections', rows[0])
        self.assertEqual(rows[0]['sections_count'], 5)

    def test_list_search_and_filter(self):
        self._create({"title": "Leave Policy", "status": "active"})
        self._create({"title": "Draft Conduct Policy", "status": "draft"})

        def rows(resp):
            return resp.data['results'] if isinstance(resp.data, dict) else resp.data

        self.assertEqual(len(rows(self.client.get(LIST_URL, {'status': 'draft'}))), 1)
        self.assertEqual(len(rows(self.client.get(LIST_URL, {'search': 'Leave'}))), 1)

    # ----------------------------------------------------------- validation
    def test_point_requires_content(self):
        response = self.client.post(LIST_URL, {
            "title": "Bad Policy",
            "sections": [{"title": "S", "direct_points": [{"title": "Only label"}]}],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(HRPolicy.objects.count(), 0)  # atomic: nothing saved

    def test_duplicate_policy_code_rejected(self):
        self._create({"title": "A", "policy_code": "POL-DUP"})
        response = self.client.post(LIST_URL, {"title": "B", "policy_code": "POL-DUP"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_blank_policy_codes_do_not_collide(self):
        self._create({"title": "A", "policy_code": ""})
        self._create({"title": "B", "policy_code": ""})
        self.assertEqual(HRPolicy.objects.filter(policy_code__isnull=True).count(), 2)

    def test_point_must_have_exactly_one_parent(self):
        policy = HRPolicy.objects.create(title="P")
        section = HRPolicySection.objects.create(policy=policy, title="S")
        subtitle = HRPolicySubtitle.objects.create(section=section, title="ST")
        with self.assertRaises(ValidationError):
            HRPolicyPoint(section=section, subtitle=subtitle, content="x").full_clean()
        with self.assertRaises(ValidationError):
            HRPolicyPoint(content="orphan").full_clean()
        HRPolicyPoint(section=section, content="ok").full_clean()  # valid

    # --------------------------------------------------------------- update
    def test_patch_metadata_keeps_tree(self):
        created = self._create(ALL_SCENARIOS_PAYLOAD)
        response = self.client.patch(detail_url(created['id']), {"status": "archived"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'archived')
        self.assertEqual(len(response.data['sections']), 5)

    def test_patch_with_sections_replaces_tree(self):
        created = self._create(ALL_SCENARIOS_PAYLOAD)
        response = self.client.patch(detail_url(created['id']), {
            "sections": [{"title": "Only Section", "direct_points": [{"content": "One point"}]}]
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['sections']), 1)
        self.assertEqual(HRPolicySection.objects.count(), 1)
        self.assertEqual(HRPolicyPoint.objects.count(), 1)

    def test_delete_cascades(self):
        created = self._create(ALL_SCENARIOS_PAYLOAD)
        response = self.client.delete(detail_url(created['id']))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(HRPolicySection.objects.count(), 0)
        self.assertEqual(HRPolicySubtitle.objects.count(), 0)
        self.assertEqual(HRPolicyPoint.objects.count(), 0)

    # ------------------------------------------------------ multipart upload
    def test_multipart_with_document_and_json_sections(self):
        pdf = SimpleUploadedFile("policy.pdf", b"%PDF-1.4 test", content_type="application/pdf")
        response = self.client.post(LIST_URL, {
            "title": "Policy With PDF",
            "document": pdf,
            "sections": json.dumps([{"title": "Intro", "content": "Hello"}]),
        }, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertTrue(response.data['document'])
        self.assertEqual(response.data['sections'][0]['title'], "Intro")

    def test_multipart_invalid_sections_json(self):
        response = self.client.post(LIST_URL, {"title": "X", "sections": "{not json"}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ------------------------------------------------- granular endpoints
    def test_granular_add_edit_delete(self):
        policy_id = self._create({"title": "Granular Policy"})['id']

        # add section
        r = self.client.post(reverse('hr-policy-section-create', kwargs={'policy_id': policy_id}),
                             {"title": "Section A", "content": "Intro"}, format='json')
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        section_id = r.data['id']

        # add direct point
        r = self.client.post(reverse('hr-policy-section-point-create', kwargs={'section_id': section_id}),
                             {"content": "Direct point"}, format='json')
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        self.assertEqual(r.data['section'], section_id)
        self.assertIsNone(r.data['subtitle'])

        # add subtitle + point under it
        r = self.client.post(reverse('hr-policy-subtitle-create', kwargs={'section_id': section_id}),
                             {"title": "Subtitle A"}, format='json')
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        subtitle_id = r.data['id']

        r = self.client.post(reverse('hr-policy-subtitle-point-create', kwargs={'subtitle_id': subtitle_id}),
                             {"title": "Label", "content": "Value"}, format='json')
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        point_id = r.data['id']
        self.assertEqual(r.data['subtitle'], subtitle_id)
        self.assertIsNone(r.data['section'])

        # edit point / subtitle / section
        r = self.client.patch(reverse('hr-policy-point-detail', kwargs={'pk': point_id}),
                              {"content": "Updated value"}, format='json')
        self.assertEqual(r.data['content'], "Updated value")
        r = self.client.patch(reverse('hr-policy-subtitle-detail', kwargs={'pk': subtitle_id}),
                              {"title": "Renamed"}, format='json')
        self.assertEqual(r.data['title'], "Renamed")
        r = self.client.patch(reverse('hr-policy-section-detail', kwargs={'pk': section_id}),
                              {"content": "New intro"}, format='json')
        self.assertEqual(r.data['content'], "New intro")

        # full tree reflects granular changes
        tree = self.client.get(detail_url(policy_id)).data
        section = tree['sections'][0]
        self.assertEqual(section['content'], "New intro")
        self.assertEqual(section['direct_points'][0]['content'], "Direct point")
        self.assertEqual(section['subtitles'][0]['title'], "Renamed")
        self.assertEqual(section['subtitles'][0]['points'][0]['content'], "Updated value")

        # delete point and section
        self.assertEqual(self.client.delete(reverse('hr-policy-point-detail', kwargs={'pk': point_id})).status_code,
                         status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.client.delete(reverse('hr-policy-section-detail', kwargs={'pk': section_id})).status_code,
                         status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.client.get(detail_url(policy_id)).data['sections'], [])

    def test_granular_parent_not_found(self):
        r = self.client.post(reverse('hr-policy-section-create', kwargs={'policy_id': 999999}),
                             {"title": "X"}, format='json')
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_granular_cannot_reassign_parent(self):
        policy_id = self._create(ALL_SCENARIOS_PAYLOAD)['id']
        other_policy = HRPolicy.objects.create(title="Other")
        section_id = HRPolicySection.objects.filter(policy_id=policy_id).first().id
        self.client.patch(reverse('hr-policy-section-detail', kwargs={'pk': section_id}),
                          {"policy": other_policy.id}, format='json')
        self.assertEqual(HRPolicySection.objects.get(pk=section_id).policy_id, policy_id)
