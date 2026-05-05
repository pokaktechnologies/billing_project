from decimal import Decimal

from django.utils import timezone
from django.db import IntegrityError, transaction
from django.db.models import Sum,Q
from rest_framework import serializers
from twisted.test import obj

from accounts.models import CustomUser, ModulePermission, StaffProfile
from ..models import (
    Batch,
    Center,
    Course,
    CoursePayment,
    Faculty,
    InstallmentItem,
    InstallmentPlan,
    Student,
    StudentCourseEnrollment,
    Class,
    Section,
    SectionDay,
)
from internship.utils import (
    get_installment_due_date_for_staff,
    get_next_unpaid_installment_item,
    get_payment_student,
    get_staff_course_enrollment,
    get_staff_installment_plan,
)
from ..utils import generate_batch_number, generate_student_id, get_clean_prefix

class InstallmentItemSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

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
    id = serializers.IntegerField(required=False)
    items = InstallmentItemSerializer(many=True)
    course_total_fee = serializers.DecimalField(
        source="course.total_fee",
        max_digits=10,
        decimal_places=2,
        read_only=True
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
        read_only_fields = ["course", "course_total_fee"]

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

    faculty_details = serializers.SerializerMethodField()

    students_count = serializers.SerializerMethodField()

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
            "faculty_details",
            'students_count',
            "total_fee",
            "installment_plans",
            "created_at",
            "tax_settings",
            "sgst",
            "cgst",
            "total_tax_percentage",
        ]
        read_only_fields = [
            "created_at",
            "faculty_details",
            "sgst",
            "cgst",
            "total_tax_percentage",
        ]


    def get_students_count(self, obj):
        annotated_count = getattr(obj, "students_count", None)
        if annotated_count is not None:
            return annotated_count
        return obj.enrollments.values("student_id").distinct().count()

    def get_faculty_details(self, obj):
        faculties = set()
        for batch in obj.batches.all():
            for f in batch.faculties.all():
                faculties.add(f)
        return [
            {
                "id": faculty.id,
                "name": faculty.get_full_name()
            }
            for faculty in faculties
        ]

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

        # ── Duplicate total_installments across plans ──
        total_installments_list = [plan.get("total_installments") for plan in plans]
        if len(total_installments_list) != len(set(total_installments_list)):
            duplicates = list(set(n for n in total_installments_list if total_installments_list.count(n) > 1))
            raise serializers.ValidationError(
                f"Duplicate total_installments {duplicates} found. Each plan must have a unique installment count."
            )

        for plan in plans:
            items = plan.get("items", [])
            total_installments = plan.get("total_installments")

            # ── Duplicate installment_number within a plan ──
            installment_numbers = [item["installment_number"] for item in items]
            if len(installment_numbers) != len(set(installment_numbers)):
                duplicates = list(set(n for n in installment_numbers if installment_numbers.count(n) > 1))
                raise serializers.ValidationError(
                    f"Duplicate installment_number(s) {duplicates} found in plan '{total_installments} installments'."
                )

            # ── Installment numbers must be sequential (1, 2, 3...) ──
            expected = list(range(1, total_installments + 1))
            if sorted(installment_numbers) != expected:
                raise serializers.ValidationError(
                    f"Installment numbers must be sequential starting from 1. "
                    f"Expected {expected}, got {sorted(installment_numbers)}."
                )

            # ── Items count must match total_installments ──
            if len(items) != total_installments:
                raise serializers.ValidationError(
                    "Items count must match total_installments."
                )

            # ── Total amount must match course fee ──
            total = sum(i["amount"] for i in items)
            if total != total_fee:
                raise serializers.ValidationError(
                    f"Plan total ({total}) must equal course fee ({total_fee})."
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
        plans_data = validated_data.pop("installment_plans", None)

        # Update course fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # If plans not sent in request, skip sync (partial update)
        if plans_data is None:
            return instance

        with transaction.atomic():
            existing_plans = {p.id: p for p in instance.installment_plans.all()}
            request_plan_ids = set()

            for plan_data in plans_data:
                items_data = plan_data.pop("items")
                plan_id = plan_data.get("id")

                if plan_id and plan_id in existing_plans:
                    # ── CASE 1: Update existing plan (ID preserved) ──
                    plan = existing_plans[plan_id]

                    # Block modification if students enrolled
                    if plan.enrollments.exists():
                        raise serializers.ValidationError(
                            f"Plan '{plan.total_installments} installments' is assigned "
                            f"to students. Modification not allowed."
                        )

                    plan.total_installments = plan_data.get(
                        "total_installments", plan.total_installments
                    )
                    plan.is_active = plan_data.get("is_active", plan.is_active)
                    plan.save()

                    # Sync items within this plan
                    self._sync_items(plan, items_data)
                    request_plan_ids.add(plan.id)

                else:
                    # ── CASE 2: Create new plan ──
                    plan = InstallmentPlan.objects.create(
                        course=instance, **plan_data
                    )
                    for item in items_data:
                        InstallmentItem.objects.create(plan=plan, **item)
                    request_plan_ids.add(plan.id)

            # ── CASE 3: Delete plans not in request ──
            for plan_id, plan in existing_plans.items():
                if plan_id not in request_plan_ids:
                    if plan.enrollments.exists():
                        raise serializers.ValidationError(
                            f"Cannot remove plan '{plan.total_installments} installments' — "
                            f"students are enrolled with it."
                        )
                    plan.delete()

        return instance

    def _sync_items(self, plan, items_data):
        """Sync installment items within a plan (in-place update, preserving IDs)."""
        existing_items = {item.id: item for item in plan.items.all()}
        request_item_ids = set()

        for item_data in items_data:
            item_id = item_data.get("id")

            if item_id and item_id in existing_items:
                # Update existing item (same ID)
                item = existing_items[item_id]
                item.installment_number = item_data["installment_number"]
                item.amount = item_data["amount"]
                item.due_days = item_data["due_days"]
                item.save()
                request_item_ids.add(item.id)
            else:
                # Create new item
                item = InstallmentItem.objects.create(
                    plan=plan,
                    installment_number=item_data["installment_number"],
                    amount=item_data["amount"],
                    due_days=item_data["due_days"],
                )
                request_item_ids.add(item.id)

        # Delete items not in request
        for item_id, item in existing_items.items():
            if item_id not in request_item_ids:
                item.delete()

    
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

        #  1. Prevent duplicate plan (course + total_installments)
        if InstallmentPlan.objects.filter(
            course=instance.course,
            total_installments=total_installments
        ).exclude(id=instance.id).exists():
            raise serializers.ValidationError(
                "Plan with this installment count already exists for this course"
            )

        #  2. Validate items count
        if len(items_data) != total_installments:
            raise serializers.ValidationError(
                "Items count must match total_installments"
            )

        #  3. Validate duplicate installment_number in request
        numbers = [item["installment_number"] for item in items_data]
        if len(numbers) != len(set(numbers)):
            raise serializers.ValidationError(
                "Duplicate installment_number in request"
            )

        with transaction.atomic():

            #  Update plan fields
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

                #  CASE 1: Update using ID
                if item_id and item_id in existing_items:
                    item = existing_items[item_id]

                #  CASE 2: Update using installment_number (AUTO MATCH)
                elif number in existing_by_number:
                    item = existing_by_number[number]

                #  CASE 3: Create new
                else:
                    item = InstallmentItem.objects.create(
                        plan=instance,
                        installment_number=number,
                        amount=item_data["amount"],
                        due_days=item_data["due_days"],
                    )
                    updated_ids.append(item.id)
                    continue

                #  UPDATE fields (including amount change )
                item.installment_number = number
                item.amount = item_data["amount"]
                item.due_days = item_data["due_days"]
                item.save()

                updated_ids.append(item.id)

            #  DELETE removed items
            for item in instance.items.all():
                if item.id not in updated_ids:
                    item.delete()

        return instance
    
#Faculty
class FacultySerializer(serializers.ModelSerializer):
    faculty = serializers.IntegerField(source="id", read_only=True)
    name = serializers.CharField(source="get_full_name", read_only=True)
    faculty_name = serializers.CharField(source="get_full_name", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    email = serializers.CharField(source="user.staff_email", read_only=True)
    phone_number = serializers.CharField(source="user.phone_number", read_only=True)
    course_count = serializers.SerializerMethodField()
    students_count = serializers.SerializerMethodField()

    class Meta:
        model = Faculty
        fields = [
            "id",
            "faculty",
            "user",
            "name",
            "faculty_name",
            "department",
            "department_name",
            "email",
            "phone_number",
            "course_count",
            "students_count",
            "is_active",
        ]

    def get_course_count(self, obj):
        annotated_count = getattr(obj, "course_count", None)
        if annotated_count is not None:
            return annotated_count
        return Course.objects.filter(batches__faculties=obj).distinct().count()

    def get_students_count(self, obj):
        annotated_count = getattr(obj, "students_count", None)
        if annotated_count is not None:
            return annotated_count
        return Student.objects.filter(enrollments__batch__faculties=obj).distinct().count()


#Batch
class BatchSerializer(serializers.ModelSerializer):
    faculties = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Faculty.objects.all(),
        write_only=True,
        required=False
    )

    faculty_details = serializers.SerializerMethodField()
    course_title    = serializers.CharField(source="course.title", read_only=True)
    is_expired      = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Batch
        fields = [
            "id",
            "batch_number",
            "description",
            "faculties",
            "faculty_details",
            "course",
            "course_title",
            "start_date",
            "end_date",
            "is_active",
            "is_expired",
            "created_at",
        ]
        read_only_fields = ["batch_number", "created_at"]

    def get_faculty_details(self, obj):
        return [
            {"id": f.id, "name": f.get_full_name()}
            for f in obj.faculties.all()
        ]

    def get_is_expired(self, obj):
        return timezone.now().date() > obj.end_date

    def validate(self, data):
        end_date   = data.get("end_date", getattr(self.instance, "end_date", None))
        start_date = data.get("start_date", getattr(self.instance, "start_date", None))
        if end_date and start_date and end_date <= start_date:
            raise serializers.ValidationError("end_date must be after start_date.")
        return data

    def create(self, validated_data):
        faculties = validated_data.pop("faculties", [])


        with transaction.atomic():
            validated_data["batch_number"] = generate_batch_number(
                model=Batch,
                field_name="batch_number",
                prefix="BAT",
                length=4,
                use_lock=True
            )
            batch = Batch.objects.create(**validated_data)
            batch.faculties.set(faculties)
            return batch

    def update(self, instance, validated_data):
        faculties    = validated_data.pop("faculties", None)
        new_end_date = validated_data.get("end_date", instance.end_date)

        #  Re-activate batch if end_date extended beyond today
        if new_end_date >= timezone.now().date():
            validated_data["is_active"] = True

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if faculties is not None:
            instance.faculties.set(faculties)

        return instance
        
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


class StudentSerializer(serializers.ModelSerializer):
    profile = StaffProfileSerializer(required=False, allow_null=True)
    batch = serializers.SerializerMethodField()
    batch_number = serializers.SerializerMethodField()
    course = serializers.SerializerMethodField()
    course_title = serializers.SerializerMethodField()
    center_name = serializers.CharField(source="center.name", read_only=True)
    councellor_name = serializers.CharField(source="councellor.get_full_name", read_only=True)
    payment_type = serializers.SerializerMethodField()
    payment_installment_count = serializers.SerializerMethodField()
    student_id = serializers.CharField(read_only=True)
    modules = serializers.ListField(
        child=serializers.ChoiceField(choices=ModulePermission.MODULE_CHOICES),
        write_only=True,
        required=False
    )
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = [
            "id",
            "student_id",
            "profile",
            "full_name",
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
            "modules",
            "is_active",
            "created_at"
        ]
        extra_kwargs = {
            "profile": {"required": False}
        }

    def get_full_name(self, obj):
        return obj.get_full_name()

    def get_batch(self, obj):
        enrollment = obj.enrollments.first()
        return enrollment.batch.id if enrollment and enrollment.batch else None

    def get_batch_number(self, obj):
        enrollment = obj.enrollments.first()
        return enrollment.batch.batch_number if enrollment and enrollment.batch else None

    def get_course(self, obj):
        enrollment = obj.enrollments.first()
        return enrollment.course.id if enrollment and enrollment.course else None

    def get_course_title(self, obj):
        enrollment = obj.enrollments.first()
        return enrollment.course.title if enrollment and enrollment.course else None

    def get_payment_type(self, obj):
        enrollment = obj.enrollments.first()
        return enrollment.installment_plan.id if enrollment and enrollment.installment_plan else None

    def get_payment_installment_count(self, obj):
        enrollment = obj.enrollments.first()
        if enrollment and enrollment.installment_plan:
            return enrollment.installment_plan.total_installments
        return None

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
            modules = validated_data.pop("modules", [])

            # Extract nested data
            profile_data = validated_data.pop("profile", None)

            if not profile_data:
                raise serializers.ValidationError({
                    "profile": "This field is required"
                })

            user_data = profile_data.pop("user", None)

            if not user_data:
                raise serializers.ValidationError({
                    "user": "User data is required"
                })

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

            #  Assign module permissions
            if modules:
                ModulePermission.objects.bulk_create([
                    ModulePermission(user=custom_user, module_name=module)
                    for module in modules
                ])

            # Create Student
            return Student.objects.create(
                student_id=student_id,
                profile=staff_profile,
                **validated_data
            )

    def update(self, instance, validated_data):
        with transaction.atomic():

            modules = validated_data.pop("modules", None)
            profile_data = validated_data.pop("profile", None)

            profile = instance.profile
            user = profile.user  # FIX: always define

            #  Update Student fields
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()

            #  Update Profile + User
            if profile_data:
                user_data = profile_data.pop("user", None)

                # Update StaffProfile
                for attr, value in profile_data.items():
                    setattr(profile, attr, value)
                profile.save()

                if user_data:
                    email = user_data.get("email")
                    password = user_data.pop("password", None)

                    # Email uniqueness check
                    if email and CustomUser.objects.filter(email=email).exclude(id=user.id).exists():
                        raise serializers.ValidationError({
                            "email": "Email already exists"
                        })

                    for attr, value in user_data.items():
                        setattr(user, attr, value)

                    if password:
                        user.set_password(password)

                    user.save()

            #  Update module permissions
            if modules is not None:
                ModulePermission.objects.filter(user=user).delete()

                ModulePermission.objects.bulk_create([
                    ModulePermission(user=user, module_name=module)
                    for module in modules
                ])

            return instance


class StudentCourseEnrollmentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.get_full_name", read_only=True)
    course_title = serializers.CharField(source="course.title", read_only=True)
    batch_number = serializers.CharField(source="batch.batch_number", read_only=True)
    total_installments = serializers.CharField(source="installment_plan.total_installments", read_only=True)

    class Meta:
        model = StudentCourseEnrollment
        fields = [
            "id",
            "student",
            "student_name",
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
        batch = attrs.get("batch")
        installment_plan = attrs.get("installment_plan")
        student = attrs.get("student")

        # ── Batch required ──
        if not batch:
            raise serializers.ValidationError("Batch is required.")

        # ── Installment plan must match course ──
        if installment_plan and installment_plan.course_id != batch.course_id:
            raise serializers.ValidationError(
                f"Installment plan '{installment_plan}' does not belong "
                f"to course '{batch.course.title}'."
            )

        # ── ❗ MAIN VALIDATION: One student → only one course ──
        existing_qs = StudentCourseEnrollment.objects.filter(student=student)

        if self.instance:
            existing_qs = existing_qs.exclude(pk=self.instance.pk)

        if existing_qs.exists():
            raise serializers.ValidationError(
                "This student is already enrolled in a course."
            )

        return attrs
    
class CenterSerializer(serializers.ModelSerializer):
    # country_name = serializers.CharField(source="country.name", read_only=True)
    # state_name = serializers.CharField(source="state.name", read_only=True)

    class Meta:
        model = Center
        fields = [
            "id",
            "name",
            "country_name",
            "state_name",
            "address"
        ]


class CoursePaymentSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(
        source="installments.plan.course.title",
        read_only=True
    )
    installment_amount = serializers.DecimalField(
        source="installments.amount",
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    already_paid = serializers.SerializerMethodField()
    balance = serializers.SerializerMethodField()

    class Meta:
        model = CoursePayment
        fields = [
            "id",
            "student",
            "installments",
            "course_title",
            "installment_amount",
            "already_paid",
            "balance",
            "amount_paid",
            "payment_method",
            "transaction_id",
            "payment_date",
        ]
        read_only_fields = ["payment_date"]

    def get_already_paid(self, obj):
        if not obj.installments:  
            return 0
        return CoursePayment.objects.filter(
            student=obj.student,
            installments=obj.installments,
        ).aggregate(t=Sum("amount_paid"))["t"] or 0

    def get_balance(self, obj):
        if not obj.installments: 
            return 0
        already = self.get_already_paid(obj)
        return obj.installments.amount - already

    def validate(self, data):
        student        = data["student"]
        installments   = data["installments"]
        amount_paid    = data["amount_paid"]
        payment_method = data["payment_method"]
        transaction_id = data.get("transaction_id")

        course = installments.plan.course

        #  Enrollment check
        enrollment = StudentCourseEnrollment.objects.filter(
            student=student,
            course=course,
        ).first()

        if not enrollment:
            raise serializers.ValidationError(
                "Student not enrolled in this course."
            )

        if enrollment.installment_plan and enrollment.installment_plan_id != installments.plan_id:
            raise serializers.ValidationError(
                "This installment plan is not assigned to this student."
            )

        if payment_method != "cash" and not transaction_id:
            raise serializers.ValidationError(
                "Transaction ID required for non-cash payments."
            )

        already_paid = CoursePayment.objects.filter(
            student=student,
            installments=installments,
        ).aggregate(t=Sum("amount_paid"))["t"] or 0

        remaining = installments.amount - already_paid

        if amount_paid <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")

        if amount_paid > remaining:
            raise serializers.ValidationError(
                f"Overpayment! Item due: ₹{installments.amount}, "
                f"Already paid: ₹{already_paid}, "
                f"Max you can pay: ₹{remaining}."
            )

        return data

    def create(self, validated_data):
        with transaction.atomic():
            return super().create(validated_data)

    def update(self, instance, validated_data):
        raise serializers.ValidationError(
            "Payments cannot be updated once created."
        )

class CourceInstallmentListSerializer(serializers.ModelSerializer):
    status         = serializers.SerializerMethodField()
    due_date       = serializers.SerializerMethodField()
    paid_date      = serializers.SerializerMethodField()
    payment_method = serializers.SerializerMethodField()
    total_paid     = serializers.SerializerMethodField()  
    balance        = serializers.SerializerMethodField()  

    class Meta:
        model  = InstallmentItem
        fields = [
            "id",
            "amount",
            "status",
            "due_date",
            "paid_date",
            "payment_method",
            "total_paid",   # new
            "balance",      # new
        ]

    def _get_payments(self, obj):
        """ഈ student-ന്റെ ഈ item-ലേക്കുള്ള എല്ലാ payments"""
        student = get_payment_student(self.context.get("student"))
        if not student:
            return CoursePayment.objects.none()
        return obj.course_payments.filter(student=student).order_by("payment_date")

    def get_total_paid(self, obj):
        return self._get_payments(obj).aggregate(
            t=Sum("amount_paid")
        )["t"] or 0

    def get_balance(self, obj):
        return obj.amount - self.get_total_paid(obj)

    def get_status(self, obj):
        total_paid = self.get_total_paid(obj)
        if total_paid <= 0:
            return "Pending"
        elif total_paid < obj.amount:
            return "Partial"
        return "Paid"

    def get_paid_date(self, obj):
        # Last payment date
        last = self._get_payments(obj).last()
        return last.payment_date if last else None

    def get_payment_method(self, obj):
        last = self._get_payments(obj).last()
        return last.payment_method if last else "-"

    def get_due_date(self, obj):
        student = self.context.get("student")
        if not student:
            return None
        return get_installment_due_date_for_staff(student, obj)



class StudentPaymentDetailSerializer(serializers.ModelSerializer):
    student_full_name = serializers.SerializerMethodField()
    student_code = serializers.CharField(source="student.student_id")
    phone_number = serializers.CharField(source="student.profile.phone_number")
    email = serializers.CharField(source="student.profile.user.email")

    course_title = serializers.CharField(source="course.title")
    course_id = serializers.CharField(source="course.id")
    course_total_fee = serializers.DecimalField(
        source="course.total_fee",
        max_digits=10,
        decimal_places=2,
        coerce_to_string=True,
    )

    total_paid = serializers.SerializerMethodField()
    pending_fee = serializers.SerializerMethodField()
    next_due_date = serializers.SerializerMethodField()
    installment_list = serializers.SerializerMethodField()

    class Meta:
        model = StudentCourseEnrollment
        fields = [
            "id",
            "student_full_name",
            "student_code",
            "phone_number",
            "email",
            "course_title",
            "course_id",
            "course_total_fee",
            "total_paid",
            "pending_fee",
            "next_due_date",
            "installment_list",
        ]

    # Decimal formatter — always returns string like "15000.00"
    def format_decimal(self, value):
        return str(Decimal(str(value)).quantize(Decimal("0.00")))

    # Student full name
    def get_student_full_name(self, obj):
        user = obj.student.profile.user
        return f"{user.first_name} {user.last_name}"

    # Total paid
    def get_total_paid(self, obj):
        payments = [
            p for p in obj.student.course_payments.all()
            if p.installments and p.installments.plan_id == obj.installment_plan_id
        ]
        total = sum((p.amount_paid for p in payments), Decimal("0.00"))
        return self.format_decimal(total)

    # Pending fee
    def get_pending_fee(self, obj):
        total = Decimal(str(obj.course.total_fee))
        paid = Decimal(self.get_total_paid(obj))
        return self.format_decimal(total - paid)

    # Next due date
    def get_next_due_date(self, obj):
        if not obj.installment_plan:
            return None

        next_installment = get_next_unpaid_installment_item(
            obj.student,
            obj.course,
            preferred_plan=obj.installment_plan,
        )

        if not next_installment:
            return None

        return get_installment_due_date_for_staff(
            obj.student,
            next_installment,
        )

    # Installment list
    def get_installment_list(self, obj):
        plan = obj.installment_plan
        if not plan:
            return []

        student = obj.student
        all_payments = list(student.course_payments.all())

        result = []

        for item in plan.items.all():
            payments = [
                p for p in all_payments
                if p.installments_id == item.id
            ]

            total_paid = sum((p.amount_paid for p in payments), Decimal("0.00"))
            item_amount = Decimal(str(item.amount))

            # Status logic
            if total_paid == 0:
                status = "Pending"
            elif total_paid < item_amount:
                status = "Partial"
            else:
                status = "Paid"

            first_payment = payments[0] if payments else None

            result.append({
                "id": item.id,
                "amount": self.format_decimal(item_amount),
                "status": status,
                "due_date": get_installment_due_date_for_staff(student, item),
                "paid_date": first_payment.payment_date if first_payment else None,
                "payment_method": first_payment.payment_method if first_payment else None,
                "total_paid": self.format_decimal(total_paid),
                "balance": self.format_decimal(item_amount - total_paid),
            })

        return result

class ClassListCreateSerializer(serializers.ModelSerializer):
    center_name    = serializers.CharField(source="center.name", read_only=True)
    sections_count = serializers.SerializerMethodField()

    class Meta:
        model  = Class
        fields = ["id", "name", "center", "center_name", "sections_count", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]

    def get_sections_count(self, obj):
        #  Only count sections with active batches
        return obj.sections.filter(
            batch__is_active=True,
            batch__end_date__gte=timezone.now().date()
        ).count()


class SectionSerializer(serializers.ModelSerializer):
    days = serializers.ListField(
        child=serializers.ChoiceField(choices=SectionDay.DAYS),
        write_only=True
    )
    days_display     = serializers.SerializerMethodField(read_only=True)
    course_title     = serializers.CharField(source="batch.course.title", read_only=True)
    batch_number     = serializers.CharField(source="batch.batch_number", read_only=True)
    duration_minutes = serializers.SerializerMethodField(read_only=True)
    students_count   = serializers.SerializerMethodField(read_only=True)
    is_active        = serializers.BooleanField(source="batch.is_active", read_only=True)

    class Meta:
        model  = Section
        fields = [
            "id",
            "class_obj",
            "batch",
            "start_time",
            "end_time",
            "students_count",
            "days",
            "days_display",
            "course_title",
            "batch_number",
            "duration_minutes",
            "is_active",
        ]

    def get_students_count(self, obj):
        return obj.batch.enrollments.count()
        

    def get_days_display(self, obj):
        return [d.day for d in obj.days.all()]

    def get_duration_minutes(self, obj):
        from datetime import datetime, date
        start = datetime.combine(date.today(), obj.start_time)
        end   = datetime.combine(date.today(), obj.end_time)
        diff  = int((end - start).total_seconds() / 60)
        hours, mins = divmod(diff, 60)
        return f"{hours} hr {mins} min" if mins else f"{hours} hr"

    def validate_days(self, value):
        if not value:
            raise serializers.ValidationError("At least one day is required.")
        if len(value) != len(set(value)):
            raise serializers.ValidationError("Duplicate days are not allowed.")
        return value

    def validate(self, data):
        # 1. Time sanity check
        if data["start_time"] >= data["end_time"]:
            raise serializers.ValidationError("End time must be greater than start time.")

        class_obj  = data.get("class_obj")
        start_time = data.get("start_time")
        end_time   = data.get("end_time")
        days       = data.get("days", [])
        today      = timezone.now().date()

        #  Overlap check — only against ACTIVE, NON-EXPIRED batch sections
        qs = Section.objects.filter(
            class_obj=class_obj,
            start_time__lt=end_time,
            end_time__gt=start_time,
            batch__is_active=True,
            batch__end_date__gte=today,       # expired batch = free slot
        ).prefetch_related("days")

        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)

        for section in qs:
            existing_days = set(section.days.values_list("day", flat=True))
            conflict_days = set(days) & existing_days
            if conflict_days:
                raise serializers.ValidationError(
                    f"Time conflict on {', '.join(sorted(conflict_days))} — "
                    f"'{section.batch}' already runs {section.start_time:%H:%M} "
                    f"to {section.end_time:%H:%M} in this class."
                )

        return data

    @transaction.atomic
    def create(self, validated_data):
        days    = validated_data.pop("days")
        section = Section.objects.create(**validated_data)
        SectionDay.objects.bulk_create([
            SectionDay(section=section, day=day) for day in days
        ])
        return section

    @transaction.atomic
    def update(self, instance, validated_data):
        days = validated_data.pop("days", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if days is not None:
            instance.days.all().delete()
            SectionDay.objects.bulk_create([
                SectionDay(section=instance, day=day) for day in days
            ])
        return instance


class ClassDetailSerializer(serializers.ModelSerializer):
    center_name    = serializers.CharField(source="center.name", read_only=True)
    sections_count = serializers.SerializerMethodField()
    sections       = serializers.SerializerMethodField()

    class Meta:
        model  = Class
        fields = ["id", "name", "center", "center_name", "sections_count", "sections", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]

    def _get_filtered_sections_qs(self, obj):
        today   = timezone.now().date()
        request = self.context.get("request")

        qs = obj.sections.filter(
            batch__is_active=True,
            batch__end_date__gte=today
        ).select_related("batch__course").prefetch_related("days")

        if request:
            # 1. Course filter
            course_id = request.query_params.get("course")
            if course_id:
                qs = qs.filter(batch__course__id=course_id)

            # 2. Batch filter
            batch_id = request.query_params.get("batch")
            if batch_id:
                qs = qs.filter(batch__id=batch_id)

            # 3. Day filter  (mon, tue, wed...)
            day = request.query_params.get("day")
            if day:
                qs = qs.filter(days__day=day)

            # 4. Search (course title or batch number)
            search = request.query_params.get("search")
            if search:
                qs = qs.filter(
                    Q(batch__course__title__icontains=search) |
                    Q(batch__batch_number__icontains=search)
                )

        return qs

    def get_sections_count(self, obj):
        # filtered count ആണ് return ചെയ്യുന്നത്
        return self._get_filtered_sections_qs(obj).count()

    def get_sections(self, obj):
        qs = self._get_filtered_sections_qs(obj)
        return SectionSerializer(qs, many=True, context=self.context).data

from rest_framework import serializers
from decimal import Decimal


class StudentPaymentSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    course_title = serializers.SerializerMethodField()
    installment_plan = serializers.SerializerMethodField()
    total_fee = serializers.SerializerMethodField()
    paid_amount = serializers.SerializerMethodField()
    pending_amount = serializers.SerializerMethodField()
    next_due_date = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = [
            "id",
            "student_name",
            "student_id",
            "course_title",
            "installment_plan",
            "total_fee",
            "paid_amount",
            "pending_amount",
            "next_due_date",
        ]

    # Decimal formatter
    def format_decimal(self, value):
        return str(Decimal(str(value)).quantize(Decimal("0.00")))

    # Cache enrollment
    def get_enrollment(self, obj):
        if not hasattr(obj, "_cached_enrollment"):
            obj._cached_enrollment = obj.enrollments.first()
        return obj._cached_enrollment

    # Student name
    def get_student_name(self, obj):
        user = obj.profile.user
        return f"{user.first_name} {user.last_name}"

    # Course title
    def get_course_title(self, obj):
        enrollment = self.get_enrollment(obj)
        return getattr(enrollment.course, "title", None) if enrollment else None

    # Total fee
    def get_total_fee(self, obj):
        enrollment = self.get_enrollment(obj)
        if enrollment:
            return self.format_decimal(
                getattr(enrollment.course, "total_fee", Decimal("0.00"))
            )
        return self.format_decimal(Decimal("0.00"))

    # Paid amount
    def get_paid_amount(self, obj):
        enrollment = self.get_enrollment(obj)
        if not enrollment or not enrollment.installment_plan:
            return self.format_decimal(Decimal("0.00"))

        payments = [
            p for p in obj.course_payments.all()
            if p.installments and p.installments.plan_id == enrollment.installment_plan_id
        ]

        total = sum((p.amount_paid for p in payments), Decimal("0.00"))
        return self.format_decimal(total)

    # Pending amount
    def get_pending_amount(self, obj):
        total = Decimal(self.get_total_fee(obj))
        paid = Decimal(self.get_paid_amount(obj))
        return self.format_decimal(total - paid)

    # Installment plan
    def get_installment_plan(self, obj):
        enrollment = self.get_enrollment(obj)
        if enrollment and enrollment.installment_plan:
            plan = enrollment.installment_plan
            return {
                "id": plan.id,
                "total_installments": plan.total_installments,
            }
        return None

    # Next due date
    def get_next_due_date(self, obj):
        enrollment = self.get_enrollment(obj)
        if not enrollment or not enrollment.installment_plan:
            return None

        next_installment = get_next_unpaid_installment_item(
            obj,
            enrollment.course,
            preferred_plan=enrollment.installment_plan,
        )

        if not next_installment:
            return None

        return get_installment_due_date_for_staff(
            obj,
            next_installment,
        )

class AcademicDashboardSerializer(serializers.Serializer):
    stats = serializers.DictField()
    charts = serializers.DictField()
    recent_interns = serializers.ListField()
    top_faculty = serializers.ListField()



class AvailableStudentSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    email     = serializers.SerializerMethodField()
    center_name = serializers.SerializerMethodField()

    class Meta:
        model  = Student
        fields = ['id', 'student_id', 'full_name', 'email', 'center_name']

    def get_full_name(self, obj):
        return obj.get_full_name()

    def get_email(self, obj):
        return obj.profile.user.email

    def get_center_name(self, obj):
        return obj.center.name if obj.center else None
