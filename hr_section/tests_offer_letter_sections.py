from decimal import Decimal
import shutil
import tempfile
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import CustomUser
from hr_section.models import (
    OfferLetter,
    OfferLetterSection,
    OfferLetterSubtitle,
    OfferLetterPoint,
    StatusChoices,
    DutyTypeChoices,
)

TEMP_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT, ALLOWED_HOSTS=["*"])
class OfferLetterDynamicSectionsAPITests(TestCase):
    """
    Automated test suite verifying the Offer Letter APIs with dynamic nested
    Sections, Subtitles, and Points.
    """

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    @classmethod
    def setUpTestData(cls):
        # Admin / HR user for API authentication
        cls.hr_user = CustomUser.objects.create_user(
            first_name="HR",
            last_name="Manager",
            email="hr@pokaktechnologies.com",
            password="testpassword123",
            is_staff=True,
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.hr_user)

    def test_01_create_offer_letter_without_sections_backward_compatible(self):
        """
        Verify backward compatibility: Creating an offer letter with standard fields
        and no sections succeeds, resulting in empty sections array.
        """
        payload = {
            "candidate_name": "John Doe",
            "candidate_email": "john.doe@example.com",
            "phone_number": "9876543210",
            "job_title": "Backend Developer",
            "introduction": "We are pleased to offer you the position of Backend Developer.",
            "basic_salary": "30000.00",
            "allowances": [
                {"name": "HRA", "amount": 5000},
                {"name": "Travel", "amount": 2000},
            ],
            "is_target_based": False,
            "contract_period": "1 Year",
            "notice_period": "30 Days",
            "probation_period": "6 Months",
            "duty_type": DutyTypeChoices.ONSITE,
            "working_days": "Monday - Friday",
            "timing": "9:00 AM - 6:00 PM",
            "food_accommodation": "Provided",
            "joining_date": "2026-12-01",
            "note": "Bring all original educational certificates on joining day.",
            "company_name": "ABC Technologies Pvt Ltd",
            "hr_name": "HR Manager",
            "company_location": "Kochi, Kerala",
            "status": StatusChoices.DRAFT,
        }

        response = self.client.post("/hr/offer-letters/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        res_data = response.json()
        self.assertEqual(res_data.get("Status"), "1")
        self.assertEqual(res_data.get("message"), "Offer letter created successfully.")

        data = res_data.get("Data", {})
        self.assertEqual(data.get("candidate_name"), "John Doe")
        self.assertEqual(float(data.get("basic_salary")), 30000.0)
        self.assertEqual(float(data.get("total_allowance")), 7000.0)
        self.assertEqual(float(data.get("monthly_salary")), 37000.0)
        self.assertEqual(data.get("sections"), [])

        # DB verification
        offer = OfferLetter.objects.get(id=data["id"])
        self.assertEqual(offer.sections.count(), 0)
        self.assertEqual(offer.created_by, self.hr_user)

    def test_02_create_offer_letter_with_full_hierarchy(self):
        """
        Verify creating an offer letter with complete nested hierarchy:
        Offer Letter -> Sections -> Subtitles -> Points.
        """
        payload = {
            "candidate_name": "Jane Smith",
            "candidate_email": "jane.smith@example.com",
            "job_title": "Full Stack Engineer",
            "basic_salary": "40000.00",
            "allowances": [
                {"name": "HRA", "amount": 8000},
                {"name": "Internet", "amount": 1500},
            ],
            "is_target_based": False,
            "duty_type": DutyTypeChoices.HYBRID,
            "joining_date": "2026-12-15",
            "company_name": "ABC Technologies Pvt Ltd",
            "hr_name": "HR Manager",
            "company_location": "Bangalore",
            "status": StatusChoices.DRAFT,
            "sections": [
                {
                    "title": "1. Position and Commencement",
                    "content": "You will be employed as Full Stack Engineer reporting to the VP Engineering.",
                    "order": 1,
                    "subtitles": [
                        {
                            "title": "1.1 Commencement Details",
                            "order": 1,
                            "points": [
                                {
                                    "content": "Anticipated start date is 15th December 2026.",
                                    "order": 1,
                                },
                                {
                                    "content": "Reporting time will be 09:30 AM IST.",
                                    "order": 2,
                                },
                            ],
                        }
                    ],
                },
                {
                    "title": "2. Roles and Responsibilities",
                    "content": "",
                    "order": 2,
                    "subtitles": [
                        {
                            "title": "2.1 Technical Responsibilities",
                            "order": 1,
                            "points": [
                                {
                                    "content": "Design and build Django REST APIs and React components.",
                                    "order": 1,
                                },
                                {
                                    "content": "Maintain PostgreSQL database schema and optimize queries.",
                                    "order": 2,
                                },
                            ],
                        },
                        {
                            "title": "2.2 Teamwork & Code Standards",
                            "order": 2,
                            "points": [
                                {
                                    "content": "Perform code reviews and follow Git branching workflows.",
                                    "order": 1,
                                },
                                {
                                    "content": "Participate in sprint planning and daily standups.",
                                    "order": 2,
                                },
                            ],
                        },
                    ],
                },
                {
                    "title": "3. Compensation & Probation",
                    "content": "Comprehensive details regarding probation and review.",
                    "order": 3,
                    "subtitles": [],
                },
            ],
        }

        response = self.client.post("/hr/offer-letters/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        res_data = response.json()
        self.assertEqual(res_data.get("Status"), "1")
        data = res_data.get("Data", {})
        offer_id = data["id"]

        # Check DB hierarchy
        offer = OfferLetter.objects.get(id=offer_id)
        sections = offer.sections.all().order_by("order")
        self.assertEqual(sections.count(), 3)

        # Section 1
        s1 = sections[0]
        self.assertEqual(s1.title, "1. Position and Commencement")
        self.assertEqual(s1.order, 1)
        self.assertEqual(s1.subtitles.count(), 1)
        sub1 = s1.subtitles.first()
        self.assertEqual(sub1.title, "1.1 Commencement Details")
        self.assertEqual(sub1.points.count(), 2)
        p1 = sub1.points.first()
        self.assertEqual(p1.content, "Anticipated start date is 15th December 2026.")

        # Section 2
        s2 = sections[1]
        self.assertEqual(s2.title, "2. Roles and Responsibilities")
        self.assertEqual(s2.order, 2)
        self.assertEqual(s2.subtitles.count(), 2)

        # Section 3
        s3 = sections[2]
        self.assertEqual(s3.title, "3. Compensation & Probation")
        self.assertEqual(s3.content, "Comprehensive details regarding probation and review.")
        self.assertEqual(s3.subtitles.count(), 0)

        # Verify response structure contains nested sections
        self.assertEqual(len(data["sections"]), 3)
        self.assertEqual(len(data["sections"][1]["subtitles"]), 2)
        self.assertEqual(len(data["sections"][1]["subtitles"][0]["points"]), 2)

    def test_03_retrieve_offer_letter_detail(self):
        """
        Verify GET /hr/offer-letters/<id>/ returns complete details including
        nested sections, subtitles, points, calculated fields, and display values.
        """
        offer = OfferLetter.objects.create(
            candidate_name="Robert Brown",
            candidate_email="robert.b@example.com",
            job_title="DevOps Engineer",
            basic_salary=Decimal("50000.00"),
            allowances=[{"name": "On-Call", "amount": 6000}],
            duty_type="remote",
            joining_date="2026-11-20",
            company_name="ABC Technologies Pvt Ltd",
            status="draft",
            created_by=self.hr_user,
        )
        sec = OfferLetterSection.objects.create(
            offer_letter=offer, title="General Terms", content="Terms text", order=1
        )
        sub = OfferLetterSubtitle.objects.create(section=sec, title="Working Hours", order=1)
        OfferLetterPoint.objects.create(
            subtitle=sub, content="Flexible 40 hours per week across weekdays.", order=1
        )

        response = self.client.get(f"/hr/offer-letters/{offer.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        res_data = response.json()
        self.assertEqual(res_data.get("Status"), "1")
        data = res_data.get("Data", {})

        self.assertEqual(data.get("id"), offer.id)
        self.assertEqual(data.get("candidate_name"), "Robert Brown")
        self.assertEqual(data.get("duty_type_display"), "Remote")
        self.assertEqual(data.get("status_display"), "Draft")
        self.assertEqual(float(data.get("total_allowance")), 6000.0)
        self.assertEqual(float(data.get("monthly_salary")), 56000.0)

        # Nested content check
        self.assertEqual(len(data["sections"]), 1)
        self.assertEqual(data["sections"][0]["title"], "General Terms")
        self.assertEqual(data["sections"][0]["subtitles"][0]["title"], "Working Hours")
        self.assertEqual(
            data["sections"][0]["subtitles"][0]["points"][0]["content"],
            "Flexible 40 hours per week across weekdays.",
        )

    def test_04_list_endpoint_pagination_and_search(self):
        """
        Verify GET /hr/offer-letters/ lists items with pagination, search, and filtering.
        """
        # Create 3 offer letters
        for i in range(1, 4):
            OfferLetter.objects.create(
                candidate_name=f"Candidate {i}",
                candidate_email=f"candidate{i}@example.com",
                job_title="Software Engineer" if i < 3 else "UI/UX Designer",
                basic_salary=Decimal("35000.00"),
                joining_date="2026-12-01",
                company_name="ABC Technologies",
                status="draft" if i != 2 else "sent",
                created_by=self.hr_user,
            )

        # List all with pagination
        response = self.client.get("/hr/offer-letters/?page=1&page_size=10")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        res_data = response.json()
        self.assertEqual(res_data.get("Status"), "1")
        self.assertIn("Data", res_data)
        self.assertGreaterEqual(res_data.get("count", 0), 3)

        # Search by candidate name with pagination
        search_res = self.client.get("/hr/offer-letters/?search=Candidate 2&page=1&page_size=10")
        self.assertEqual(search_res.status_code, status.HTTP_200_OK)
        search_data = search_res.json()
        self.assertEqual(search_data["count"], 1)
        self.assertEqual(search_data["Data"][0]["candidate_name"], "Candidate 2")

        # Filter by status with pagination
        status_res = self.client.get("/hr/offer-letters/?status=sent&page=1&page_size=10")
        self.assertEqual(status_res.status_code, status.HTTP_200_OK)
        status_data = status_res.json()
        for item in status_data["Data"]:
            self.assertEqual(item["status"], "sent")

        # Test unpaginated list (no page_size query param)
        unpaginated_res = self.client.get("/hr/offer-letters/")
        self.assertEqual(unpaginated_res.status_code, status.HTTP_200_OK)
        unpaginated_data = unpaginated_res.json()
        self.assertEqual(unpaginated_data.get("Status"), "1")
        self.assertIsInstance(unpaginated_data.get("Data"), list)
        self.assertGreaterEqual(len(unpaginated_data["Data"]), 3)

    def test_05_partial_update_patch_normal_fields_preserves_sections(self):
        """
        Verify PATCH /hr/offer-letters/<id>/ updates standard fields without
        overwriting or deleting existing sections when 'sections' is omitted.
        """
        offer = OfferLetter.objects.create(
            candidate_name="Mark Spencer",
            candidate_email="mark@example.com",
            job_title="Frontend Developer",
            basic_salary=Decimal("25000.00"),
            joining_date="2026-12-01",
            company_name="ABC Technologies",
            status="draft",
            created_by=self.hr_user,
        )
        sec = OfferLetterSection.objects.create(
            offer_letter=offer, title="Responsibilities", order=1
        )
        sub = OfferLetterSubtitle.objects.create(section=sec, title="React", order=1)
        OfferLetterPoint.objects.create(subtitle=sub, content="Build React components", order=1)

        # Patch only candidate name and salary
        patch_payload = {
            "candidate_name": "Mark Spencer Jr.",
            "basic_salary": "28000.00",
        }
        response = self.client.patch(f"/hr/offer-letters/{offer.id}/", patch_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        res_data = response.json()
        self.assertEqual(res_data.get("Status"), "1")
        self.assertEqual(res_data["Data"]["candidate_name"], "Mark Spencer Jr.")
        self.assertEqual(float(res_data["Data"]["basic_salary"]), 28000.0)

        # Verify sections remained completely intact in DB
        offer.refresh_from_db()
        self.assertEqual(offer.sections.count(), 1)
        self.assertEqual(offer.sections.first().subtitles.first().points.count(), 1)

    def test_06_partial_update_patch_replace_sections(self):
        """
        Verify PATCH /hr/offer-letters/<id>/ atomically replaces existing sections
        when a new 'sections' array is provided.
        """
        offer = OfferLetter.objects.create(
            candidate_name="Sarah Connor",
            candidate_email="sarah@example.com",
            job_title="QA Engineer",
            basic_salary=Decimal("30000.00"),
            joining_date="2026-12-01",
            company_name="ABC Technologies",
            status="draft",
            created_by=self.hr_user,
        )
        # Old section
        old_sec = OfferLetterSection.objects.create(
            offer_letter=offer, title="Old Section", order=1
        )
        OfferLetterSubtitle.objects.create(section=old_sec, title="Old Subtitle", order=1)

        # Patch with new replacement sections
        patch_payload = {
            "sections": [
                {
                    "title": "New Section A",
                    "content": "Updated content A",
                    "order": 1,
                    "subtitles": [
                        {
                            "title": "New Subtitle A1",
                            "order": 1,
                            "points": [
                                {"content": "New Point 1", "order": 1},
                                {"content": "New Point 2", "order": 2},
                            ],
                        }
                    ],
                },
                {
                    "title": "New Section B",
                    "content": "Updated content B",
                    "order": 2,
                    "subtitles": [],
                },
            ]
        }
        response = self.client.patch(f"/hr/offer-letters/{offer.id}/", patch_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        res_data = response.json()
        self.assertEqual(res_data.get("Status"), "1")

        # Verify old section is gone, new sections exist
        self.assertFalse(OfferLetterSection.objects.filter(title="Old Section").exists())
        self.assertEqual(offer.sections.count(), 2)
        s1 = offer.sections.get(order=1)
        self.assertEqual(s1.title, "New Section A")
        self.assertEqual(s1.subtitles.first().points.count(), 2)

    def test_07_validation_target_based_requires_target_details(self):
        """
        Verify validation: If is_target_based is True, target_details is mandatory.
        """
        payload = {
            "candidate_name": "Sales Rep",
            "candidate_email": "sales@example.com",
            "job_title": "Business Development Executive",
            "basic_salary": "20000.00",
            "joining_date": "2026-12-01",
            "company_name": "ABC Technologies",
            "is_target_based": True,
            "target_details": "",  # Empty when target based is True
        }
        response = self.client.post("/hr/offer-letters/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        res_data = response.json()
        self.assertEqual(res_data.get("Status"), "0")
        self.assertEqual(res_data.get("message"), "Validation failed.")
        self.assertIn("target_details", res_data.get("Data", {}))

    def test_08_validation_allowance_format(self):
        """
        Verify validation: Each allowance must have a name, non-negative amount, and valid structure.
        """
        payload = {
            "candidate_name": "Tester",
            "candidate_email": "tester@example.com",
            "job_title": "Engineer",
            "basic_salary": "25000.00",
            "joining_date": "2026-12-01",
            "company_name": "ABC Technologies",
            "allowances": [
                {"name": "Negative Allowance", "amount": -500}  # Negative amount
            ],
        }
        response = self.client.post("/hr/offer-letters/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        res_data = response.json()
        self.assertEqual(res_data.get("Status"), "0")
        self.assertEqual(res_data.get("message"), "Validation failed.")
        self.assertIn("allowances", res_data.get("Data", {}))

    def test_09_cannot_modify_accepted_offer_letter(self):
        """
        Verify business rule: Accepted offer letters cannot be modified via PATCH.
        """
        offer = OfferLetter.objects.create(
            candidate_name="Accepted Candidate",
            candidate_email="accepted@example.com",
            job_title="Lead Architect",
            basic_salary=Decimal("80000.00"),
            joining_date="2026-12-01",
            company_name="ABC Technologies",
            status="accepted",  # Accepted status
            created_by=self.hr_user,
        )

        patch_payload = {"job_title": "Principal Architect"}
        response = self.client.patch(f"/hr/offer-letters/{offer.id}/", patch_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        res_data = response.json()
        self.assertEqual(res_data.get("Status"), "0")
        self.assertEqual(res_data.get("message"), "Cannot modify an accepted offer letter.")

        # Ensure DB value unchanged
        offer.refresh_from_db()
        self.assertEqual(offer.job_title, "Lead Architect")

    def test_10_delete_offer_letter_cascades_sections_subtitles_points(self):
        """
        Verify DELETE /hr/offer-letters/<id>/ removes the offer letter and
        cascades deletion to all its sections, subtitles, and points.
        """
        offer = OfferLetter.objects.create(
            candidate_name="To Delete",
            candidate_email="todelete@example.com",
            job_title="Intern",
            basic_salary=Decimal("15000.00"),
            joining_date="2026-12-01",
            company_name="ABC Technologies",
            status="draft",
            created_by=self.hr_user,
        )
        sec = OfferLetterSection.objects.create(offer_letter=offer, title="Section 1", order=1)
        sub = OfferLetterSubtitle.objects.create(section=sec, title="Subtitle 1", order=1)
        point = OfferLetterPoint.objects.create(subtitle=sub, content="Point 1", order=1)

        sec_id = sec.id
        sub_id = sub.id
        point_id = point.id

        response = self.client.delete(f"/hr/offer-letters/{offer.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        res_data = response.json()
        self.assertEqual(res_data.get("Status"), "1")
        self.assertEqual(res_data.get("message"), "Offer letter deleted successfully.")

        # Verify DB records deleted
        self.assertFalse(OfferLetter.objects.filter(id=offer.id).exists())
        self.assertFalse(OfferLetterSection.objects.filter(id=sec_id).exists())
        self.assertFalse(OfferLetterSubtitle.objects.filter(id=sub_id).exists())
        self.assertFalse(OfferLetterPoint.objects.filter(id=point_id).exists())
