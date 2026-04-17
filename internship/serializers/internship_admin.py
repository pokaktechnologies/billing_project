from django.db import IntegrityError, transaction
from django.db.models import Sum
from rest_framework import serializers

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
    faculties = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Faculty.objects.all(),
        write_only=True,
        required=False
    )

    faculty_details = serializers.SerializerMethodField()

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
            "faculties",
            "faculty_details",
            'sudents_count',
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


    def get_sudents_count(self, obj):
        return obj.students.count()

    def get_faculty_details(self, obj):
        return [
            {
                "id": faculty.id,
                "name": faculty.get_full_name()
            }
            for faculty in obj.faculties.all()
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
        faculties = validated_data.pop("faculties", [])
        course = Course.objects.create(**validated_data)
        course.faculties.set(faculties)

        for plan_data in plans_data:
            items_data = plan_data.pop("items")

            plan = InstallmentPlan.objects.create(course=course, **plan_data)

            for item in items_data:
                InstallmentItem.objects.create(plan=plan, **item)

        return course

    # ---------- UPDATE ----------
    def update(self, instance, validated_data):
        validated_data.pop("installment_plans", None)
        faculties = validated_data.pop("faculties", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if faculties is not None:
            instance.faculties.set(faculties)
        return instance
    
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
        return obj.courses.count()

    def get_students_count(self, obj):
        annotated_count = getattr(obj, "students_count", None)
        if annotated_count is not None:
            return annotated_count
        return Student.objects.filter(batch__faculties=obj).distinct().count()


#Batch
class BatchSerializer(serializers.ModelSerializer):
    faculties = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Faculty.objects.all(),
        write_only=True,
        required=False
    )

    faculty_details = serializers.SerializerMethodField()

    course_title = serializers.CharField(source="course.title", read_only=True)

    class Meta:
        model = Batch
        fields = [
            "id",
            "batch_number",
            "description",
            "faculties",        # write
            "faculty_details",  # read
            "course",
            "course_title",
            "start_date",
            "end_date",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["batch_number", "created_at"]

    #  Clean faculty response
    def get_faculty_details(self, obj):
        return [
            {
                "id": faculty.id,
                "name": faculty.get_full_name()
            }
            for faculty in obj.faculties.all()
        ]

    #  Create
    def create(self, validated_data):
        faculties = validated_data.pop("faculties", [])
        course = validated_data.get("course")

        prefix = get_clean_prefix(course.title)

        with transaction.atomic():
            validated_data["batch_number"] = generate_batch_number(
                model=Batch,
                field_name="batch_number",
                prefix=prefix,
                length=3,
                course=course,
            )

            batch = Batch.objects.create(**validated_data)
            batch.faculties.set(faculties)
            return batch

    #  Update
    def update(self, instance, validated_data):
        faculties = validated_data.pop("faculties", None)

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
    course_title = serializers.CharField(source="course.title", read_only=True)
    batch_number = serializers.CharField(source="batch.batch_number", read_only=True)
    center_name = serializers.CharField(source="center.name", read_only=True)
    councellor_name = serializers.CharField(source="councellor.get_full_name", read_only=True)
    payment_installment_count = serializers.CharField(source="payment_type.total_installments", read_only=True)
    student_id = serializers.CharField(read_only=True)
    modules = serializers.ListField(
        child=serializers.ChoiceField(choices=ModulePermission.MODULE_CHOICES),
        write_only=True,
        required=False
    )

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
            modules = validated_data.pop("modules", [])

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
            user = profile.user   #  FIX: always define

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

    class Meta:
        model = CoursePayment
        fields = [
            "id",
            "student",
            "installments",
            "course_title",
            "installment_amount",
            "amount_paid",
            "payment_method",
            "transaction_id",
            "payment_date",
        ]
        read_only_fields = ["payment_date"]

    def validate(self, data):
        student = data["student"]
        installments = data["installments"]
        amount_paid = data["amount_paid"]
        payment_method = data["payment_method"]
        transaction_id = data.get("transaction_id")

        course = installments.plan.course
        enrollment = get_staff_course_enrollment(
            student,
            course,
            installment_plan=installments.plan,
        )

        # Student must be enrolled
        if not enrollment:
            raise serializers.ValidationError("Student not enrolled in this course.")

        # Transaction ID check
        if payment_method != "cash" and not transaction_id:
            raise serializers.ValidationError("Transaction ID required.")

        # Full payment check
        if amount_paid != installments.amount:
            raise serializers.ValidationError("Full payment required.")

        return data

    def create(self, validated_data):
        try:
            with transaction.atomic():
                return super().create(validated_data)
        except IntegrityError as exc:
            raise serializers.ValidationError(
                "This installment has already been paid."
            ) from exc

    def update(self, instance, validated_data):
        # Immutable financial records
        raise serializers.ValidationError(
            "Payments cannot be updated once created."
        )


class CourceInstallmentListSerializer(serializers.ModelSerializer):
    # installment_no = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    due_date = serializers.SerializerMethodField()
    paid_date = serializers.SerializerMethodField()
    payment_method = serializers.SerializerMethodField()

    class Meta:
        model = InstallmentItem
        fields = [
            "id",
            # "installment_no",
            "amount",
            "status",
            "due_date",
            "paid_date",
            "payment_method",
        ]

    #  Get payment ONLY for this staff
    def get_payment(self, obj):
        student = get_payment_student(self.context.get("student"))
        if not student:
            return None
        return obj.payments.filter(student=student).order_by("-payment_date").first()

    # #  Installment number (1,2,3…)
    # def get_installment_no(self, obj):
    #     ids = list(
    #         obj.course.installments
    #         .order_by("due_days_after_enrollment")
    #         .values_list("id", flat=True)
    #     )
    #     return f"#{ids.index(obj.id) + 1}"

    #  Paid / Pending (staff-specific)
    def get_status(self, obj):
        return "Paid" if self.get_payment(obj) else "Pending"

    #  Paid date
    def get_paid_date(self, obj):
        payment = self.get_payment(obj)
        return payment.payment_date if payment else None

    #  Payment method
    def get_payment_method(self, obj):
        payment = self.get_payment(obj)
        return payment.payment_method if payment else "-"

    #  Due date (based on staff enrollment)
    def get_due_date(self, obj):
        student = self.context.get("student")
        if not student:
            return None
        return get_installment_due_date_for_staff(student, obj)

class CoursePaymentDetailSerializer(serializers.ModelSerializer):
    student_full_name = serializers.SerializerMethodField()
    student_code = serializers.CharField(source="student.student_id", read_only=True)
    phone_number = serializers.CharField(source="student.profile.phone_number", read_only=True)
    email = serializers.CharField(source="student.profile.user.email", read_only=True)
    course_title = serializers.CharField(source="installments.plan.course.title", read_only=True)
    course_id = serializers.CharField(source="installments.plan.course.id", read_only=True)

    course_total_fee = serializers.CharField(source="installments.plan.course.total_fee", read_only=True)
    total_paid = serializers.SerializerMethodField()
    pending_fee = serializers.SerializerMethodField()
    next_due_date = serializers.SerializerMethodField()

    installment_list = CourceInstallmentListSerializer(
        many=True,
        source="installments.plan.items",
        read_only=True,
    )




    class Meta:
        model = CoursePayment
        fields = [
            "id",
            "student",
            "student_full_name",
            "student_code",
            "phone_number",
            "email",
            "course_title",
            "course_id",
            # "installment",

            "course_total_fee",
            "total_paid",
            "pending_fee",
            "next_due_date",

            "installment_list",
        ]

    def get_student_full_name(self, obj):
        user = obj.student.profile.user
        return f"{user.first_name} {user.last_name}"
    
    def get_total_paid(self, obj):
        course = obj.installments.plan.course
        total_paid = CoursePayment.objects.filter(
            student=obj.student,
            installments__plan__course=course
        ).aggregate(total=Sum("amount_paid"))["total"] or 0
        return total_paid

    def get_pending_fee(self, obj):
        course = obj.installments.plan.course
        total_paid = self.get_total_paid(obj)
        pending = course.total_fee - total_paid
        return pending
    
    def get_next_due_date(self, obj):
        course = obj.installments.plan.course
        plan = get_staff_installment_plan(
            obj.student,
            course,
            preferred_plan=obj.installments.plan,
        ) or obj.installments.plan
        next_installment = get_next_unpaid_installment_item(
            obj.student,
            course,
            preferred_plan=plan,
        )
        return get_installment_due_date_for_staff(obj.student, next_installment)
    
    def to_representation(self, instance):
        self.fields["installment_list"].context.update({
            "student": instance.student
        })
        return super().to_representation(instance)


