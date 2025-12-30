from django.db import models
from accounts.models import CustomUser

# ========== Models for Enquiry ==========
class Enquiry(models.Model):
    STATUS = (
        ('new', 'New'),
        ('reviewed', 'Reviewed'),
        ('responded', 'Responded'),
    )

    first_name = models.CharField(max_length=100, verbose_name="First Name")
    last_name = models.CharField(max_length=100,blank=True, null=True, verbose_name="Last Name")
    email = models.EmailField(max_length=254,verbose_name="Email Address")
    phone = models.CharField(max_length=15, verbose_name="Phone Number")
    message = models.TextField(verbose_name="Enquiry Message")
    status = models.CharField(max_length=20, choices=STATUS, default='new', verbose_name="Enquiry Status")
    created_at = models.DateTimeField( auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True,verbose_name="Last Updated")

    class Meta:
        verbose_name = "Enquiry"
        verbose_name_plural = "Enquiries"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.first_name} {self.last_name or ''} - {self.email}"

# ========== End of Models for Enquiry ==========


# ========== Models for Job Application ==========

class Designation(models.Model):
    user = models.ForeignKey(CustomUser,on_delete=models.SET_NULL, null=True, blank=True, verbose_name="User")
    name = models.CharField(max_length=100, verbose_name="Designation Name")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")

    class Meta:
        verbose_name = "Designation"
        verbose_name_plural = "Designations"
        ordering = ['name']

    def __str__(self):
        return self.name


from django.db import models

class JobPosting(models.Model):
    JOB_TYPE = (        
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('contract', 'Contract'),
        ('internship', 'Internship'),
    )
    WORK_MODE = (
        ('remote', 'Remote'),
        ('onsite', 'Onsite'),
        ('hybrid', 'Hybrid'),
    )
    STATUS = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    )

    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="User")
    job_title = models.CharField(max_length=200, verbose_name="Job Title")
    job_type = models.CharField(max_length=20, choices=JOB_TYPE, verbose_name="Job Type")
    education = models.CharField(max_length=200, null=True, blank=True, verbose_name="Education Required")
    work_mode = models.CharField(max_length=20, choices=WORK_MODE, verbose_name="Work Mode")
    designation = models.ForeignKey(Designation, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Designation")
    job_description = models.TextField(verbose_name="Job Description")
    more_details = models.TextField(verbose_name="More Details", blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS, default='active', verbose_name="Status")
    experience_required = models.CharField(max_length=100, verbose_name="Experience Required")
    salery_range = models.CharField(max_length=100, verbose_name="Salary Range")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Last Updated")

    def __str__(self):
        return self.job_title


class JobResponsibility(models.Model):
    job_posting = models.ForeignKey(JobPosting, on_delete=models.CASCADE, related_name='responsibilities', verbose_name="Job Posting", null=True, blank=True)
    responsibility = models.TextField(verbose_name="Responsibility")

    def __str__(self):
        return f"{self.job_posting.job_title} - {self.responsibility[:50]}..."


class JobRequirement(models.Model):
    job_posting = models.ForeignKey(JobPosting, on_delete=models.CASCADE, related_name='requirements', verbose_name="Job Posting", null=True, blank=True)
    requirement = models.TextField(verbose_name="Requirement")

    def __str__(self):
        return f"{self.job_posting.job_title} - {self.requirement[:50]}..."
    
    
class JobPostingSkill(models.Model):
    job_posting = models.ForeignKey(JobPosting, on_delete=models.CASCADE, related_name='skills', verbose_name="Job Posting", null=True, blank=True)
    skill = models.CharField(max_length=100, verbose_name="Skill")

    def __str__(self):
        return f"{self.job_posting.job_title} - {self.skill}"


class JobWhyJoinUs(models.Model):
    job_posting = models.ForeignKey(JobPosting, on_delete=models.CASCADE, related_name='benefits', verbose_name="Job Posting", null=True, blank=True)
    reason = models.TextField(verbose_name="Why Join Us")

    def __str__(self):
        return f"{self.job_posting.job_title} - {self.reason[:50]}..."


class JobApplication(models.Model):
    Status = (
        ('applied', 'Applied'),
        ('under_review', 'Under Review'),
        ('shortlisted', 'Shortlisted'),
        ('interview_scheduled', 'Interview Scheduled'),
        ('hired', 'Hired'),
        ('rejected', 'Rejected'),
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    job = models.ForeignKey(JobPosting, on_delete=models.CASCADE, related_name='applications', verbose_name="Job Posting", null=True, blank=True)
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    designation = models.ForeignKey(Designation, on_delete=models.SET_NULL, null=True, blank=True)
    experience = models.PositiveIntegerField(help_text="Years of experience")
    resume = models.FileField(upload_to='resumes/')
    status = models.CharField(max_length=20, choices=Status, default='applied')
    applied_at = models.DateTimeField(auto_now_add=True)

# ========== End of Models for Job Application ==========


