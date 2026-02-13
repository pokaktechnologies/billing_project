from django.apps import AppConfig
import os

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        import sys
        # 1. In local dev (runserver), Django starts two processes. 
        #    We only start the scheduler in the reloader process (RUN_MAIN=true).
        # 2. In production (Daphne/Gunicorn), RUN_MAIN is not set. We start it there.
        # 3. We avoid starting during maintenance commands (migrate, etc.)
        
        run_main = os.environ.get('RUN_MAIN') == 'true'
        is_manage_command = any(arg in sys.argv for arg in ['makemigrations', 'migrate', 'collectstatic', 'trigger_scheduler', 'test', 'shell'])

        if run_main or (not os.environ.get('RUN_MAIN') and not is_manage_command):
            from . import scheduler
            scheduler.start()
