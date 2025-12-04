from django.contrib import admin
from django.apps import apps
from import_export.admin import ImportExportModelAdmin

app_models = apps.get_app_config('internship').get_models()

for model in app_models:
    try:
        @admin.register(model)
        class GenericAdmin(ImportExportModelAdmin):
            pass
    except admin.sites.AlreadyRegistered:
        pass
