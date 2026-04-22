from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .models import InternshipApplication, InternshipDocument

User = get_user_model()


class InternshipApplicationAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            first_name="Test",
            last_name="User",
            email="tester@example.com",
            password="testpass123",
        )
        self.client.force_authenticate(user=self.user)
        self.list_url = reverse("internship-application-list-create")

    def test_create_application_with_nested_documents(self):
        response = self.client.post(
            self.list_url,
            data=self._build_payload(),
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(InternshipApplication.objects.count(), 1)
        self.assertEqual(InternshipDocument.objects.count(), 2)
        self.assertEqual(len(response.data["documents"]), 2)
        self.assertEqual(response.data["documents"][0]["document_type"], "qualification")
        self.assertEqual(response.data["documents"][1]["document_type"], "legal")

    def test_get_list_and_detail_include_documents(self):
        application = InternshipApplication.objects.create(
            first_name="Anu",
            last_name="Joseph",
            primary_phone="+919876543210",
            email="anu@example.com",
            dob="2000-01-01",
            gender="female",
            qualification="ug",
            course_name="BSc Computer Science",
            address="Address line",
            state="Kerala",
            district="Ernakulam",
            pincode="682001",
            where_did_you_find_us="google",
            course_applied_for="Python Internship",
            course_duration=6,
            course_type="online",
        )
        InternshipDocument.objects.create(
            application=application,
            document_type="qualification",
            file=SimpleUploadedFile("degree.pdf", b"degree-file", content_type="application/pdf"),
        )

        list_response = self.client.get(self.list_url)
        detail_response = self.client.get(
            reverse("internship-application-detail", kwargs={"pk": application.pk})
        )

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data), 1)
        self.assertNotIn("documents", list_response.data[0])
        self.assertEqual(detail_response.data["id"], application.id)
        self.assertIn("documents", detail_response.data)
        self.assertEqual(len(detail_response.data["documents"]), 1)

    def test_list_applications_supports_page_and_page_size(self):
        for index in range(12):
            InternshipApplication.objects.create(
                first_name=f"User{index}",
                last_name="Test",
                primary_phone=f"+9198765432{index:02d}",
                email=f"user{index}@example.com",
                dob="2000-01-01",
                gender="male",
                qualification="ug",
                course_name="BSc",
                address="Address line",
                state="Kerala",
                district="Ernakulam",
                pincode="682001",
                where_did_you_find_us="google",
                course_applied_for="Python Internship",
                course_duration=6,
                course_type="online",
            )

        response = self.client.get(self.list_url, {"page": 2, "page_size": 5})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 12)
        self.assertEqual(len(response.data["results"]), 5)
        self.assertNotIn("documents", response.data["results"][0])
        self.assertIsNotNone(response.data["next"])
        self.assertIsNotNone(response.data["previous"])

    def test_list_without_pagination_params_returns_all_records(self):
        for index in range(3):
            InternshipApplication.objects.create(
                first_name=f"All{index}",
                last_name="User",
                primary_phone=f"+9198765441{index:02d}",
                email=f"all{index}@example.com",
                dob="2000-01-01",
                gender="female",
                qualification="ug",
                course_name="BSc",
                address="Address line",
                state="Kerala",
                district="Thrissur",
                pincode="680001",
                where_did_you_find_us="google",
                course_applied_for="Python Internship",
                course_duration=6,
                course_type="online",
            )

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertEqual(len(response.data), 3)

    def test_paginated_search_out_of_range_returns_empty_results(self):
        InternshipApplication.objects.create(
            first_name="Search",
            last_name="User",
            primary_phone="+919876540001",
            email="search-user@example.com",
            dob="2000-01-01",
            gender="female",
            qualification="ug",
            course_name="BSc",
            address="Address line",
            state="Kerala",
            district="Kollam",
            pincode="691001",
            where_did_you_find_us="google",
            course_applied_for="Python Internship",
            course_duration=6,
            course_type="online",
            academic_counselor="Riya",
        )

        response = self.client.get(
            self.list_url,
            {"search": "Search", "page": 2, "page_size": 10},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"], [])
        self.assertEqual(response.data["detail"], "Not found.")

    def test_list_supports_basic_filters(self):
        today = timezone.localdate().isoformat()
        matching_application = InternshipApplication.objects.create(
            first_name="Filter",
            last_name="Match",
            primary_phone="+919876549900",
            email="filter-match@example.com",
            dob="2000-01-01",
            gender="female",
            qualification="ug",
            course_name="BSc",
            address="Address line",
            state="Kerala",
            district="Kozhikode",
            pincode="673001",
            where_did_you_find_us="google",
            course_applied_for="Python Internship",
            course_duration=6,
            course_type="online",
            academic_counselor="Riya",
        )
        InternshipApplication.objects.create(
            first_name="Filter",
            last_name="Other",
            primary_phone="+919876549901",
            email="filter-other@example.com",
            dob="2000-01-01",
            gender="male",
            qualification="pg",
            course_name="MBA",
            address="Another address",
            state="Tamil Nadu",
            district="Chennai",
            pincode="600001",
            where_did_you_find_us="friend",
            course_applied_for="Business Internship",
            course_duration=3,
            course_type="offline",
            academic_counselor="Anu",
        )

        response = self.client.get(
            self.list_url,
            {
                "academic_counselor": "Riya",
                "created_at": today,
                "gender": "female",
                "qualification": "ug",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], matching_application.id)

    def test_delete_application_cascades_documents(self):
        application = InternshipApplication.objects.create(
            first_name="Akhil",
            last_name="Babu",
            primary_phone="+919876543211",
            email="akhil@example.com",
            dob="1999-02-02",
            gender="male",
            qualification="pg",
            course_name="MBA",
            address="Another address",
            state="Kerala",
            district="Kottayam",
            pincode="686001",
            where_did_you_find_us="friend",
            course_applied_for="Business Internship",
            course_duration=3,
            course_type="offline",
        )
        InternshipDocument.objects.create(
            application=application,
            document_type="legal",
            file=SimpleUploadedFile("id-card.png", b"id-card", content_type="image/png"),
        )

        response = self.client.delete(
            reverse("internship-application-detail", kwargs={"pk": application.pk})
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(InternshipApplication.objects.filter(pk=application.pk).exists())
        self.assertEqual(InternshipDocument.objects.count(), 0)

    def test_create_requires_other_source_when_source_is_other(self):
        payload = self._build_payload()
        payload["where_did_you_find_us"] = "other"
        payload.pop("other_source", None)

        response = self.client.post(self.list_url, data=payload, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("other_source", response.data)

    def _build_payload(self):
        return {
            "first_name": "Niya",
            "last_name": "Das",
            "primary_phone": "+919876543212",
            "secondary_phone": "+919876543213",
            "email": "niya@example.com",
            "dob": "2001-05-01",
            "gender": "female",
            "qualification": "ug",
            "course_name": "BCA",
            "address": "Sample address",
            "state": "Kerala",
            "district": "Kozhikode",
            "pincode": "673001",
            "where_did_you_find_us": "other",
            "other_source": "College seminar",
            "course_applied_for": "Full Stack Internship",
            "course_duration": "6",
            "course_type": "offline",
            "linkedin_profile_url": "https://linkedin.com/in/niya",
            "github_profile_url": "https://github.com/niya",
            "portfolio_url": "https://niya.dev",
            "academic_counselor": "Riya",
            "documents[0][document_type]": "qualification",
            "documents[0][file]": SimpleUploadedFile(
                "marksheet.pdf",
                b"qualification-file",
                content_type="application/pdf",
            ),
            "documents[1][document_type]": "legal",
            "documents[1][file]": SimpleUploadedFile(
                "id-proof.png",
                b"legal-file",
                content_type="image/png",
            ),
        }
