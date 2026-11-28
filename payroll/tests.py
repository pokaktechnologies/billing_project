from datetime import date, datetime
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import CustomUser, Department, JobDetail, StaffProfile
from payroll.models import AttendanceSummary, Payroll, PayrollPeriod


class SalaryStatementAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.all_url = reverse('salary-statement-all')

        self.dept_eng = Department.objects.create(name='Engineering')
        self.dept_hr = Department.objects.create(name='HR')

        self.user_alice = CustomUser.objects.create_user(
            first_name='Alice',
            last_name='Smith',
            email='alice@example.com',
            password='password123',
        )
        self.staff_alice = StaffProfile.objects.create(
            user=self.user_alice,
            phone_number='9990001111',
        )
        JobDetail.objects.create(
            staff=self.staff_alice,
            employee_id='EMP001',
            department=self.dept_eng,
            job_type='full_day',
            role='Senior Developer',
            salary=Decimal('50000.00'),
            start_date=date(2025, 1, 1),
            status='active',
        )

        self.user_bob = CustomUser.objects.create_user(
            first_name='Bob',
            last_name='Jones',
            email='bob@example.com',
            password='password123',
        )
        self.staff_bob = StaffProfile.objects.create(
            user=self.user_bob,
            phone_number='9990002222',
        )
        JobDetail.objects.create(
            staff=self.staff_bob,
            employee_id='EMP002',
            department=self.dept_hr,
            job_type='part_time',
            role='HR Specialist',
            salary=Decimal('30000.00'),
            start_date=date(2025, 1, 1),
            status='active',
        )

        # Staff without JobDetail or AttendanceSummary to ensure null safety
        self.user_nojob = CustomUser.objects.create_user(
            first_name='Charlie',
            last_name='NoJob',
            email='charlie@example.com',
            password='password123',
        )
        self.staff_nojob = StaffProfile.objects.create(
            user=self.user_nojob,
            phone_number=None,
        )

        self.p_2025_03 = PayrollPeriod.objects.create(month='2025-03', status='locked')
        self.p_2026_01 = PayrollPeriod.objects.create(month='2026-01', status='locked')
        self.p_2026_02 = PayrollPeriod.objects.create(month='2026-02', status='locked')
        self.p_2026_03 = PayrollPeriod.objects.create(month='2026-03', status='generated')

        # Alice records: 2025-03 (Paid), 2026-01 (Paid), 2026-02 (Paid), 2026-03 (Draft)
        self.pay_alice_25_03 = self._create_payroll(
            self.staff_alice,
            self.p_2025_03,
            gross='45000.00',
            deduction='1000.00',
            net='44000.00',
            status_val='Paid',
            working_days=20,
            hours='160.00',
            paid_leave=1,
            unpaid_leave='0.00',
            att=(20, 18, 1, 1, 0),
        )
        self.pay_alice_26_01 = self._create_payroll(
            self.staff_alice,
            self.p_2026_01,
            gross='50000.00',
            deduction='2000.00',
            net='48000.00',
            status_val='Paid',
            working_days=22,
            hours='176.00',
            paid_leave=1,
            unpaid_leave='0.50',
            att=(22, 20, 1, 1, 0),
        )
        self.pay_alice_26_02 = self._create_payroll(
            self.staff_alice,
            self.p_2026_02,
            gross='50000.00',
            deduction='0.00',
            net='50000.00',
            status_val='Paid',
            working_days=20,
            hours='160.00',
            paid_leave=0,
            unpaid_leave='0.00',
            att=(20, 20, 0, 0, 0),
        )
        self.pay_alice_26_03 = self._create_payroll(
            self.staff_alice,
            self.p_2026_03,
            gross='50000.00',
            deduction='5000.00',
            net='45000.00',
            status_val='Draft',
            working_days=22,
            hours='168.00',
            paid_leave=1,
            unpaid_leave='1.00',
            att=(22, 20, 0, 1, 1),
        )

        # Bob records: 2026-01 (Paid), 2026-03 (Paid)
        self.pay_bob_26_01 = self._create_payroll(
            self.staff_bob,
            self.p_2026_01,
            gross='30000.00',
            deduction='1000.00',
            net='29000.00',
            status_val='Paid',
            working_days=22,
            hours='110.00',
            paid_leave=0,
            unpaid_leave='0.00',
            att=(22, 22, 0, 0, 0),
        )
        self.pay_bob_26_03 = self._create_payroll(
            self.staff_bob,
            self.p_2026_03,
            gross='30000.00',
            deduction='3000.00',
            net='27000.00',
            status_val='Paid',
            working_days=22,
            hours='100.00',
            paid_leave=1,
            unpaid_leave='1.00',
            att=(22, 19, 1, 1, 1),
        )

        # Charlie (no job_detail, no AttendanceSummary) in 2026-02 (Draft)
        self.pay_nojob_26_02 = self._create_payroll(
            self.staff_nojob,
            self.p_2026_02,
            gross='15000.00',
            deduction='500.00',
            net='14500.00',
            status_val='Draft',
            working_days=20,
            hours='80.00',
            paid_leave=0,
            unpaid_leave='0.00',
            att=None,
        )

        # Set explicit created_at values in a later month (2026-05) for 2026-01/02 records
        # so tests prove start_date/end_date filter by payroll period month, not created_at.
        later_dt = timezone.make_aware(datetime(2026, 5, 10, 12, 0, 0))
        earlier_dt = timezone.make_aware(datetime(2026, 4, 2, 12, 0, 0))
        Payroll.objects.filter(
            id__in=[self.pay_alice_26_01.id, self.pay_alice_26_02.id, self.pay_bob_26_01.id]
        ).update(created_at=later_dt)
        Payroll.objects.filter(
            id__in=[self.pay_alice_26_03.id, self.pay_bob_26_03.id, self.pay_nojob_26_02.id]
        ).update(created_at=earlier_dt)

    def _create_payroll(
        self,
        staff,
        period,
        gross,
        deduction,
        net,
        status_val,
        working_days,
        hours,
        paid_leave,
        unpaid_leave,
        att,
    ):
        if att is not None:
            AttendanceSummary.objects.create(
                staff=staff,
                period=period,
                month=period.month,
                working_days=att[0],
                full_days=att[1],
                half_days=att[2],
                leave_days=att[3],
                absent_days=att[4],
            )
        return Payroll.objects.create(
            staff=staff,
            period=period,
            month=period.month,
            gross_salary=Decimal(gross),
            working_days=working_days,
            total_working_hours=Decimal(hours),
            paid_leave_used=paid_leave,
            unpaid_leave_days=Decimal(unpaid_leave),
            deduction=Decimal(deduction),
            net_salary=Decimal(net),
            status=status_val,
        )

    def test_all_staff_summary_default_and_totals(self):
        response = self.client.get(self.all_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(data['view'], 'summary')
        self.assertEqual(data['count'], 3)
        self.assertEqual(data['summary']['total_staff'], 3)
        self.assertEqual(data['summary']['total_records'], 7)
        self.assertEqual(data['summary']['total_gross_salary'], '270000.00')
        self.assertEqual(data['summary']['total_deduction'], '12500.00')
        self.assertEqual(data['summary']['total_net_salary'], '257500.00')

        by_staff = {row['staff_id']: row for row in data['results']}
        alice_row = by_staff[self.staff_alice.id]
        self.assertEqual(alice_row['months_count'], 4)
        self.assertIsNone(alice_row['payroll_id'])
        self.assertEqual(alice_row['status'], 'Partial')
        self.assertEqual(alice_row['paid_months'], 3)
        self.assertEqual(alice_row['draft_months'], 1)
        self.assertEqual(Decimal(alice_row['net_salary']), Decimal('187000.00'))
        self.assertEqual(alice_row['full_days'], 78)
        self.assertEqual(alice_row['period'], '2025-03 to 2026-03')

        charlie_row = by_staff[self.staff_nojob.id]
        self.assertIsNone(charlie_row['employee_id'])
        self.assertIsNone(charlie_row['department'])
        self.assertEqual(charlie_row['payroll_id'], self.pay_nojob_26_02.id)
        self.assertEqual(charlie_row['status'], 'Draft')
        self.assertEqual(charlie_row['full_days'], 0)

    def test_year_and_month_filters(self):
        # Full year 2026
        resp_year = self.client.get(self.all_url, {'year': '2026'})
        self.assertEqual(resp_year.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_year.data['summary']['total_records'], 6)
        by_staff = {row['staff_id']: row for row in resp_year.data['results']}
        self.assertEqual(Decimal(by_staff[self.staff_alice.id]['net_salary']), Decimal('143000.00'))

        # year + numeric month (single digit)
        resp_ym = self.client.get(self.all_url, {'year': '2026', 'month': '3'})
        self.assertEqual(resp_ym.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_ym.data['count'], 2)
        for row in resp_ym.data['results']:
            self.assertEqual(row['period'], '2026-03')
            self.assertIsNotNone(row['payroll_id'])

        # Direct YYYY-MM in month
        resp_full_m = self.client.get(self.all_url, {'month': '2026-03'})
        self.assertEqual(resp_full_m.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_full_m.data['count'], 2)

        # Month only across years (03 matches 2025-03 and 2026-03)
        resp_m_only = self.client.get(self.all_url, {'month': '03'})
        self.assertEqual(resp_m_only.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_m_only.data['summary']['total_records'], 3)

    def test_start_end_month_and_date_range_filter_period_month(self):
        resp_months = self.client.get(
            self.all_url, {'start_month': '2026-01', 'end_month': '2026-02'}
        )
        self.assertEqual(resp_months.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_months.data['summary']['total_records'], 4)

        # created_at on 2026-01/02 rows is 2026-05-10, so this confirms period-month matching
        resp_dates = self.client.get(
            self.all_url, {'start_date': '2026-01-01', 'end_date': '2026-02-28'}
        )
        self.assertEqual(resp_dates.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_dates.data['summary']['total_records'], 4)
        self.assertEqual(resp_dates.data['summary']['total_net_salary'], '141500.00')

    @patch('payroll.filters.timezone.localdate', return_value=date(2026, 4, 15))
    def test_duration_and_precedence(self, _mock_localdate):
        # 3m from 2026-04 -> >= 2026-01 (excludes 2025-03)
        resp_3m = self.client.get(self.all_url, {'duration': '3m'})
        self.assertEqual(resp_3m.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_3m.data['summary']['total_records'], 6)

        # duration=all returns everything including 2025-03
        resp_all = self.client.get(self.all_url, {'duration': 'all'})
        self.assertEqual(resp_all.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_all.data['summary']['total_records'], 7)

        # Explicit year takes precedence over duration=3m
        resp_override = self.client.get(self.all_url, {'duration': '3m', 'year': '2025'})
        self.assertEqual(resp_override.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_override.data['summary']['total_records'], 1)

    def test_status_filters_case_insensitive(self):
        resp_paid = self.client.get(self.all_url, {'year': '2026', 'status': 'paid'})
        self.assertEqual(resp_paid.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_paid.data['count'], 2)
        by_staff = {row['staff_id']: row for row in resp_paid.data['results']}
        self.assertEqual(Decimal(by_staff[self.staff_alice.id]['net_salary']), Decimal('98000.00'))
        self.assertEqual(by_staff[self.staff_alice.id]['full_days'], 40)
        self.assertEqual(by_staff[self.staff_alice.id]['status'], 'Paid')

        resp_draft = self.client.get(self.all_url, {'year': '2026', 'status': 'DRAFT'})
        self.assertEqual(resp_draft.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_draft.data['count'], 2)
        for row in resp_draft.data['results']:
            self.assertEqual(row['status'], 'Draft')

        resp_all = self.client.get(self.all_url, {'year': '2026', 'status': 'all'})
        self.assertEqual(resp_all.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_all.data['count'], 3)

    def test_sort_presets_in_summary_and_flat_modes(self):
        resp_high = self.client.get(self.all_url, {'year': '2026', 'sort_by': 'highest'})
        self.assertEqual(resp_high.status_code, status.HTTP_200_OK)
        ids_high = [row['staff_id'] for row in resp_high.data['results']]
        self.assertEqual(ids_high, [self.staff_alice.id, self.staff_bob.id, self.staff_nojob.id])

        resp_low = self.client.get(self.all_url, {'year': '2026', 'sort': 'lowest'})
        self.assertEqual(resp_low.status_code, status.HTTP_200_OK)
        ids_low = [row['staff_id'] for row in resp_low.data['results']]
        self.assertEqual(ids_low, [self.staff_nojob.id, self.staff_bob.id, self.staff_alice.id])

        resp_old = self.client.get(self.all_url, {'sort_by': 'oldest'})
        self.assertEqual(resp_old.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_old.data['results'][0]['staff_id'], self.staff_alice.id)

        # Flat mode
        resp_flat_new = self.client.get(
            self.all_url, {'view': 'flat', 'year': '2026', 'sort_by': 'newest'}
        )
        self.assertEqual(resp_flat_new.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_flat_new.data['view'], 'flat')
        self.assertEqual(resp_flat_new.data['count'], 6)
        self.assertEqual(resp_flat_new.data['results'][0]['period_month'], '2026-03')

        resp_flat_high = self.client.get(
            self.all_url, {'view': 'flat', 'year': '2026', 'sort_by': 'highest'}
        )
        nets = [Decimal(row['net_salary']) for row in resp_flat_high.data['results']]
        self.assertEqual(nets, sorted(nets, reverse=True))

        # Flat row without job_detail and AttendanceSummary stays null-safe
        nojob_flat = [
            row for row in resp_flat_high.data['results'] if row['staff_id'] == self.staff_nojob.id
        ][0]
        self.assertIsNone(nojob_flat['employee_id'])
        self.assertIsNone(nojob_flat['department'])
        self.assertIsNone(nojob_flat['full_days'])

    def test_staff_name_search_department_and_pagination(self):
        resp_name = self.client.get(self.all_url, {'staff_name': 'Alice'})
        self.assertEqual(resp_name.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_name.data['count'], 1)
        self.assertEqual(resp_name.data['results'][0]['staff_id'], self.staff_alice.id)

        resp_dept = self.client.get(self.all_url, {'department': self.dept_hr.id})
        self.assertEqual(resp_dept.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_dept.data['count'], 1)
        self.assertEqual(resp_dept.data['results'][0]['staff_id'], self.staff_bob.id)

        resp_search = self.client.get(self.all_url, {'search': 'EMP002'})
        self.assertEqual(resp_search.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_search.data['count'], 1)

        resp_page = self.client.get(
            self.all_url, {'year': '2026', 'sort_by': 'highest', 'page': 1, 'page_size': 1}
        )
        self.assertEqual(resp_page.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_page.data['count'], 3)
        self.assertEqual(len(resp_page.data['results']), 1)
        self.assertEqual(resp_page.data['results'][0]['staff_id'], self.staff_alice.id)
        # Summary reflects full filtered set even when paginated
        self.assertEqual(resp_page.data['summary']['total_staff'], 3)
        self.assertEqual(resp_page.data['summary']['total_net_salary'], '213500.00')

    def test_single_staff_endpoint_backwards_compat_and_filters(self):
        single_url = reverse('salary-statement', kwargs={'staff_id': self.staff_alice.id})

        resp = self.client.get(single_url, {'year': '2026', 'status': 'paid', 'sort_by': 'highest'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIsInstance(resp.data, list)
        self.assertEqual(len(resp.data), 2)
        self.assertEqual(resp.data[0]['period_month'], '2026-02')
        self.assertEqual(resp.data[0]['net_salary'], '50000.00')
        self.assertEqual(resp.data[0]['attendance_summary']['full_days'], 20)
        self.assertEqual(resp.data[1]['period_month'], '2026-01')
