from django.contrib import admin

from .models import Resume


@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ["title", "user", "updated_at"]
    search_fields = ["title", "original_text", "user__username"]
