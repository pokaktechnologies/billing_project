import calendar
from datetime import date
from django.utils import timezone
from decimal import Decimal
from attendance.models import DailyAttendance
from .models import AttendanceSummary, Payroll, PayrollDeduction, PayrollEarning, PayrollPeriod
from accounts.models import StaffProfile
from django.db import transaction

PAID_LEAVE_LIMIT = 1

def generate_attendance_summary(staff, period):
    """
    Creates an AttendanceSummary snapshot for a staff for the given period.
    """
    try:
        year, month = map(int, period.month.split("-"))
    except ValueError:
        raise ValueError(f"Invalid month format in period ({period.month}).")

    records = DailyAttendance.objects.filter(
        staff=staff,
        date__year=year,
        date__month=month
    )

    working_days = records.count()
    full_days = records.filter(status="full_day").count()
    half_days = records.filter(status="half_day").count()
    leave_days = records.filter(status="leave").count()
    absent_days = records.filter(status="absent").count()

    # 3. Validate Breakdown
    if (full_days + half_days + leave_days + absent_days) != working_days:
        raise ValueError(f"Attendance mismatch for {staff.user.email}: {full_days}F, {half_days}H, {leave_days}L, {absent_days}A != {working_days} total")

    summary = AttendanceSummary.objects.create(
        staff=staff,
        period=period,
        month=period.month,
        working_days=working_days,
        full_days=full_days,
        half_days=half_days,
        leave_days=leave_days,
        absent_days=absent_days,
    )

    return summary

def create_payroll_record(summary, monthly_salary):
    """
    Calculates and saves a Payroll record based on the attendance summary,
    staff salary configuration, and additional earnings/deductions.
    """

    # -----------------------------------
    # 1. Attendance / Leave calculation
    # -----------------------------------

    paid_leave_used = min(
        summary.leave_days,
        PAID_LEAVE_LIMIT
    )

    unpaid_leave_count = Decimal(
        max(summary.leave_days - paid_leave_used, 0)
    )

    absent_unpaid_count = Decimal(
        summary.absent_days
    )

    half_day_unpaid_count = (
        Decimal(summary.half_days) * Decimal("0.5")
    )

    unpaid_days_total = (
        unpaid_leave_count
        + absent_unpaid_count
        + half_day_unpaid_count
    )

    # -----------------------------------
    # 2. Basic salary
    # -----------------------------------

    salary_decimal = Decimal(str(monthly_salary))

    # -----------------------------------
    # 3. Attendance deduction
    # -----------------------------------

    working_days_decimal = Decimal(
        summary.working_days
    )

    if working_days_decimal > 0:
        per_day_salary = (
            salary_decimal / working_days_decimal
        )
    else:
        per_day_salary = Decimal("0")

    attendance_deduction = (
        unpaid_days_total * per_day_salary
    ).quantize(Decimal("0.01"))

    # -----------------------------------
    # 4. Staff additional earnings
    # -----------------------------------

    staff_earnings = summary.staff.job_detail.earnings.filter(
        is_active=True
    )

    additional_earnings_total = sum(
        (
            Decimal(str(earning.amount))
            for earning in staff_earnings
        ),
        Decimal("0")
    )

    # -----------------------------------
    # 5. Gross salary
    # -----------------------------------

    gross_salary = (
        salary_decimal
        + additional_earnings_total
    ).quantize(Decimal("0.01"))

    # -----------------------------------
    # 6. Staff additional deductions
    # -----------------------------------

    staff_deductions = summary.staff.job_detail.deductions.filter(
        is_active=True
    )

    additional_deductions_total = sum(
        (
            Decimal(str(deduction.amount))
            for deduction in staff_deductions
        ),
        Decimal("0")
    )

    # -----------------------------------
    # 7. Total deductions
    # -----------------------------------

    total_deduction = (
        attendance_deduction
        + additional_deductions_total
    ).quantize(Decimal("0.01"))

    # -----------------------------------
    # 8. Net salary
    # -----------------------------------

    net_salary = (
        gross_salary - total_deduction
    ).quantize(Decimal("0.01"))

    net_salary = max(
        net_salary,
        Decimal("0")
    )

    # -----------------------------------
    # 9. Create Payroll
    # -----------------------------------

    payroll = Payroll.objects.create(
        staff=summary.staff,
        period=summary.period,
        month=summary.month,
        gross_salary=gross_salary,
        working_days=summary.working_days,
        paid_leave_used=paid_leave_used,
        unpaid_leave_days=unpaid_days_total,
        deduction=total_deduction,
        net_salary=net_salary,
        status="Draft"
    )

    # -----------------------------------
    # 10. Create Basic Salary earning
    # -----------------------------------

    PayrollEarning.objects.create(
        payroll=payroll,
        earning_type="Basic Salary",
        amount=salary_decimal
    )

    # -----------------------------------
    # 11. Copy Staff Earnings
    # -----------------------------------

    PayrollEarning.objects.bulk_create([
        PayrollEarning(
            payroll=payroll,
            earning_type=earning.earning_type,
            amount=earning.amount
        )
        for earning in staff_earnings
    ])

    # -----------------------------------
    # 12. Create Attendance Deduction
    # -----------------------------------

    if attendance_deduction > 0:
        PayrollDeduction.objects.create(
            payroll=payroll,
            deduction_type="Attendance Deduction",
            amount=attendance_deduction
        )

    # -----------------------------------
    # 13. Copy Staff Deductions
    # -----------------------------------

    PayrollDeduction.objects.bulk_create([
        PayrollDeduction(
            payroll=payroll,
            deduction_type=deduction.deduction_type,
            amount=deduction.amount
        )
        for deduction in staff_deductions
    ])

    return payroll

