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
            
        elif job == 'status':
            self.stdout.write("--- Scheduler Configuration Status ---")
            from core.scheduler import start
            # We can't easily access the running server's scheduler instance, 
            # but we can show what IS configured to run.
            self.stdout.write("Listing configured jobs:")
            self.stdout.write("- Daily Attendance: 08:00 AM (Asia/Kolkata)")
            self.stdout.write("- Session 1 Logout: 12:00 PM (Asia/Kolkata)")
            self.stdout.write("- Session 2 Logout: 03:00 PM (Asia/Kolkata)")
            self.stdout.write("- Session 3 Logout: 06:00 PM (Asia/Kolkata)")
            self.stdout.write("- Monthly Payroll: Day 1, 00:00 AM")
            self.stdout.write("\nTo confirm if the LIVE scheduler is currently running, check the log file:")
            self.stdout.write(self.style.NOTICE("Get-Content scheduler.log -Tail 10"))

        else:
            self.stdout.write("Running all standard jobs (Attendance)...")
            create_daily_attendance_records()
            self.stdout.write(self.style.SUCCESS("Jobs triggered."))
