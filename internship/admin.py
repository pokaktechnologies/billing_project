from django.contrib import admin
from django.apps import apps
from import_export.admin import ImportExportModelAdmin

from .models.attendance import ClassAttendanceSession, StudentAttendanceRecord


class StudentAttendanceRecordInline(admin.TabularInline):
    model = StudentAttendanceRecord
    extra = 0
    fields = ('student', 'status', 'remarks')
    raw_id_fields = ('student',)


@admin.register(ClassAttendanceSession)
class ClassAttendanceSessionAdmin(ImportExportModelAdmin):
    list_display = ('id', 'section', 'faculty', 'date', 'topic_covered', 'created_at')
    list_filter = ('date', 'section', 'faculty')
    search_fields = (
        'section__class_obj__name',
        'section__batch__batch_number',
        'topic_covered',
        'faculty__user__user__first_name',
        'faculty__user__user__last_name',
    )
    date_hierarchy = 'date'
    raw_id_fields = ('section', 'faculty')
    inlines = [StudentAttendanceRecordInline]


@admin.register(StudentAttendanceRecord)
class StudentAttendanceRecordAdmin(ImportExportModelAdmin):
    list_display = ('id', 'session', 'student', 'status', 'remarks', 'created_at')
    list_filter = ('status', 'session__date', 'session__section')
    search_fields = (
        'student__student_id',
        'student__profile__user__first_name',
        'student__profile__user__last_name',
        'student__profile__user__email',
        'remarks',
    )
    raw_id_fields = ('session', 'student')


app_models = apps.get_app_config('internship').get_models()

for model in app_models:
    try:
        @admin.register(model)
        class GenericAdmin(ImportExportModelAdmin):
            pass
    except admin.sites.AlreadyRegistered:
        pass

