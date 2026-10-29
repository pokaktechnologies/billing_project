
# import uuid

# from django.conf import settings
# from django.db import models


# class BugReport(models.Model):

#     SEVERITY_CHOICES = [
#         ('critical', 'Critical'),
#         ('major', 'Major'),
#         ('minor', 'Minor'),
#         ('trivial', 'Trivial'),
#     ]

#     STATUS_CHOICES = [
#         ('suggestion', 'Suggestion'),
#         ('open', 'Open'),
#         ('closed', 'Closed'),
#         ('fixed', 'Fixed'),
#         ('pending', 'Pending'),
#         ('reopen', 'Reopen'),
#         ('not_a_bug', 'Not a bug'),
#     ]

#     bug_id = models.CharField(
#         max_length=20,
#         unique=True,
#         editable=False,
#     )

#     title = models.CharField(max_length=255)

#     # Example: Sales, Academy, Finance, Registration
#     module = models.CharField(max_length=100, db_index=True)

#     steps_to_reproduce = models.TextField()
#     expected_result = models.TextField()
#     actual_result = models.TextField()

#     screenshot = models.ImageField(
#         upload_to='testing/bug_screenshots/',
#         blank=True,
#         null=True,
#     )

#     severity = models.CharField(
#         max_length=20,
#         choices=SEVERITY_CHOICES,
#         default='minor',
#     )

#     status = models.CharField(
#         max_length=20,
#         choices=STATUS_CHOICES,
#         default='open',
#         db_index=True,
#     )

#     # Optional link to an existing project
#     project = models.ForeignKey(
#         'project_management.ProjectManagement',
#         on_delete=models.SET_NULL,
#         null=True,
#         blank=True,
#         related_name='bug_reports',
#     )

#     reported_by = models.ForeignKey(
#         settings.AUTH_USER_MODEL,
#         on_delete=models.PROTECT,
#         related_name='reported_bugs',
#     )

#     assigned_developer = models.ForeignKey(
#         settings.AUTH_USER_MODEL,
#         on_delete=models.SET_NULL,
#         null=True,
#         blank=True,
#         related_name='assigned_bug_reports',
#     )

#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
#     fixed_at = models.DateTimeField(null=True, blank=True)
#     verified_at = models.DateTimeField(null=True, blank=True)

#     def save(self, *args, **kwargs):
#         if not self.bug_id:
#             self.bug_id = f"BUG-{uuid.uuid4().hex[:8].upper()}"

#         super().save(*args, **kwargs)

#     def __str__(self):
#         return f"{self.bug_id} - {self.title}"


# class BugStatusHistory(models.Model):

#     bug = models.ForeignKey(
#         BugReport,
#         on_delete=models.CASCADE,
#         related_name='status_history',
#     )

#     old_status = models.CharField(
#         max_length=20,
#         choices=BugReport.STATUS_CHOICES,
#         blank=True,
#     )

#     new_status = models.CharField(
#         max_length=20,
#         choices=BugReport.STATUS_CHOICES,
#     )

#     changed_by = models.ForeignKey(
#         settings.AUTH_USER_MODEL,
#         on_delete=models.PROTECT,
#         related_name='bug_status_changes',
#     )

#     comment = models.TextField(blank=True)
#     changed_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"{self.bug.bug_id}: {self.old_status} -> {self.new_status}"
