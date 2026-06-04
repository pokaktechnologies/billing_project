import datetime
from django.utils import timezone
from attendance.models import AttendanceSession, DailyAttendance

target_date = datetime.date(2026, 6, 4)
logout_time_local = datetime.datetime.combine(target_date, datetime.time(15, 0, 0))

aware_logout_time = timezone.make_aware(logout_time_local, timezone.get_current_timezone())

sessions_to_update = AttendanceSession.objects.filter(
    daily_attendance__date=target_date,
    session='session2',
    login_time__isnull=False,
    logout_time__isnull=True 
)

print(f"Found {sessions_to_update.count()} sessions to update.")

for session in sessions_to_update:
    session.logout_time = aware_logout_time
    
    if session.status == 'leave' and session.login_time:
        local_login_time = timezone.localtime(session.login_time)
        if local_login_time.time() <= datetime.time(12, 15, 0):
            session.status = 'present'
        else:
            session.status = 'late'
            
    session.save()
    print(f"Updated session2 logout for: {session.daily_attendance.staff.user.email} (Session Status: {session.status})")

daily_records = DailyAttendance.objects.filter(date=target_date)
for daily_attendance in daily_records:
    sessions = daily_attendance.sessions.all()
    if sessions.exists():
        total_hours = sum(s.session_duration() for s in sessions)
        daily_attendance.total_working_hours = total_hours

        if total_hours >= 7:
            daily_attendance.status = "full_day"
        elif total_hours >= 4:
            daily_attendance.status = "half_day"
        else:
            daily_attendance.status = "leave"

        daily_attendance.save()
        print(f"Updated DailyAttendance for {daily_attendance.staff.user.email}: Hours={total_hours:.2f}, Status={daily_attendance.status}")