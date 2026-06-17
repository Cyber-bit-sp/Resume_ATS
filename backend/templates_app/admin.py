from django.contrib import admin

from .models import ResumeTemplate


@admin.register(ResumeTemplate)
class ResumeTemplateAdmin(admin.ModelAdmin):
    list_display = ["template_name", "user", "is_default", "created_at"]
    list_filter = ["is_default"]
    search_fields = ["template_name", "description", "user__username"]
