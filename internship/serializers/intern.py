from rest_framework import serializers
from ..models import Class, Section, StudyMaterial, TaskAttachment, TaskSubmission, TaskAssignment, Task, TaskSubmissionAttachment
from ..utils import get_authenticated_student, get_student_task_assignment
from datetime import date

# from django.utils import timezone

# from django.db.models import Sum



class TaskAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskAssignment
        fields = "__all__"

class TaskAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskAttachment
        fields = ["id", "file", "uploaded_at"]
        read_only_fields = ["id", "uploaded_at"]

class InternTaskSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    assignment_details = serializers.SerializerMethodField()
    task_attachment = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            "id",
            "title",
            "description",
            "start_date",
            "due_date",
            "course",
            "status",
            "assignment_details",
            "task_attachment",
        ]

    def _get_assignment(self, obj):
        request = self.context.get("request")
        student = get_authenticated_student(getattr(request, "user", None))
        return get_student_task_assignment(obj, student)

    def get_status(self, obj):
        assignment = self._get_assignment(obj)
        return assignment.status if assignment else None

    def get_assignment_details(self, obj):
        assignment = self._get_assignment(obj)
        if not assignment:
            return []

        return TaskAssignmentSerializer(assignment).data
    
    def get_task_attachment(self, obj):
        attachments = obj.attachments.all()
        return TaskAttachmentSerializer(attachments, many=True).data



class TaskSubmissionAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskSubmissionAttachment
        fields = ["id", "file", "uploaded_at"]
        read_only_fields = ["id", "uploaded_at"]


class TaskSubmissionSerializer(serializers.ModelSerializer):
    attachments = TaskSubmissionAttachmentSerializer(many=True, read_only=True)
    task_attachment = serializers.SerializerMethodField(read_only=True)
    task_id = serializers.IntegerField(source='assignment.task.id', read_only=True)

    title = serializers.CharField(source='assignment.task.title', read_only=True)
    description = serializers.CharField(source='assignment.task.description', read_only=True)
    status = serializers.CharField(source='assignment.status', read_only=True)
    student_name = serializers.SerializerMethodField(read_only=True)
    staff = serializers.SerializerMethodField(read_only=True)
    due_date = serializers.DateField(source='assignment.task.due_date', read_only=True)

    # accept multiple files on create
    files = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = TaskSubmission
        fields = [
            "id",
            "assignment",
            "submitted_at",
            "link",
            "response",
            "instructor_feedback",
            "reviewed_at",
            "attachments",
            "files",
            "task_id",

            "title",
            "description",
            "task_attachment",
            "status",
            "student_name",
            "staff",
            "due_date",
        ]
        read_only_fields = ["submitted_at", "instructor_feedback", "reviewed_at"]

    def _get_assignee_name(self, assignment):
        student = assignment.student
        if student and student.profile and student.profile.user:
            user = student.profile.user
            return f"{user.first_name} {user.last_name}".strip()

        staff = assignment.staff
        if staff and staff.user:
            return f"{staff.user.first_name} {staff.user.last_name}".strip()

        return None

    def get_student_name(self, obj):
        return self._get_assignee_name(obj.assignment)

    def get_staff(self, obj):
        # Backward-compatible alias for older clients.
        return self._get_assignee_name(obj.assignment)
    
    def get_task_attachment(self, obj):
        attachments = obj.assignment.task.attachments.all()
        return TaskAttachmentSerializer(attachments, many=True).data

    def validate(self, data):
        assignment = data.get("assignment") or self.instance.assignment
        request = self.context.get("request")
        student = get_authenticated_student(getattr(request, "user", None))

        if not student:
            raise serializers.ValidationError("User has no student profile.")

        if assignment.student_id != student.id:
            raise serializers.ValidationError(
                "You are not assigned to this task."
            )

        task = assignment.task
        due = task.due_date
        revision = assignment.revision_due_date

        effective_deadline = (
            revision if (revision and revision > due) else due
        )

        # deadline check
        if date.today() > effective_deadline:
            raise serializers.ValidationError(
                "Deadline passed. You cannot create or modify."
            )

        # CREATE
        if self.instance is None:
            if assignment.status not in ["pending", "revision_required"]:
                raise serializers.ValidationError(
                    "You cannot create new submission now."
                )

        # UPDATE
        else:
            # only allowed while submitted
            if assignment.status != "submitted":
                raise serializers.ValidationError(
                    "You can only update when status is submitted."
                )

        return data
    def create(self, validated_data):
        files = validated_data.pop("files", [])
        submission = TaskSubmission.objects.create(**validated_data)

        # save all attachments
        for f in files:
            TaskSubmissionAttachment.objects.create(
                submission=submission,
                file=f
            )

        # update assignment status to 'submitted'
        assignment = submission.assignment
        assignment.status = 'submitted'
        assignment.save()
        return submission

    def update(self, instance, validated_data):
        files = validated_data.pop("files", [])
        
        # normal update fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # handle new attachments
        for f in files:
            TaskSubmissionAttachment.objects.create(
                submission=instance,
                file=f
            )

        return instance
    

