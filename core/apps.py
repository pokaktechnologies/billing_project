from django.apps import AppConfig
import os

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        # Only start the scheduler if we're not in the main thread (avoids double execution in dev server)
        # OR just check for RUN_MAIN environment variable which Django sets for the reloader
        if os.environ.get('RUN_MAIN') == 'true':
            from . import scheduler
            scheduler.start()
