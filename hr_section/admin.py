from django.contrib import admin
from django.apps import apps


models = apps.get_app_config('hr_section').get_models()

for model in models:
    # Define a function to create a custom admin class per model
    def get_admin_class(model):
        class CustomAdmin(admin.ModelAdmin):
            list_display = ('id', 'display_str')



            def display_str(self, obj):
                return str(obj)
            display_str.short_description = 'Description'

        return CustomAdmin

    admin.site.register(model, get_admin_class(model))
