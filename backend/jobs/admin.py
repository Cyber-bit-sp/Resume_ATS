from django.contrib import admin

from .models import JobDescription


@admin.register(JobDescription)
class JobDescriptionAdmin(admin.ModelAdmin):
    list_display = ["job_title", "company_name", "user", "created_at"]
    search_fields = ["job_title", "company_name", "description_text", "user__username"]
