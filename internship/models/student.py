from django.db import models
from accounts.models import SalesPerson, StaffProfile
from .academic import Center

class Student(models.Model):
    profile  = models.OneToOneField(StaffProfile, on_delete=models.CASCADE, related_name="student_profile")
    student_id = models.CharField(max_length=20, unique=True)
    center = models.ForeignKey(Center, on_delete=models.SET_NULL, null=True, blank=True, related_name="students")
    course = models.ForeignKey('Course', on_delete=models.SET_NULL, null=True, blank=True, related_name="students") # Unused
    batch = models.ForeignKey('Batch', on_delete=models.SET_NULL, null=True, blank=True, related_name="students") # Unused
    payment_type = models.ForeignKey('InstallmentPlan', on_delete=models.SET_NULL, null=True, blank=True, related_name="students") # Unused
    start_date = models.DateField()
    slot_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    STATUS_CHOICES = [
    ('active', 'Active'),
    ('completed', 'Completed'),
    ('inactive', 'Inactive'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    councellor = models.ForeignKey(SalesPerson, on_delete=models.SET_NULL, null=True, blank=True, related_name="counselled_students")
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def get_full_name(self):
        user = self.profile.user
        return f"{user.first_name} {user.last_name}"
    
    def __str__(self):
        return f"{self.profile.user.first_name} {self.profile.user.last_name} {self.profile.user.email} - {self.student_id}"
