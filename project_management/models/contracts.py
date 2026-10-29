from datetime import date
from django.db import models
from accounts.models import CustomUser, Customer


class ClientContract(models.Model):
    contract_type = models.CharField(max_length=255, null=True, blank=True)
    contract_number = models.CharField(max_length=255, unique=True, null=True, blank=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    client = models.ForeignKey(Customer, on_delete=models.CASCADE)
    contract_name = models.CharField(max_length=255)
    description = models.TextField()
    contract_date = models.DateField(null=True, blank=True, default=date.today)
    start_date = models.DateField()
    end_date = models.DateField()
    duration = models.IntegerField(help_text="Duration in days", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.client} - {self.contract_name} ({self.user.id})"
