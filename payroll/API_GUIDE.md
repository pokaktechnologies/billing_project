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

### List Salary Statements

Returns a list of salary statements for a specific employee with advanced duration and range filtering.

- **URL**: `/salary-statement/<int:staff_id>/`
- **Method**: `GET`
- **Filtering Options**:
  - `duration` (string): Predefined periods (`1m`, `3m`, `6m`, `9m`, `12m`).
  - `start_month` (string): Start of range in `YYYY-MM` format.
  - `end_month` (string): End of range in `YYYY-MM` format.
  - Supports standard `PayrollFilter` parameters (status, etc.).
- **Isolation**: Strictly returns records only for the `staff_id` specified in the URL.

---

## 6. Automation & Scheduling

The payroll system integrates with the project's central scheduler (`core/scheduler.py`).

- **Auto-Month Creation**: On the **1st of every month at 00:00**, a new `PayrollPeriod` is automatically created with status `OPEN`.
- **Status Progression**:
  - `OPEN`: Period created, ready for payroll generation.
  - `GENERATED`: Payroll records have been created for some or all staff.
  - `LOCKED`: Payroll verified and final; no further modifications possible.