def process_payroll_for_month(target_month, current_date=None):
    """
    Handles the payroll generation step.
    Input: target_month (YYYY-MM), current_date (default now)
    """
    if current_date is None:
        current_date = timezone.localdate()
    
    try:
        year, month = map(int, target_month.split("-"))
    except ValueError:
        return {"success": False, "error": "Invalid target_month format. Use YYYY-MM."}

    # 1. Validate Month Eligibility
    last_day = calendar.monthrange(year, month)[1]
    month_end_date = date(year, month, last_day)
    
    if current_date <= month_end_date:
        return {"success": False, "error": "Payroll cannot be generated before month ends."}

    # 2. Validate Status
    period, created = PayrollPeriod.objects.get_or_create(month=target_month)
    if period.status != "open":
        return {"success": False, "error": "Payroll already generated or locked."}

    # Create Attendance Summary Snapshot and Payroll Records for each active staff
    active_staff = StaffProfile.objects.filter(job_detail__status='active')
    
    if not active_staff.exists():
        return {"success": False, "error": "No active staff found for payroll generation."}

    try:
        for staff in active_staff:
            # Skip if already exists for this period
            if AttendanceSummary.objects.filter(staff=staff, period=period).exists():
                continue
            
            if not hasattr(staff, 'job_detail'):
                continue

            # 3. Create Attendance Summary Snapshot
            summary = generate_attendance_summary(staff, period)
            
            # 4. Generate Payroll Records
            create_payroll_record(summary, staff.job_detail.salary)
            generated_count += 1
            
        # 5. Update PayrollMonth
        period.status = "generated"
        period.generated_at = timezone.now()
        period.save()
        
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": f"Error during payroll generation: {str(e)}"}


def process_bulk_staff_payroll(staff_ids, period_id, current_date=None):
    """
    Handles bulk payroll generation for a list of staff IDs using a PayrollPeriod ID.
    """
    if current_date is None:
        current_date = timezone.localdate()
    
    try:
        period = PayrollPeriod.objects.get(id=period_id)
    except PayrollPeriod.DoesNotExist:
        return {"success": False, "error": "Invalid PayrollPeriod ID."}

    target_month = period.month
    try:
        year, month = map(int, target_month.split("-"))
    except ValueError:
        return {"success": False, "error": f"Invalid month format in PayrollPeriod ({target_month})."}

    # 1. Validate Month Eligibility
    last_day = calendar.monthrange(year, month)[1]
    month_end_date = date(year, month, last_day)
    
    if current_date <= month_end_date:
        return {"success": False, "error": "Payroll cannot be generated before month ends."}

    # 2. Validate Status
    if period.status == "locked":
        return {"success": False, "error": "Payroll month is locked."}

    results = []
    skipped = []
    
    try:
        with transaction.atomic():
            staff_profiles = StaffProfile.objects.filter(id__in=staff_ids)
            found_ids = set(staff_profiles.values_list('id', flat=True))
            not_found_ids = set(staff_ids) - found_ids
            
            active_staff_profiles = staff_profiles.filter(job_detail__status='active')
            inactive_ids = set(staff_profiles.exclude(job_detail__status='active').values_list('id', flat=True))

            for staff in active_staff_profiles:
                # Check if already exists for this period
                if AttendanceSummary.objects.filter(staff=staff, period=period).exists():
                    skipped.append({"staff_id": staff.id, "email": staff.user.email, "reason": "Attendance summary already exists for this period."})
                    continue
                if Payroll.objects.filter(staff=staff, period=period).exists():
                    skipped.append({"staff_id": staff.id, "email": staff.user.email, "reason": "Payroll record already exists for this period."})
                    continue
                
                if not hasattr(staff, 'job_detail'):
                    skipped.append({"staff_id": staff.id, "email": staff.user.email, "reason": "No job detail found for staff."})
                    continue

                try:
                    # 3. Create Attendance Summary Snapshot
                    summary = generate_attendance_summary(staff, period)
                    
                    # 4. Generate Payroll Records
                    payroll = create_payroll_record(summary, staff.job_detail.salary)
                    
                    results.append(payroll)
                except ValueError as e:
                    raise ValueError(f"Error processing staff {staff.user.email}: {str(e)}")
            
            # Populate other categories
            for sid in inactive_ids:
                staff = staff_profiles.get(id=sid)
                skipped.append({"staff_id": sid, "email": staff.user.email, "reason": "Staff is not active."})
            
            not_found = [{"staff_id": sid, "reason": "Staff ID not found."} for sid in not_found_ids]

            # 5. Update PayrollMonth status (if not already GENERATED or LOCKED)
            if period.status == "open" and results:
                period.status = "generated"
                period.generated_at = timezone.now()
                period.save()
        
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": f"Error during bulk payroll generation: {str(e)}"}

    return {
        "success": True, 
        "message": f"Processed {len(results)} staff members, skipped {len(skipped)}.", 
        "results": results,
        "skipped": skipped,
        "not_found": not_found
    }

