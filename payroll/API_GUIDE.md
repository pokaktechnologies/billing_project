# Payroll API Documentation

This guide documents the API endpoints available in the **Payroll** module.

**Base URL**: `/payroll/`

---

## 1. Payroll Periods

### List Payroll Periods

Returns a list of all payroll periods (months) and their current status.

- **URL**: `/periods/`
- **Method**: `GET`

### Retrieve Payroll Period Detail

Returns detailed information for a specific payroll period.

- **URL**: `/periods/<int:pk>/`
- **Method**: `GET`

---

## 2. Payroll Generation

### Bulk Staff Payroll Generation

Generates attendance snapshots and payroll records for one or more staff members in a single atomic transaction.

- **URL**: `/generate-bulk/`
- **Method**: `POST`
- **Payload Parameters**:
  - `staff_ids` (List[int]): Array of staff IDs to process.
  - `period_id` (int): The primary key of the `PayrollPeriod`.

---

## 3. Payroll Management

### Reset Staff Payroll

Deletes the payroll and attendance records for a specific staff member in a given period. Only allowed if the period is **not locked**.

- **URL**: `/reset-staff/`
- **Method**: `POST`
- **Payload Parameters**:
  - `staff_id` (int): The ID of the staff member.
  - `period_id` (int): The ID of the `PayrollPeriod`.
  - `generate_now` (bool, optional): If `true`, immediately regenerates payroll and attendance records after reset. Default is `false`.
- **Response (200 OK)**:
  - Default (`generate_now: false`):
    ```json
    {
      "success": true,
      "message": "Successfully reset payroll for staff ID 5 in period 2026-01."
    }
    ```
  - Regeneration (`generate_now: true`):
    ```json
    {
      "reset": {
        "success": true,
        "message": "Successfully reset payroll for staff ID 5 in period 2026-01."
      },
      "generation": {
        "success": true,
        "message": "Processed 1 staff members, skipped 0.",
        "results": [...],
        "skipped": [],
        "not_found": []
      }
    }
    ```

---

## 4. Payroll Records

### List Payroll Records

Returns a list of all payroll records. Supports extensive filtering, searching, and ordering.

- **URL**: `/`
- **Method**: `GET`
- **Filtering Options**:
  - `staff` (int): Filter by Staff ID.
  - `employee_id` (string): Search by Employee ID (partial match).
  - `staff_email` (string): Search by Staff Email (partial match).
  - `staff_name` (string): Search by Staff Name (partial match).
  - `department` (int): Filter by Department ID.
  - `job_type` (string): Filter by Job Type (`full_day`, `part_time`, etc.).
  - `period` (int): Filter by PayrollPeriod ID.
  - `period_month` (string): Exact match for month (e.g., `2026-01`).
  - `status` (string): Exact match for status (`DRAFT`, `PAID`).
  - `start_date` / `end_date` (YYYY-MM-DD): Filter by creation date range.
  - `min_salary` / `max_salary` (decimal): Filter by net salary range.
- **Searching**: Use `?search=<term>` to search across name, email, and employee ID.
- **Ordering**: Use `?ordering=<field>` (e.g., `-created_at`). Supported fields: `gross_salary`, `net_salary`, `created_at`, `working_days`.

### List My Payroll Records (Personal)

Returns a list of payroll records belonging ONLY to the logged-in staff member.

- **URL**: `/me/`
- **Method**: `GET`
- **Filtering Options**: Supports the same options as the main list (excluding staff ID filtering).
- **Security**: Automatically restricted to the user's data based on their authentication token.

### Retrieve Payroll Detail

Returns full details for a specific payroll record.

- **URL**: `/<int:pk>/`
- **Method**: `GET`

---

## 5. Reports & Payslips

### Retrieve Employee Payslip

Returns a comprehensive, single-month payslip for a specific employee. Includes staff details, attendance breakdown, and financial summary.

- **URL**: `/payslip/`
- **Method**: `GET`
- **Query Parameters**:
  - `staff_id` (int, Required): The ID of the staff member.
  - `period_id` (int, Optional): The ID of the `PayrollPeriod`.
  - `month` (string, Optional): Month in `YYYY-MM` format (Use if `period_id` is not known).
- **Note**: Either `period_id` or `month` is required.

### List All Staff Salary Statements (One-Line)

Returns one-line salary statements across all staff members. By default (`view=summary`), returns one aggregated summary row per staff member across the filtered periods along with overall totals; pass `?view=flat` for one flat row per `(staff, period)` payroll record.

- **URL**: `/salary-statement/`
- **Method**: `GET`
- **View Modes**:
  - `view=summary` (default): 1 aggregated row per staff across all matching periods.
  - `view=flat`: 1 flat row per `(staff, period)` payroll record.
