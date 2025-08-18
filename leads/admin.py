from django.contrib import admin
from django.apps import apps


apps_model = apps.get_app_config('leads').get_models()
for model in apps_model:
    admin.site.register(model)