## DASHABOARD --------------

class InternTaskMiniSerializer(serializers.ModelSerializer):
    status = serializers.CharField(source="latest_status")
    course = serializers.CharField(source="course.title")
    attachment = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            "id",
            "title",
            "description",
            "start_date",
            "due_date",
            "course",
            "status",
            "attachment",
        ]

    def get_attachment(self, obj):
        attachments = obj.attachments.all()
        return TaskAttachmentSerializer(attachments, many=True).data



class StudyMaterialMiniSerializer(serializers.ModelSerializer):
    course = serializers.CharField(source="course.title")

    class Meta:
        model = StudyMaterial
        fields = ["id", "title","course", "material_type", "file", "url"]


class InternSectionSerializer(serializers.ModelSerializer):
    batch_number = serializers.CharField(source="batch.batch_number", read_only=True)
    course = serializers.IntegerField(source="batch.course_id", read_only=True)
    course_title = serializers.CharField(source="batch.course.title", read_only=True)
    days = serializers.SerializerMethodField()
    duration_minutes = serializers.SerializerMethodField()

    class Meta:
        model = Section
        fields = [
            "id",
            "batch",
            "batch_number",
            "course",
            "course_title",
            "start_time",
            "end_time",
            "days",
            "duration_minutes",
        ]

    def get_days(self, obj):
        day_order = {
            "mon": 1,
            "tue": 2,
            "wed": 3,
            "thu": 4,
            "fri": 5,
            "sat": 6,
            "sun": 7,
        }
        return sorted(
            [day.day for day in obj.days.all()],
            key=lambda day: day_order.get(day, 99),
        )

    def get_duration_minutes(self, obj):
        from datetime import date, datetime

        start = datetime.combine(date.today(), obj.start_time)
        end = datetime.combine(date.today(), obj.end_time)
        diff = int((end - start).total_seconds() / 60)
        hours, mins = divmod(diff, 60)
        return f"{hours} hr {mins} min" if mins else f"{hours} hr"


class InternClassSectionSerializer(serializers.ModelSerializer):
    center_name = serializers.CharField(source="center.name", read_only=True)
    sections = serializers.SerializerMethodField()

    class Meta:
        model = Class
        fields = [
            "id",
            "name",
            "center",
            "center_name",
            "sections",
        ]

    def get_sections(self, obj):
        sections = getattr(obj, "student_sections", obj.sections.all())
        return InternSectionSerializer(
            sections,
            many=True,
            context=self.context,
        ).data




# serializers.py

from rest_framework import serializers
from ..models import (
    Test, TestSection, TestQuestion, QuestionOption,
    TestAttempt, TestAnswer
)


# ─── Student Test List ────────────────────────────────────────────
class StudentTestListSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)
    batch_number = serializers.CharField(source='batch.batch_number', read_only=True)
    total_questions = serializers.SerializerMethodField()
    attempt_status = serializers.SerializerMethodField()

    class Meta:
        model = Test
        fields = [
            'id', 'name', 'test_type', 'course_title', 'batch_number',
            'duration_minutes', 'total_marks', 'total_questions',
            'status', 'attempt_status'
        ]

    def get_total_questions(self, obj):
        return TestQuestion.objects.filter(section__test=obj).count()

    def get_attempt_status(self, obj):
        student = self.context.get('student')
        attempt = obj.attempts.filter(student=student).first()
        if not attempt:
            return 'not_attempted'
        return attempt.status  # in_progress / submitted


