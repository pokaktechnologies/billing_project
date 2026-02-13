import logging
from django.core.management.base import BaseCommand
from attendance.scheduler import create_daily_attendance_records, auto_logout_job
from payroll.scheduler import create_monthly_payroll_period

logger = logging.getLogger('scheduler')

class Command(BaseCommand):
    help = 'Manually trigger scheduler jobs'

    def add_arguments(self, parser):
        parser.add_argument(
            '--job',
            type=str,
            help='Specific job to run (attendance, logout, payroll)',
        )
        parser.add_argument(
            '--session',
            type=str,
            default='session1',
            help='Session name for logout job (session1, session2, session3)',
        )

    def handle(self, *args, **options):
        job = options.get('job')
        session = options.get('session')

        if job == 'attendance':
            self.stdout.write("Triggering daily attendance creation...")
            create_daily_attendance_records()
            self.stdout.write(self.style.SUCCESS("Daily attendance job triggered."))
        
        elif job == 'logout':
            self.stdout.write(f"Triggering auto logout for {session}...")
            auto_logout_job(session)
            self.stdout.write(self.style.SUCCESS(f"Auto logout job for {session} triggered."))
            
        elif job == 'payroll':
            self.stdout.write("Triggering monthly payroll period creation...")
            create_monthly_payroll_period()
            self.stdout.write(self.style.SUCCESS("Payroll job triggered."))
            
        else:
            self.stdout.write("Running all standard jobs (Attendance)...")
            create_daily_attendance_records()
            self.stdout.write(self.style.SUCCESS("Jobs triggered."))