- **Filtering Options**:
  - `year` (string): 4-digit year (e.g., `2026`).
  - `month` (string): Month number (`3` or `03`) or `YYYY-MM` (`2026-03`). Combines with `year` when numeric (`?year=2026&month=3`).
  - `period_month` (string): Exact `YYYY-MM` match (e.g., `2026-03`).
  - `start_month` / `end_month` (string): Inclusive `YYYY-MM` range.
  - `start_date` / `end_date` (YYYY-MM-DD): Inclusive date range mapped to payroll period months (`YYYY-MM`).
  - `duration` (string): Predefined rolling windows (`1m`, `3m`, `6m`, `9m`, `12m`, `all`). Explicit period filters take precedence when combined.
  - `status` (string): `paid`, `draft`, or `all` (case-insensitive; default returns all).
  - `sort_by` / `sort` (string): `newest` (default), `oldest`, `highest` (`highest_salary`/`salary_high`), `lowest` (`lowest_salary`/`salary_low`).
  - `ordering` (string): Custom field ordering (e.g., `net_salary`, `-gross_salary`, `working_days`, `staff_name`).
  - Standard `PayrollFilter` options: `staff`, `period`, `department`, `job_type`, `staff_name`, `staff_email`, `employee_id`, `min_salary`, `max_salary`, and `?search=<term>`.
  - Pagination: `?page=<n>&page_size=<m>` (or `size=<m>`) via `OptionalPagination`; omit for all records at once.
- **Sample Response (`GET /payroll/salary-statement/?year=2026&status=all&sort_by=highest`)**:
  ```json
  {
    "view": "summary",
    "filters": {
      "year": "2026",
      "month": null,
      "period_month": null,
      "start_month": null,
      "end_month": null,
      "start_date": null,
      "end_date": null,
      "duration": null,
      "status": "all",
      "sort_by": "highest"
    },
    "summary": {
      "total_staff": 2,
      "total_records": 4,
      "total_gross_salary": "220000.00",
      "total_deduction": "4000.00",
      "total_net_salary": "216000.00"
    },
    "count": 2,
    "results": [
      {
        "staff_id": 5,
        "employee_id": "EMP005",
        "staff_name": "John Doe",
        "email": "john@example.com",
        "phone_number": "9876543210",
        "department": "Engineering",
        "role": "Developer",
        "job_type": "full_day",
        "period": "2026-01 to 2026-02",
        "months_count": 2,
        "payroll_id": null,
        "status": "Paid",
        "paid_months": 2,
        "draft_months": 0,
        "working_days": 44,
        "total_working_hours": "352.00",
        "paid_leave_used": 1,
        "unpaid_leave_days": "0.00",
        "gross_salary": "120000.00",
        "deduction": "1000.00",
        "net_salary": "119000.00",
        "full_days": 43,
        "half_days": 0,
        "leave_days": 1,
        "absent_days": 0,
        "latest_created_at": "2026-03-01T10:00:00+05:30"
      }
    ]
  }
  ```

### List Salary Statements (Single Staff)

Returns a list of salary statements for a specific employee with year/month, duration, date range, status, and sort preset filtering.

- **URL**: `/salary-statement/<int:staff_id>/`
- **Method**: `GET`
- **Filtering Options**:
  - `year` (string): 4-digit year (e.g., `2026`).
  - `month` (string): Month number (`3` or `03`) or `YYYY-MM`.
  - `duration` (string): Predefined periods (`1m`, `3m`, `6m`, `9m`, `12m`, `all`).
  - `start_month` / `end_month` (string): Range in `YYYY-MM` format.
  - `start_date` / `end_date` (YYYY-MM-DD): Period-month range filter.
  - `status` (string): `paid`, `draft`, or `all` (case-insensitive).
  - `sort_by` / `sort` (string): `newest` (default), `oldest`, `highest`, `lowest`.
  - Supports standard `PayrollFilter` parameters (`min_salary`, `max_salary`, `ordering`, etc.).
- **Isolation**: Strictly returns records only for the `staff_id` specified in the URL.

---

## 6. Automation & Scheduling

The payroll system integrates with the project's central scheduler (`core/scheduler.py`).

- **Auto-Month Creation**: On the **1st of every month at 00:00**, a new `PayrollPeriod` is automatically created with status `OPEN`.
- **Status Progression**:
  - `OPEN`: Period created, ready for payroll generation.
  - `GENERATED`: Payroll records have been created for some or all staff.
  - `LOCKED`: Payroll verified and final; no further modifications possible.
