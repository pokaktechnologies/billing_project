from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .models import Account

class AccountFilterTests(APITestCase):
    def setUp(self):
        # Create Level 1 types (conceptual, not in DB usually but for tests we rely on what Account model allows)
        # Note: Account model enforces depth and regex.
        # Let's create strict valid accounts.
        
        # 1. Asset Type (Level 1) - actually Level 1 is conceptual, but let's see how models.py handles it.
        # Model says: Level 1 is Type (10000). Level 2 is Parent (1.1000).
        # We need to create valid accounts.
        
        # Level 2 (Root)
        self.root_asset = Account.objects.create(
            name="Current Assets",
            type="asset",
            account_number="1.1000",
            is_posting=False,
            status="active",
            opening_balance=0
        )
        
        self.root_sales = Account.objects.create(
            name="Sales Income",
            type="sales",
            account_number="4.1000",
            is_posting=False,
            status="active",
            opening_balance=0
        )
        
        # Level 3 (Child)
        self.child_cash = Account.objects.create(
            name="Cash in Hand",
            type="asset",
            parent_account=self.root_asset,
            account_number="1.1001",
            is_posting=True,
            status="active",
            opening_balance=1000
        )
        
        self.child_bank = Account.objects.create(
            name="Bank Account",
            type="asset",
            parent_account=self.root_asset,
            account_number="1.1002",
            is_posting=True,
            status="inactive",
            opening_balance=5000
        )

        self.url = '/finance/account/' # Correct URL based on urls.py

    def test_filter_parent_only(self):
        """Test ?parent_only=true returns only root accounts (no parent)"""
        response = self.client.get(self.url, {'parent_only': 'true'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results'] if 'results' in response.data else response.data
        
        ids = [item['id'] for item in results]
        self.assertIn(self.root_asset.id, ids)
        self.assertIn(self.root_sales.id, ids)
        self.assertNotIn(self.child_cash.id, ids)
        self.assertNotIn(self.child_bank.id, ids)

    def test_filter_by_parent(self):
        """Test ?parent=ID returns only children of that parent"""
        response = self.client.get(self.url, {'parent': self.root_asset.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results'] if 'results' in response.data else response.data
        
        ids = [item['id'] for item in results]
        self.assertNotIn(self.root_asset.id, ids)
        self.assertIn(self.child_cash.id, ids)
        self.assertIn(self.child_bank.id, ids)
        # Should not see sales root
        self.assertNotIn(self.root_sales.id, ids)

    def test_filter_is_posting(self):
        """Test ?is_posting=true/false"""
        # True
        response = self.client.get(self.url, {'is_posting': 'true'})
        results = response.data['results'] if 'results' in response.data else response.data
        ids = [item['id'] for item in results]
        self.assertIn(self.child_cash.id, ids)
        self.assertNotIn(self.root_asset.id, ids)
        
        # False
        response = self.client.get(self.url, {'is_posting': 'false'})
        results = response.data['results'] if 'results' in response.data else response.data
        ids = [item['id'] for item in results]
        self.assertIn(self.root_asset.id, ids)
        self.assertNotIn(self.child_cash.id, ids)

    def test_filter_type(self):
        """Test ?type=sales"""
        response = self.client.get(self.url, {'type': 'sales'})
        results = response.data['results'] if 'results' in response.data else response.data
        ids = [item['id'] for item in results]
        self.assertIn(self.root_sales.id, ids)
        self.assertNotIn(self.root_asset.id, ids)

    def test_filter_status(self):
        """Test ?status=inactive"""
        response = self.client.get(self.url, {'status': 'inactive'})
        results = response.data['results'] if 'results' in response.data else response.data
        ids = [item['id'] for item in results]
        self.assertIn(self.child_bank.id, ids)
        self.assertNotIn(self.child_cash.id, ids)

    def test_search_name(self):
        """Test ?search=Cash"""
        response = self.client.get(self.url, {'search': 'Cash'})
        results = response.data['results'] if 'results' in response.data else response.data
        ids = [item['id'] for item in results]
        self.assertIn(self.child_cash.id, ids)
        self.assertNotIn(self.child_bank.id, ids)

    def test_search_account_number(self):
        """Test ?search=1.1002"""
        response = self.client.get(self.url, {'search': '1.1002'})
        results = response.data['results'] if 'results' in response.data else response.data
        ids = [item['id'] for item in results]
        self.assertIn(self.child_bank.id, ids)

    def test_filter_created_at(self):
        """Test created_at__before and created_at__after"""
        # All accounts created now. Let's filter slightly in future/past.
        # This is tricky since auto_now_add=True.
        # We can just check that parameters don't error and maybe filter everything out with a past date.
        
        from django.utils import timezone
        import datetime
        
        tomorrow = (timezone.now() + datetime.timedelta(days=1)).date()
        yesterday = (timezone.now() - datetime.timedelta(days=1)).date()
        
        # Filter before yesterday -> Should be empty
        response = self.client.get(self.url, {'created_at__before': yesterday})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results'] if 'results' in response.data else response.data
        self.assertEqual(len(results), 0)
        
        # Filter after yesterday -> Should include our accounts
        response = self.client.get(self.url, {'created_at__after': yesterday})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results'] if 'results' in response.data else response.data
        self.assertTrue(len(results) > 0)
