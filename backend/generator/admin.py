from django.contrib import admin

from .models import ResumeGeneration


@admin.register(ResumeGeneration)
class ResumeGenerationAdmin(admin.ModelAdmin):
    list_display = ["resume", "job_description", "user", "ats_score", "created_at"]
    search_fields = ["resume__title", "job_description__job_title", "user__username"]