# ─── Test Detail (Before Start) ───────────────────────────────────
class StudentSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestSection
        fields = ['id', 'name', 'section_type', 'marks', 'duration_minutes', 'order']


class StudentTestDetailSerializer(serializers.ModelSerializer):
    sections = StudentSectionSerializer(many=True, read_only=True)
    total_questions = serializers.SerializerMethodField()
    attempt_id = serializers.SerializerMethodField()
    attempt_status = serializers.SerializerMethodField()

    class Meta:
        model = Test
        fields = [
            'id', 'name', 'test_type', 'duration_minutes',
            'total_marks', 'total_questions', 'instructions',
            'sections', 'attempt_id', 'attempt_status'
        ]

    def get_total_questions(self, obj):
        return TestQuestion.objects.filter(section__test=obj).count()

    def get_attempt_id(self, obj):
        student = self.context.get('student')
        attempt = obj.attempts.filter(student=student).first()
        return attempt.id if attempt else None

    def get_attempt_status(self, obj):
        student = self.context.get('student')
        attempt = obj.attempts.filter(student=student).first()
        if not attempt:
            return 'not_attempted'
        return attempt.status


# ─── Test Taking — Questions ──────────────────────────────────────
class StudentOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionOption
        fields = ['id', 'label', 'option_text']
        # is_correct — test taking-ൽ hide cheyyുക


class StudentQuestionSerializer(serializers.ModelSerializer):
    options = StudentOptionSerializer(many=True, read_only=True)
    saved_answer = serializers.SerializerMethodField()

    class Meta:
        model = TestQuestion
        fields = [
            'id', 'question_text', 'marks', 'file',
            'order', 'word_limit', 'manual_evaluation',
            'options', 'saved_answer'
        ]

    def get_saved_answer(self, obj):
        attempt = self.context.get('attempt')
        if not attempt:
            return None
        answer = obj.answers.filter(attempt=attempt).first()
        if not answer:
            return None
        return {
            'selected_option': answer.selected_option_id,
            'text_answer': answer.text_answer,
            'is_marked_for_review': answer.is_marked_for_review,
        }


class StudentSectionWithQuestionsSerializer(serializers.ModelSerializer):
    questions = StudentQuestionSerializer(many=True, read_only=True)

    class Meta:
        model = TestSection
        fields = ['id', 'name', 'section_type', 'marks', 'order', 'questions']


# ─── Answer Save ──────────────────────────────────────────────────
class TestAnswerSaveSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    selected_option = serializers.IntegerField(required=False, allow_null=True)
    text_answer = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    is_marked_for_review = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        question_id = attrs.get('question_id')
        attempt = self.context.get('attempt')

        # Question ee test-nte underil aano
        try:
            question = TestQuestion.objects.get(
                id=question_id,
                section__test=attempt.test
            )
        except TestQuestion.DoesNotExist:
            raise serializers.ValidationError({
                "question_id": "Invalid question for this test."
            })

        # MCQ — selected_option validate
        section_type = question.section.section_type
        if section_type == 'mcq':
            selected_option = attrs.get('selected_option')
            if selected_option:
                if not QuestionOption.objects.filter(
                    id=selected_option, question=question
                ).exists():
                    raise serializers.ValidationError({
                        "selected_option": "Invalid option for this question."
                    })

        attrs['question'] = question
        return attrs


# ─── Submit ───────────────────────────────────────────────────────
class TestSubmitSerializer(serializers.Serializer):
    time_taken_seconds = serializers.IntegerField()


