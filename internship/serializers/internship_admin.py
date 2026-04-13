from attr import attrs
from rest_framework import serializers

from accounts.models import CustomUser
from accounts.views import user
from ..models import *
from django.db import transaction
from ..utils import generate_batch_number, generate_student_id, get_clean_prefix

class InstallmentItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstallmentItem
        fields = [
            "id",
            "plan",
            "installment_number",
            "amount",
            "due_days",
        ]
        read_only_fields = ["plan"]

class InstallmentPlanSerializer(serializers.ModelSerializer):
    items = InstallmentItemSerializer(many=True)
    course_total_fee = serializers.DecimalField(
        source="course.total_fee",
        max_digits=10,
        decimal_places=2
    )


    class Meta:
        model = InstallmentPlan
        fields = [
            "id",
            "course",
            "course_total_fee",
            "total_installments",
            "is_active",
            "items",
        ]
        read_only_fields = ["course", "total_installments"]

    def create(self, validated_data):
        items_data = validated_data.pop("items")
        plan = InstallmentPlan.objects.create(**validated_data)

        for item in items_data:
            InstallmentItem.objects.create(plan=plan, **item)

        return plan

class CourseSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(
        source="department.name",
        read_only=True
    )

    sudents_count = serializers.SerializerMethodField()

    installment_plans = InstallmentPlanSerializer(
        many=True,
        required=False
    )

    sgst = serializers.SerializerMethodField()
    cgst = serializers.SerializerMethodField()
    total_tax_percentage = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            "id",
            "title",
            "description",
            "is_active",
            "department",
            "department_name",
            'sudents_count',
            "total_fee",
            "installment_plans",
            "created_at",
            "tax_settings",
            "sgst",
            "cgst",
            "total_tax_percentage",
        ]
        read_only_fields = ["created_at", "sgst", "cgst", "total_tax_percentage"]


    def get_sudents_count(self, obj):
        return obj.students.count()

    # ---------- TAX LOGIC ----------
    def get_sgst(self, obj):
        if not obj.tax_settings:
            return 0
        return obj.tax_settings.rate / 2

    def get_cgst(self, obj):
        if not obj.tax_settings:
            return 0
        return obj.tax_settings.rate / 2
    
    def get_total_tax_percentage(self, obj):
        if not obj.tax_settings:
            return 0
        return obj.tax_settings.rate

    def validate(self, data):
        plans = data.get("installment_plans", [])
        total_fee = data.get("total_fee", getattr(self.instance, "total_fee", None))

        for plan in plans:
            items = plan.get("items", [])

            total = sum(i["amount"] for i in items)

            if total != total_fee:
                raise serializers.ValidationError(
                    f"Plan total must equal course fee ({total_fee})"
                )

            if len(items) != plan.get("total_installments"):
                raise serializers.ValidationError(
                    "Items count must match total_installments"
                )

        return data


    # ---------- CREATE ----------
    def create(self, validated_data):
        plans_data = validated_data.pop("installment_plans", [])
        course = Course.objects.create(**validated_data)

        for plan_data in plans_data:
            items_data = plan_data.pop("items")

            plan = InstallmentPlan.objects.create(course=course, **plan_data)

            for item in items_data:
                InstallmentItem.objects.create(plan=plan, **item)

        return course

    # ---------- UPDATE ----------
    def update(self, instance, validated_data):
        validated_data.pop("installment_plans", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
    

from django.db import transaction
from rest_framework import serializers


class InstallmentItemUpdateSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = InstallmentItem
        fields = ["id", "installment_number", "amount", "due_days"]


class InstallmentPlanUpdateSerializer(serializers.ModelSerializer):
    items = InstallmentItemUpdateSerializer(many=True)

    class Meta:
        model = InstallmentPlan
        fields = ["id", "total_installments", "is_active", "items"]

    def update(self, instance, validated_data):
        items_data = validated_data.pop("items", [])

        total_installments = validated_data.get(
            "total_installments",
            instance.total_installments
        )
        if instance.enrollments.exists():
            raise serializers.ValidationError(
                "This installment plan is already assigned to students. Modification not allowed."
            )

        # ✅ 1. Prevent duplicate plan (course + total_installments)
        if InstallmentPlan.objects.filter(
            course=instance.course,
            total_installments=total_installments
        ).exclude(id=instance.id).exists():
            raise serializers.ValidationError(
                "Plan with this installment count already exists for this course"
            )

        # ✅ 2. Validate items count
        if len(items_data) != total_installments:
            raise serializers.ValidationError(
                "Items count must match total_installments"
            )

        # ✅ 3. Validate duplicate installment_number in request
        numbers = [item["installment_number"] for item in items_data]
        if len(numbers) != len(set(numbers)):
            raise serializers.ValidationError(
                "Duplicate installment_number in request"
            )

        with transaction.atomic():

            # ✅ Update plan fields
            instance.total_installments = total_installments
            instance.is_active = validated_data.get(
                "is_active", instance.is_active
            )
            instance.save()

            existing_items = {
                item.id: item for item in instance.items.all()
            }

            # map by installment_number (IMPORTANT FIX)
            existing_by_number = {
                item.installment_number: item for item in instance.items.all()
            }

            updated_ids = []

            for item_data in items_data:
                item_id = item_data.get("id")
                number = item_data["installment_number"]

                # 🔹 CASE 1: Update using ID
                if item_id and item_id in existing_items:
                    item = existing_items[item_id]

                # 🔹 CASE 2: Update using installment_number (AUTO MATCH)
                elif number in existing_by_number:
                    item = existing_by_number[number]

                # 🔹 CASE 3: Create new
                else:
                    item = InstallmentItem.objects.create(
                        plan=instance,
                        installment_number=number,
                        amount=item_data["amount"],
                        due_days=item_data["due_days"],
                    )
                    updated_ids.append(item.id)
                    continue

                # 🔹 UPDATE fields (including amount change 🔥)
                item.installment_number = number
                item.amount = item_data["amount"]
                item.due_days = item_data["due_days"]
                item.save()

                updated_ids.append(item.id)

            # 🔹 DELETE removed items
            for item in instance.items.all():
                if item.id not in updated_ids:
                    item.delete()

        return instance
    
#Faculty
class FacultySerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="get_full_name", read_only=True)

    class Meta:
        model = Faculty
        fields = ["id", "user", "name"]

