from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from accounts.models import Department, SalesPerson, StaffProfile
from finance.models import TaxSettings
from internship.models import (
    Center, Course, Batch, Student, StudentCourseEnrollment,
    InstallmentPlan, InstallmentItem, InternshipApplication, CoursePayment
)
from internship.utils import StudentConversionService

User = get_user_model()


class Command(BaseCommand):
    help = "Seed persistent counsellor conversion data directly into the active database"

    def handle(self, *args, **options):
        self.stdout.write("--- Seeding Counsellor Conversion Data into Active Database ---")

        today = date.today()

        # 1. Department & TaxSettings
        department, _ = Department.objects.get_or_create(
            name="Admissions & Career Counselling"
        )
        tax_settings, _ = TaxSettings.objects.get_or_create(
            name="Standard GST",
            defaults={"rate": 18.00}
        )

        # 2. Counsellor (SalesPerson)
        counsellor_a, created_ca = SalesPerson.objects.get_or_create(
            email="priya.counsellor@pokak.com",
            defaults={
                "first_name": "Priya",
                "last_name": "Sharma",
                "phone": "9876500011",
                "mobile": "9876500012",
                "incentive": 500,
                "designation": "Senior Career Counsellor",
            }
        )
        self.stdout.write(f"Counsellor A: ID={counsellor_a.id}, Name={counsellor_a.first_name} {counsellor_a.last_name} (Created: {created_ca})")

        counsellor_b, created_cb = SalesPerson.objects.get_or_create(
            email="arun.counsellor@pokak.com",
            defaults={
                "first_name": "Arun",
                "last_name": "Kumar",
                "phone": "9876500021",
                "mobile": "9876500022",
                "incentive": 300,
                "designation": "Junior Counsellor",
            }
        )
        self.stdout.write(f"Counsellor B: ID={counsellor_b.id}, Name={counsellor_b.first_name} {counsellor_b.last_name} (Created: {created_cb})")

        # 3. Center, Course & Batch
        center, _ = Center.objects.get_or_create(
            name="Kochi Tech Hub",
            defaults={"country_name": "India", "state_name": "Kerala"}
        )

        course_1, _ = Course.objects.get_or_create(
            title="Full Stack Python Development",
            defaults={
                "description": "Python, Django, React Full Stack Program",
                "department": department,
                "total_fee": 45000,
                "tax_settings": tax_settings,
            }
        )

        course_2, _ = Course.objects.get_or_create(
            title="Data Science & Machine Learning",
            defaults={
                "description": "AI, ML, and Data Analysis Program",
                "department": department,
                "total_fee": 55000,
                "tax_settings": tax_settings,
            }
        )

        batch, _ = Batch.objects.get_or_create(
            batch_number="BATCH-2026-PY01",
            defaults={
                "course": course_1,
                "start_date": today,
                "end_date": today + timedelta(days=180),
            }
        )

        # 4. Student 1: Converted from Internship Application
        app, app_created = InternshipApplication.objects.get_or_create(
            email="rohit.verma@example.com",
            defaults={
                "first_name": "Rohit",
                "last_name": "Verma",
                "primary_phone": "+919876540001",
                "dob": "2000-05-10",
                "gender": "male",
                "qualification": "ug",
                "course_name": "Full Stack Python",
                "address": "Kochi Infopark Road",
                "state": "Kerala",
                "district": "Ernakulam",
                "pincode": "682030",
                "where_did_you_find_us": "google",
                "course_duration": 6,
                "course_type": "offline",
                "course": course_1,
                "councellor": counsellor_a,
            }
        )
        if not app.councellor:
            app.councellor = counsellor_a
            app.save()

        if not app.is_converted:
            student_1 = StudentConversionService.convert(
                application=app,
                email="rohit.student@example.com",
                password="TestPassword@123",
                center=center,
                start_date=today - timedelta(days=20),
                councellor=counsellor_a,
                status="active",
            )
            enrollment_1, _ = StudentCourseEnrollment.objects.get_or_create(
                student=student_1,
                course=course_1,
                defaults={
                    "batch": batch,
                    "payment_plan_type": "custom_installment",
                    "custom_installments": 2,
                    "advance_amount": 10000,
                    "payment_method": "upi",
                    "transaction_id": "TXN-APP-001",
                    "payment_date": today - timedelta(days=20),
                }
            )
            self.stdout.write(f"Student 1 (Converted): ID={student_1.id}, Code={student_1.student_id}, Name=Rohit Verma")
        else:
            student_1 = app.converted_students
            if student_1 and student_1.councellor != counsellor_a:
                student_1.councellor = counsellor_a
                student_1.save()
            self.stdout.write(f"Student 1 already converted: ID={student_1.id if student_1 else 'None'}")

        # Ensure first CoursePayment for Student 1
        if student_1:
            p1 = CoursePayment.objects.filter(transaction_id="TXN-PERM-PY001").first()
            if not p1:
                p1 = CoursePayment.objects.create(
                    transaction_id="TXN-PERM-PY001",
                    student=student_1,
                    amount_paid=10000.00,
                    payment_date=today - timedelta(days=20),
                    payment_method="upi",
                    payment_type="installment",
                )
            self.stdout.write(f"  First Payment for Student 1: TXN={p1.transaction_id}, Amount={p1.amount_paid}, Date={p1.payment_date}")

        # 5. Student 2: Directly Created (Assigned to Counsellor A)
        user_2, u2_created = User.objects.get_or_create(
            email="sneha.patel@example.com",
            defaults={
                "first_name": "Sneha",
                "last_name": "Patel",
            }
        )
        if u2_created:
            user_2.set_password("TestPassword@123")
            user_2.save()

        profile_2, _ = StaffProfile.objects.get_or_create(
            user=user_2,
            defaults={
                "phone_number": "+919876540002",
                "staff_email": "sneha.patel@example.com",
            }
        )

        student_2, s2_created = Student.objects.get_or_create(
            student_id="STU-DIR-002",
            defaults={
                "profile": profile_2,
                "center": center,
                "start_date": today - timedelta(days=10),
                "status": "active",
                "councellor": counsellor_a,
            }
        )
        if not s2_created and student_2.councellor != counsellor_a:
            student_2.councellor = counsellor_a
            student_2.save()

        enrollment_2, _ = StudentCourseEnrollment.objects.get_or_create(
            student=student_2,
            course=course_2,
            defaults={
                "payment_plan_type": "custom_installment",
                "custom_installments": 2,
                "advance_amount": 15000,
                "payment_method": "cash",
                "payment_date": today - timedelta(days=10),
            }
        )

        p2, p2_created = CoursePayment.objects.get_or_create(
            transaction_id="TXN-PERM-DS002",
            defaults={
                "student": student_2,
                "amount_paid": 15000.00,
                "payment_date": today - timedelta(days=10),
                "payment_method": "cash",
                "payment_type": "installment",
            }
        )
        self.stdout.write(f"Student 2 (Direct): ID={student_2.id}, Code={student_2.student_id}, Name=Sneha Patel")
        self.stdout.write(f"  First Payment for Student 2: TXN={p2.transaction_id}, Amount={p2.amount_paid}, Date={p2.payment_date}")

        # 6. Student 3: Directly Created, No Payment Yet
        user_3, u3_created = User.objects.get_or_create(
            email="ananya.sharma@example.com",
            defaults={
                "first_name": "Ananya",
                "last_name": "Sharma",
            }
        )
        if u3_created:
            user_3.set_password("TestPassword@123")
            user_3.save()

        profile_3, _ = StaffProfile.objects.get_or_create(
            user=user_3,
            defaults={
                "phone_number": "+919876540003",
                "staff_email": "ananya.sharma@example.com",
            }
        )

        student_3, s3_created = Student.objects.get_or_create(
            student_id="STU-DIR-003",
            defaults={
                "profile": profile_3,
                "center": center,
                "start_date": today,
                "status": "active",
                "councellor": counsellor_a,
            }
        )
        if not s3_created and student_3.councellor != counsellor_a:
            student_3.councellor = counsellor_a
            student_3.save()

        enrollment_3, _ = StudentCourseEnrollment.objects.get_or_create(
            student=student_3,
            course=course_1,
            defaults={
                "payment_plan_type": "custom_installment",
                "custom_installments": 2,
            }
        )
        self.stdout.write(f"Student 3 (No Payment): ID={student_3.id}, Code={student_3.student_id}, Name=Ananya Sharma, First Payment=None")

        # Also assign counsellor_a to existing student 1 if any exists
        existing_s1 = Student.objects.filter(id=1).first()
        if existing_s1 and not existing_s1.councellor:
            existing_s1.councellor = counsellor_a
            existing_s1.save()
            self.stdout.write(f"Assigned existing Student 1 ({existing_s1.student_id}) to Counsellor A")

        self.stdout.write(self.style.SUCCESS("--- Finished Seeding Persistent Data in Database 'billing' ---"))