# ─── Result ───────────────────────────────────────────────────────
class ResultAnswerSerializer(serializers.ModelSerializer):
    question_text = serializers.CharField(source='question.question_text')
    section_name = serializers.CharField(source='question.section.name')
    section_type = serializers.CharField(source='question.section.section_type')
    correct_option = serializers.SerializerMethodField()
    selected_option_label = serializers.SerializerMethodField()
    max_marks = serializers.IntegerField(source='question.marks')
    is_correct = serializers.SerializerMethodField()

    class Meta:
        model = TestAnswer
        fields = [
            'id', 'question_text', 'section_name', 'section_type',
            'selected_option', 'selected_option_label',
            'correct_option', 'text_answer',
            'max_marks', 'marks_awarded', 'feedback',
            'is_marked_for_review', 'is_correct'
        ]

    def get_correct_option(self, obj):
        if obj.question.section.section_type == 'mcq':
            correct = obj.question.options.filter(is_correct=True).first()
            if correct:
                return {'id': correct.id, 'label': correct.label}
        return None

    def get_selected_option_label(self, obj):
        if obj.selected_option:
            return obj.selected_option.label
        return None

    def get_is_correct(self, obj):
        if obj.question.section.section_type != 'mcq':
            return None  # descriptive — manual evaluation
        if not obj.selected_option:
            return False
        return obj.selected_option.is_correct


class SectionResultSerializer(serializers.ModelSerializer):
    total_marks = serializers.IntegerField(source='marks')
    scored_marks = serializers.SerializerMethodField()
    correct_count = serializers.SerializerMethodField()
    wrong_count = serializers.SerializerMethodField()

    class Meta:
        model = TestSection
        fields = [
            'id', 'name', 'section_type',
            'total_marks', 'scored_marks',
            'correct_count', 'wrong_count'
        ]

    def get_scored_marks(self, obj):
        attempt = self.context.get('attempt')
        if obj.section_type == 'mcq':
            total = 0
            for q in obj.questions.all():
                answer = q.answers.filter(attempt=attempt).first()
                if answer and answer.selected_option and answer.selected_option.is_correct:
                    total += q.marks or 0
            return total
        else:
            # Descriptive — marks_awarded sum
            total = 0
            for q in obj.questions.all():
                answer = q.answers.filter(attempt=attempt).first()
                if answer and answer.marks_awarded:
                    total += answer.marks_awarded
            return total

    def get_correct_count(self, obj):
        if obj.section_type != 'mcq':
            return None
        attempt = self.context.get('attempt')
        count = 0
        for q in obj.questions.all():
            answer = q.answers.filter(attempt=attempt).first()
            if answer and answer.selected_option and answer.selected_option.is_correct:
                count += 1
        return count

    def get_wrong_count(self, obj):
        if obj.section_type != 'mcq':
            return None
        attempt = self.context.get('attempt')
        count = 0
        for q in obj.questions.all():
            answer = q.answers.filter(attempt=attempt).first()
            if answer and answer.selected_option and not answer.selected_option.is_correct:
                count += 1
        return count


class TestResultSerializer(serializers.ModelSerializer):
    test_name = serializers.CharField(source='test.name')
    total_marks = serializers.IntegerField(source='test.total_marks')
    scored_marks = serializers.SerializerMethodField()
    percentage = serializers.SerializerMethodField()
    section_breakdown = serializers.SerializerMethodField()
    answers = serializers.SerializerMethodField()

    class Meta:
        model = TestAttempt
        fields = [
            'id', 'test_name', 'total_marks', 'scored_marks',
            'percentage', 'time_taken_seconds',
            'started_at', 'submitted_at',
            'section_breakdown', 'answers'
        ]

    def get_scored_marks(self, obj):
        total = 0
        for answer in obj.answers.select_related(
            'question', 'selected_option', 'question__section'
        ).all():
            if answer.question.section.section_type == 'mcq':
                if answer.selected_option and answer.selected_option.is_correct:
                    total += answer.question.marks or 0
            else:
                total += answer.marks_awarded or 0
        return total

    def get_percentage(self, obj):
        scored = self.get_scored_marks(obj)
        total = obj.test.total_marks
        if total == 0:
            return 0
        return round((scored / total) * 100, 2)

    def get_section_breakdown(self, obj):
        sections = obj.test.sections.prefetch_related('questions__answers', 'questions__options').all()
        return SectionResultSerializer(
            sections, many=True, context={'attempt': obj}
        ).data

    def get_answers(self, obj):
        answers = obj.answers.select_related(
            'question', 'question__section',
            'selected_option'
        ).prefetch_related('question__options').order_by(
            'question__section__order', 'question__order'
        )
        return ResultAnswerSerializer(answers, many=True).data