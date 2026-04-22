from accounts.models import JobDetail
from internship.models import Student
from django.db import transaction
from datetime import date, datetime

year = datetime.now().year
prefix = f"ST{year}"
length = 3

latest = Student.objects.filter(
    student_id__startswith=prefix
).order_by("-student_id").first()

if latest:
    current_number = int(latest.student_id[-length:])
else:
    current_number = 0

interns = JobDetail.objects.select_related("staff__user").filter(job_type="internship")

internship_staff = JobDetail.objects.filter(job_type="internship").count()
print(f"Total internship staff: {internship_staff}")

created = 0
skipped = 0

with transaction.atomic():
    for job in interns:
        profile = job.staff

        if hasattr(profile, "student_profile"):
            skipped += 1
            continue

        current_number += 1
        student_id = f"{prefix}{current_number:0{length}d}"

        Student.objects.create(
            student_id=student_id,
            profile=profile,
            start_date=job.start_date or date.today(),
            is_active=True
        )

        created += 1
        print(profile.user.email)

print(f"Created: {created}, Skipped: {skipped}")