def reset_staff_payroll(staff_id, period_id):
    """
    Deletes Payroll and AttendanceSummary records for a specific staff and period.
    Only allowed if the period is not Locked.
    """
    try:
        period = PayrollPeriod.objects.get(id=period_id)
    except PayrollPeriod.DoesNotExist:
        return {"success": False, "error": "Invalid PayrollPeriod ID."}

    if period.status == "locked":
        return {"success": False, "error": "Cannot reset payroll for a locked period."}

    try:
        with transaction.atomic():
            # Delete Payroll records
            payroll_deleted, _ = Payroll.objects.filter(staff_id=staff_id, period=period).delete()
            
            # Delete AttendanceSummary records
            summary_deleted, _ = AttendanceSummary.objects.filter(staff_id=staff_id, period=period).delete()

            if payroll_deleted == 0 and summary_deleted == 0:
                return {"success": False, "error": "No payroll or attendance records found for this staff and period."}

            return {
                "success": True,
                "message": f"Successfully reset payroll for staff ID {staff_id} in period {period.month}."
            }
    except Exception as e:
        return {"success": False, "error": f"Error during payroll reset: {str(e)}"}

def bulk_mark_payroll_as_paid(payroll_ids):
    """
    Marks multiple payroll records as 'Paid'.
    Only records in 'Draft' status and associated with a 'Locked' period are updated.
    """
    try:
        with transaction.atomic():
            payrolls = Payroll.objects.select_for_update().filter(id__in=payroll_ids)
            
            found_ids = set(payrolls.values_list('id', flat=True))
            not_found_ids = set(payroll_ids) - found_ids
            
            # Filter for Draft status AND Locked period
            updatable_payrolls = payrolls.filter(status='Draft', period__status='locked')
            
            # Identify reasons for skipping
            already_paid_ids = set(payrolls.filter(status='Paid').values_list('id', flat=True))
            unlocked_period_payrolls = payrolls.filter(status='Draft').exclude(period__status='locked')
            unlocked_period_ids = set(unlocked_period_payrolls.values_list('id', flat=True))
            
            updated_count = updatable_payrolls.update(status='Paid')
            
            # Prepare summary and details
            total_processed = len(payroll_ids)
            skipped_count = len(already_paid_ids) + len(unlocked_period_ids)
            
            results = {
                "success": True,
                "message": f"Successfully processed {total_processed} payroll records. {updated_count} updated, {skipped_count} skipped.",
                "summary": {
                    "updated": updated_count,
                    "already_paid": len(already_paid_ids),
                    "skipped_unlocked_period": len(unlocked_period_ids),
                    "not_found": len(not_found_ids)
                },
                "details": {
                    "already_paid_ids": list(already_paid_ids),
                    "unlocked_period_ids": list(unlocked_period_ids),
                    "not_found_ids": list(not_found_ids)
                }
            }
            
            if updated_count == 0:
                if not_found_ids and not already_paid_ids and not unlocked_period_ids:
                    results["success"] = False
                    results["error"] = "None of the provided payroll IDs were found."
                    results["message"] = "No payroll records were found."
                elif unlocked_period_ids and not already_paid_ids:
                    results["message"] = f"Processed {total_processed} records. None were updated because their periods are not locked."
                else:
                    results["message"] = f"Processed {total_processed} records. No updatable records found (already paid or unlocked periods)."
            
            return results
            
    except Exception as e:
        return {"success": False, "error": f"Error during bulk mark as paid: {str(e)}"}
