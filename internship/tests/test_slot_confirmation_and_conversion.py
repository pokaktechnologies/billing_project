from datetime import date
from decimal import Decimal
import shutil
import tempfile
from django.core import mail
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Department
from internship.models import Center, Course, InternshipApplication, Student

TEMP_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class SlotConfirmationAndConversionTests(TestCase):
    """
    Test suite to safely verify:
    1. Slot confirmation saves the four slot fields and sends no email.
    2. GET API returns confirmed slot fields and unconverted status.
    3. Invalid slot amount (0 and negative) is rejected.
    4. Missing required slot fields (method and date) are rejected.
    5. Conversion succeeds without slot_amount in payload and copies application.slot_amount to student.
    6. Passing extra slot_amount in conversion request does not overwrite application or student slot amount.
    7. Duplicate conversion of already converted application is rejected.
    8. Student registration ignores slot payment fields, but preserves application-received email.
    """

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    @classmethod
    def setUpTestData(cls):
        # Create department
        cls.department = Department.objects.create(name="IT Department")

        # Create course
        cls.course = Course.objects.create(
            title="Full Stack Python",
            department=cls.department,
            total_fee=Decimal("25000.00"),
        )

        # Create center
        cls.center = Center.objects.create(name="Calicut Center")

    def setUp(self):
        self.client = APIClient()
        mail.outbox.clear()

    def _create_application(self, email="test_applicant@example.com", slot_amount=None):
        return InternshipApplication.objects.create(
            first_name="John",
            last_name="Doe",
            email=email,
            primary_phone="9876543210",
            dob=date(2000, 1, 1),
            gender="male",
            qualification="ug",
            address="Test Address, Kerala",
            state="Kerala",
            district="Kozhikode",
            pincode="673001",
            course=self.course,
            course_duration=6,
            course_type="offline",
            slot_amount=slot_amount,
            slot_payment_method="cash" if slot_amount else None,
            slot_transaction_id="TXN-INITIAL" if slot_amount else None,
            slot_payment_date=date(2026, 10, 20) if slot_amount else None,
        )

    # -------------------------------------------------------------
    # Test 1: Slot Confirmation
    # -------------------------------------------------------------
    def test_01_slot_confirmation_success(self):
        app = self._create_application(email="applicant1@example.com")
        url = f"/internship/applications/{app.id}/slot-confirmation/"

        payload = {
            "slot_amount": "500.00",
            "slot_payment_method": "cash",
            "slot_transaction_id": "TEST-SLOT-001",
            "slot_payment_date": "2026-10-29",
        }

        response = self.client.post(url, data=payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "1")
        self.assertEqual(response.data["message"], "Slot confirmed successfully.")

        # Verify saved on model
        app.refresh_from_db()
        self.assertEqual(app.slot_amount, Decimal("500.00"))
        self.assertEqual(app.slot_payment_method, "cash")
        self.assertEqual(app.slot_transaction_id, "TEST-SLOT-001")
        self.assertEqual(app.slot_payment_date, date(2026, 10, 29))

        # Verify no email was sent
        self.assertEqual(len(mail.outbox), 0)

    # -------------------------------------------------------------
    # Test 2: Verify Saved Slot Details via GET API
    # -------------------------------------------------------------
    def test_02_verify_saved_slot_details_via_get(self):
        app = self._create_application(
            email="applicant2@example.com",
            slot_amount=Decimal("500.00")
        )
        app.slot_payment_method = "cash"
        app.slot_transaction_id = "TEST-SLOT-001"
        app.slot_payment_date = date(2026, 10, 29)
        app.save()

        url = f"/internship/applications/{app.id}/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(str(response.data["slot_amount"])), Decimal("500.00"))
        self.assertEqual(response.data["slot_payment_method"], "cash")
        self.assertEqual(response.data["slot_transaction_id"], "TEST-SLOT-001")
        self.assertEqual(response.data["slot_payment_date"], "2026-10-29")
        self.assertFalse(response.data["is_converted"])

    # -------------------------------------------------------------
    # Test 3: Invalid Slot Amount (Zero and Negative)
    # -------------------------------------------------------------
    def test_03_invalid_slot_amount_rejected(self):
        app = self._create_application(email="applicant3@example.com")
        url = f"/internship/applications/{app.id}/slot-confirmation/"

        # Zero amount
        payload_zero = {
            "slot_amount": "0.00",
            "slot_payment_method": "cash",
            "slot_transaction_id": "TEST-ZERO",
            "slot_payment_date": "2026-10-29",
        }
        response_zero = self.client.post(url, data=payload_zero, format="json")
        self.assertEqual(response_zero.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("slot_amount", response_zero.data)

        # Negative amount
        payload_neg = {
            "slot_amount": "-150.00",
            "slot_payment_method": "cash",
            "slot_transaction_id": "TEST-NEG",
            "slot_payment_date": "2026-10-29",
        }
        response_neg = self.client.post(url, data=payload_neg, format="json")
        self.assertEqual(response_neg.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("slot_amount", response_neg.data)

        # Data remains unchanged
        app.refresh_from_db()
        self.assertIsNone(app.slot_amount)

    # -------------------------------------------------------------
    # Test 4: Missing Required Payment Details
    # -------------------------------------------------------------
    def test_04_missing_required_payment_details(self):
        app = self._create_application(email="applicant4@example.com")
        url = f"/internship/applications/{app.id}/slot-confirmation/"

        # Missing payment method
        payload_no_method = {
            "slot_amount": "500.00",
            "slot_payment_date": "2026-10-29",
        }
        res1 = self.client.post(url, data=payload_no_method, format="json")
        self.assertEqual(res1.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("slot_payment_method", res1.data)

        # Missing payment date
        payload_no_date = {
            "slot_amount": "500.00",
            "slot_payment_method": "cash",
        }
        res2 = self.client.post(url, data=payload_no_date, format="json")
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("slot_payment_date", res2.data)

        # Invalid payment method choice
        payload_invalid_choice = {
            "slot_amount": "500.00",
            "slot_payment_method": "crypto",
            "slot_payment_date": "2026-10-29",
        }
        res3 = self.client.post(url, data=payload_invalid_choice, format="json")
        self.assertEqual(res3.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("slot_payment_method", res3.data)

    # -------------------------------------------------------------
    # Test 5: Convert Without Slot Amount in Conversion Request
    # -------------------------------------------------------------
    def test_05_convert_without_slot_amount(self):
        app = self._create_application(
            email="applicant5@example.com",
            slot_amount=Decimal("500.00")
        )
        url = f"/internship/applications/{app.id}/convert/"

        payload = {
            "center": self.center.id,
            "start_date": "2026-11-01",
            "email": "unique_student_test_05@example.com",
            "password": "Password@123",
            "confirm_password": "Password@123",
            "status": "active",
        }

        response = self.client.post(url, data=payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "1")
        self.assertEqual(response.data["message"], "Student converted successfully.")

        # Verify Student created with previously confirmed slot amount
        student = Student.objects.get(id=response.data["student_id"])
        self.assertEqual(student.slot_amount, Decimal("500.00"))

        # Verify Application state
        app.refresh_from_db()
        self.assertTrue(app.is_converted)
        self.assertEqual(app.converted_students, student)
        self.assertEqual(app.slot_amount, Decimal("500.00"))

        # Verify absolutely NO conversion email was sent
        self.assertEqual(len(mail.outbox), 0)

    # -------------------------------------------------------------
    # Test 6: Attempt to Override Slot Amount During Conversion
    # -------------------------------------------------------------
    def test_06_attempt_to_override_slot_amount_during_conversion(self):
        app = self._create_application(
            email="applicant6@example.com",
            slot_amount=Decimal("500.00")
        )
        url = f"/internship/applications/{app.id}/convert/"

        # Send extra slot_amount in payload attempting to override to 9999.00
        payload = {
            "center": self.center.id,
            "start_date": "2026-11-01",
            "email": "unique_student_test_06@example.com",
            "password": "Password@123",
            "confirm_password": "Password@123",
            "status": "active",
            "slot_amount": "9999.00",
        }

        response = self.client.post(url, data=payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify Student received the application's slot_amount (500.00), NOT 9999.00
        student = Student.objects.get(id=response.data["student_id"])
        self.assertEqual(student.slot_amount, Decimal("500.00"))

        # Verify Application slot_amount is NOT overwritten
        app.refresh_from_db()
        self.assertEqual(app.slot_amount, Decimal("500.00"))

    # -------------------------------------------------------------
    # Test 7: Duplicate Conversion Rejected
    # -------------------------------------------------------------
    def test_07_duplicate_conversion_rejected(self):
        app = self._create_application(
            email="applicant7@example.com",
            slot_amount=Decimal("500.00")
        )
        url = f"/internship/applications/{app.id}/convert/"

        payload_1 = {
            "center": self.center.id,
            "start_date": "2026-11-01",
            "email": "unique_student_test_07a@example.com",
            "password": "Password@123",
            "confirm_password": "Password@123",
            "status": "active",
        }
        res_1 = self.client.post(url, data=payload_1, format="json")
        self.assertEqual(res_1.status_code, status.HTTP_201_CREATED)

        initial_students_count = Student.objects.count()

        # Second conversion attempt on the same application
        payload_2 = {
            "center": self.center.id,
            "start_date": "2026-11-01",
            "email": "unique_student_test_07b@example.com",
            "password": "Password@123",
            "confirm_password": "Password@123",
            "status": "active",
        }
        res_2 = self.client.post(url, data=payload_2, format="json")

        self.assertEqual(res_2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res_2.data["status"], "0")
        self.assertEqual(res_2.data["message"], "This application has already been converted.")

        # Ensure no duplicate student was created
        self.assertEqual(Student.objects.count(), initial_students_count)

        # No email sent
        self.assertEqual(len(mail.outbox), 0)

    # -------------------------------------------------------------
    # Test 8: Registration ignores slot fields but sends email
    # -------------------------------------------------------------
    def test_08_registration_ignores_slot_fields_and_sends_email(self):
        url = "/internship/applications/"

        # Dummy 1x1 png image
        from django.core.files.uploadedfile import SimpleUploadedFile
        tiny_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xff\xff\xff\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00'
            b'\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b'
        )
        profile_image = SimpleUploadedFile("profile.gif", tiny_gif, content_type="image/gif")

        payload = {
            "first_name": "Applicant",
            "last_name": "Registration",
            "profile_image": profile_image,
            "primary_phone": "9123456789",
            "email": "new_registered_applicant@example.com",
            "dob": "2001-05-15",
            "gender": "female",
            "qualification": "ug",
            "address": "Ernakulam, Kerala",
            "state": "Kerala",
            "district": "Ernakulam",
            "pincode": "682001",
            "course": self.course.id,
            "course_duration": 6,
            "course_type": "online",
            # Attempting to supply slot fields during registration:
            "slot_amount": "500.00",
            "slot_payment_method": "cash",
            "slot_transaction_id": "REG-ATTEMPT",
            "slot_payment_date": "2026-10-29",
        }

        response = self.client.post(url, data=payload, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify application created
        app = InternshipApplication.objects.get(email="new_registered_applicant@example.com")
        # Slot fields were ignored
        self.assertIsNone(app.slot_amount)
        self.assertIsNone(app.slot_payment_method)
        self.assertIsNone(app.slot_transaction_id)
        self.assertIsNone(app.slot_payment_date)

        # Registration email WAS sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Internship Application Received", mail.outbox[0].subject)
        self.assertEqual(mail.outbox[0].to, ["new_registered_applicant@example.com"])
