from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from accounts.models import StaffProfile

User = get_user_model()

class AttendanceStatsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='password',
            first_name='Test',
            last_name='User'
        )
        self.client.force_authenticate(user=self.user)
        self.staff = StaffProfile.objects.create(user=self.user)

    def test_staff_wise_stats_no_job_detail(self):
        url = reverse('staff-wise-attendance-stats')
        response = self.client.get(f"{url}?staff={self.staff.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]['department'], None)

    def test_all_staff_wise_stats_staff_filtering(self):
        url = reverse('all-staff-wise-attendance-stats')
        response = self.client.get(f"{url}?staff={self.staff.id}")
        self.assertEqual(response.status_code, 200)
        # Verify only our test staff is returned
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['staff_id'], self.staff.id)
