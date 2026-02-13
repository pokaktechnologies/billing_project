import logging
from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger('scheduler')

def start():
    """
    Centralized hub to start all background jobs across all apps.
    This is called via core/apps.py during Django startup.
    """
    scheduler = BackgroundScheduler(timezone="Asia/Kolkata")

    # --- Attendance App Jobs ---
    from attendance.scheduler import (
        create_daily_attendance_records,
        auto_logout_job,
        pre_session_notification
    )
    
    # Daily attendance creation
    scheduler.add_job(create_daily_attendance_records, "cron", hour=8, minute=0)

    # Auto-logout jobs for sessions
    scheduler.add_job(auto_logout_job, "cron", hour=12, minute=0, args=["session1"])
    scheduler.add_job(auto_logout_job, "cron", hour=15, minute=0, args=["session2"])
    scheduler.add_job(auto_logout_job, "cron", hour=18, minute=0, args=["session3"])

    # Pre-session notifications
    scheduler.add_job(pre_session_notification, "cron", hour=11, minute=50, args=["session1"])
    scheduler.add_job(pre_session_notification, "cron", hour=14, minute=50, args=["session2"])
    scheduler.add_job(pre_session_notification, "cron", hour=17, minute=50, args=["session3"])


    # --- Payroll App Jobs ---
    from payroll.scheduler import create_monthly_payroll_period
    
    # Monthly PayrollPeriod creation
    scheduler.add_job(create_monthly_payroll_period, "cron", day=1, hour=0, minute=0)


    # --- Start the Engine ---
    scheduler.start()
    logger.info("⏱ Central Scheduler started successfully with all app jobs.")