class CourseFacultySerializer(serializers.ModelSerializer):
    faculty_name    = serializers.CharField(source="get_full_name", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    email           = serializers.CharField(source="faculty.user.staff_email", read_only=True)
    phone_number    = serializers.CharField(source="faculty.user.phone_number", read_only=True)

    course_count    = serializers.IntegerField(read_only=True)
    students_count  = serializers.IntegerField(read_only=True)

    class Meta:
        model = CourseFaculty
        fields = [
            "id",
            "faculty",
            "faculty_name",
            "department",
            "department_name",
            "email",
            "phone_number",
            "course_count",
            "students_count",
            "is_active",
        ]
#Batch
class BatchSerializer(serializers.ModelSerializer):
    faculty_name = serializers.CharField(source="faculty.get_full_name", read_only=True)
    course_title = serializers.CharField(source="course.title", read_only=True)

    class Meta:
        model = Batch
        fields = [
            "id",
            "batch_number",
            "description",
            "faculty",
            "faculty_name",
            "course",
            "course_title",
            "start_date",
            "end_date",
            "is_active",
            "created_at"
        ]
        read_only_fields = ["created_at", "batch_number"]
    def create(self, validated_data):
        course = validated_data.get("course")

        prefix = get_clean_prefix(course.title)

        with transaction.atomic():
            validated_data["batch_number"] = generate_batch_number(
                model=Batch,
                field_name="batch_number",
                prefix=prefix,
                length=3,
                course=course
            )

            return super().create(validated_data)
        
class StaffUserSerializer(serializers.ModelSerializer):

    class Meta:
        model = CustomUser
        fields = ["id", "first_name", "last_name", "gender", "email", "password"]
        extra_kwargs = {
            "password": {"write_only": True},
            "email": {"validators": []}
        }

class StaffProfileSerializer(serializers.ModelSerializer):
    user = StaffUserSerializer()

    class Meta:
        model = StaffProfile
        fields = [
            "id",
            "user",
            "staff_email",
            "phone_number",
            "date_of_birth",
            "profile_image",
            "address"
        ]

from rest_framework import serializers
from django.db import transaction

class StudentSerializer(serializers.ModelSerializer):
    profile = StaffProfileSerializer(required=False, allow_null=True)
    course_title = serializers.CharField(source="course.title", read_only=True)
    batch_number = serializers.CharField(source="batch.batch_number", read_only=True)
    center_name = serializers.CharField(source="center.name", read_only=True)
    councellor_name = serializers.CharField(source="councellor.get_full_name", read_only=True)
    payment_installment_count = serializers.CharField(source="payment_type.total_installments", read_only=True)
    class Meta:
        model = Student
        fields = [
            "id",
            "profile",
            "student_id",
            "center",
            "center_name",
            "course",
            "course_title",
            "batch",
            "batch_number",
            "payment_type",
            "payment_installment_count",
            "start_date",
            "councellor",
            "councellor_name",
            "is_active",
            "created_at"
        ]
        extra_kwargs = {
            "profile": {"required": False}
        }

    def validate(self, attrs):
        course = attrs.get("course")
        batch = attrs.get("batch")

        if batch and course and batch.course != course:
            raise serializers.ValidationError({
                "batch": "Selected batch does not belong to the selected course."
            })

        return attrs

    def create(self, validated_data):
        with transaction.atomic():

            # Extract nested data
            profile_data = validated_data.pop("profile")
            user_data = profile_data.pop("user")

            password = user_data.pop("password", None)

            if not password:
                raise serializers.ValidationError({
                    "password": "Password is required"
                })

            if CustomUser.objects.filter(email=user_data.get("email")).exists():
                raise serializers.ValidationError({
                    "email": "Email already exists"
                })

            # Generate Student ID
            student_id = generate_student_id(
                model=Student,
                field_name="student_id",
                prefix="ST",
                length=3
            )

            # Create CustomUser
            custom_user = CustomUser.objects.create_user(
                **user_data,
                password=password
            )

            # Create StaffProfile
            staff_profile = StaffProfile.objects.create(
                user=custom_user,
                **profile_data
            )

            # Create Student
            return Student.objects.create(
                student_id=student_id,
                profile=staff_profile,
                **validated_data
            )
        
    def update(self, instance, validated_data):
        with transaction.atomic():

            profile_data = validated_data.pop("profile", None)

            # Update Student fields
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()

            if profile_data:
                user_data = profile_data.pop("user", None)

                # Update StaffProfile
                profile = instance.profile
                for attr, value in profile_data.items():
                    setattr(profile, attr, value)
                profile.save()

                # Update CustomUser
                if user_data:
                    user = profile.user

                    email = user_data.get("email")
                    password = user_data.pop("password", None)

                    # Email uniqueness check (correct place)
                    if email and CustomUser.objects.filter(email=email).exclude(id=user.id).exists():
                        raise serializers.ValidationError({
                            "email": "Email already exists"
                        })

                    for attr, value in user_data.items():
                        setattr(user, attr, value)

                    if password:
                        user.set_password(password)

                    user.save()

            return instance
        
class StudentCourseEnrollmentSerializer(serializers.ModelSerializer):
    sudent_name = serializers.CharField(source="student.profile.get_full_name", read_only=True)
    course_title = serializers.CharField(source="course.title", read_only=True)
    batch_number = serializers.CharField(source="batch.batch_number", read_only=True)
    total_installments = serializers.CharField(source="installment_plan.total_installments", read_only=True)

    class Meta:
        model = StudentCourseEnrollment
        fields = [
            "id",
            "student",
            "sudent_name",
            "course",
            "course_title",
            "batch",
            "batch_number",
            "installment_plan",
            "total_installments",
            "enrollment_date"
        ]
        read_only_fields = ["course"]

    def validate(self, attrs):
        if not attrs.get("batch"):
            raise serializers.ValidationError("Batch is required.")
        return attrs
    
class CenterSerializer(serializers.ModelSerializer):
    country_name = serializers.CharField(source="country.name", read_only=True)
    state_name = serializers.CharField(source="state.name", read_only=True)

    class Meta:
        model = Center
        fields = [
            "id",
            "name",
            "country",
            "country_name",
            "state",
            "state_name",
            "address"
        ]