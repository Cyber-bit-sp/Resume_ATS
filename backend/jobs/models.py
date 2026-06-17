from django.conf import settings
from django.db import models


class JobDescription(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    job_title = models.CharField(max_length=255)
    company_name = models.CharField(max_length=255, blank=True)
    description_text = models.TextField()
    job_url = models.URLField(blank=True)
    location = models.CharField(max_length=255, blank=True)
    work_type = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        company = f" at {self.company_name}" if self.company_name else ""
        return f"{self.job_title}{company}"
