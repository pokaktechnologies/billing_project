# attendance/scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


def create_daily_attendance_records():
    """Create daily attendance and 3 sessions for all staff with default leave status."""
    from django.utils import timezone
    from accounts.models import StaffProfile
    from attendance.models import DailyAttendance, AttendanceSession

    today = timezone.localdate()
    print(f"⏰ Creating daily attendance for {today}")

    # Define session times (customize as needed)
    session_times = {
        "session1": ("09:00:00", "12:00:00"),
        "session2": ("12:00:00", "15:00:00"),
        "session3": ("16:00:00", "18:00:00"),
    }

    staffs = StaffProfile.objects.all()
    created_count = 0

    for staff in staffs:
        # Avoid creating duplicate record
        daily_attendance, created = DailyAttendance.objects.get_or_create(
            staff=staff,
            date=today,
            defaults={"status": "leave", "total_working_hours": 0.0}
        )

        if created:
            created_count += 1
            # Create 3 sessions for this staff
            for session_name, (start, end) in session_times.items():
                AttendanceSession.objects.create(
                    daily_attendance=daily_attendance,
                    session=session_name,
                    status="leave",
                )

    if created_count:
        print(f"✅ Created daily attendance records for {created_count} staff members.")
    else:
        print("ℹ️ Daily attendance records already exist for all staff today.")


def send_group_notification(message: str):
    """Send a notification message to all connected staff via Channels."""
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "attendance_notifications",
        {
            "type": "send_notification",
            "message": message
        }
    )


def pre_session_notification(session_name: str):
    """Notify all users 10 minutes before session ends."""
    from django.utils import timezone
    from attendance.models import DailyAttendance, AttendanceSession

    now = timezone.localtime()
    today = now.date()
    session_labels = {
        "session1": "Morning (9:00 AM - 12:00 PM)",
        "session2": "Afternoon (12:00 PM - 3:00 PM)",
        "session3": "Evening (4:00 PM - 6:00 PM)",
    }
    friendly_session = session_labels.get(session_name, session_name)
    message = f"⏳ Reminder: {friendly_session} will end in 10 minutes."

    # Send notification to all staff
    send_group_notification(message)
    print(f"📢 Pre-session notification sent for {session_name} at {now}")


def auto_logout_job(session_name: str):
    """Logs out all users, updates session attendance, and notifies session end."""
    from django.utils import timezone
    from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
    from django.db.utils import OperationalError
    from accounts.models import CustomUser
    from attendance.models import DailyAttendance, AttendanceSession

    now = timezone.localtime()
    today = now.date()
    print(f"⏰ Auto logout job running at {now} for {session_name}")

    # 1️⃣ Blacklist all outstanding tokens
    try:
        tokens = OutstandingToken.objects.all()
        for t in tokens:
            BlacklistedToken.objects.get_or_create(token=t)
        print(f"✅ Blacklisted {len(tokens)} outstanding tokens, logged out all users.")

        # Record logout time for all users
        CustomUser.objects.filter(is_active=True).update(force_logout_time=now)
    except OperationalError:
        print("⚠️ Database not ready yet, skipping this run.")
        return

    # 2️⃣ Update attendance session records
    sessions = AttendanceSession.objects.filter(
        daily_attendance__date=today,
        session=session_name
    )

    for session in sessions:
        if session.login_time is None:
            session.status = "leave"  # never logged in
        else:
            if session.logout_time is None:
                session.logout_time = now
            session.status = "present"
        session.save()
        print(f"{session.daily_attendance.staff.user.email} | login: {session.login_time} | logout: {session.logout_time}")

    # 3️⃣ Update main daily attendance
    daily_records = DailyAttendance.objects.filter(date=today)
    for daily_attendance in daily_records:
        sessions = daily_attendance.sessions.all()
        if sessions.exists():
            total_hours = sum(s.session_duration() for s in sessions)
            daily_attendance.total_working_hours = total_hours

            # Determine status based on total working hours
            if 7 <= total_hours <= 9:
                daily_attendance.status = "full_day"
            elif 4 <= total_hours < 7:
                daily_attendance.status = "half_day"
            else:
                daily_attendance.status = "leave"

            daily_attendance.save()
            print(f"{daily_attendance.staff.user.email} | Total Hours: {total_hours:.2f} | Status: {daily_attendance.status}")

    # 4️⃣ Send session-end notification
    session_labels = {
        "session1": "Morning (9:00 AM - 12:00 PM)",
        "session2": "Afternoon (12:00 PM - 3:00 PM)",
        "session3": "Evening (4:00 PM - 6:00 PM)",
    }
    friendly_session = session_labels.get(session_name, session_name)
    message = f"✅ {friendly_session} has ended. Your session attendance is recorded."
    send_group_notification(message)


def start():
    """Start the scheduler with fixed cron jobs."""
    scheduler = BackgroundScheduler(timezone="Asia/Kolkata")

    # Schedule daily attendance creation
    scheduler.add_job(create_daily_attendance_records, "cron", hour=7, minute=0)  # before first session

    # Schedule auto-logout jobs for each session
    scheduler.add_job(auto_logout_job, "cron", hour=12, minute=0, args=["session1"])
    scheduler.add_job(auto_logout_job, "cron", hour=15, minute=0, args=["session2"])
    scheduler.add_job(auto_logout_job, "cron", hour=18, minute=0, args=["session3"])

    # Schedule pre-session 10-min notifications
    scheduler.add_job(pre_session_notification, "cron", hour=11, minute=50, args=["session1"])
    scheduler.add_job(pre_session_notification, "cron", hour=14, minute=50, args=["session2"])
    scheduler.add_job(pre_session_notification, "cron", hour=17, minute=50, args=["session3"])


    scheduler.start()
    print("⏱ Scheduler started successfully.")
