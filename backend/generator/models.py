from django.conf import settings
from django.db import models


class ResumeGeneration(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    resume = models.ForeignKey("resumes.Resume", on_delete=models.CASCADE)
    job_description = models.ForeignKey("jobs.JobDescription", on_delete=models.CASCADE)
    resume_template = models.ForeignKey(
        "templates_app.ResumeTemplate",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    custom_prompt = models.TextField(blank=True)
    generated_resume_text = models.TextField()
    generated_file = models.FileField(upload_to="generated_resumes/", blank=True, null=True)
    ats_score = models.IntegerField(default=0)
    matched_keywords = models.JSONField(default=list, blank=True)
    missing_keywords = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.resume.title} -> {self.job_description.job_title}"
