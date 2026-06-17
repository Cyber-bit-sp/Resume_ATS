import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("jobs", "0001_initial"),
        ("resumes", "0001_initial"),
        ("templates_app", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ResumeGeneration",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("custom_prompt", models.TextField(blank=True)),
                ("generated_resume_text", models.TextField()),
                ("generated_file", models.FileField(blank=True, null=True, upload_to="generated_resumes/")),
                ("ats_score", models.IntegerField(default=0)),
                ("matched_keywords", models.JSONField(blank=True, default=list)),
                ("missing_keywords", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("job_description", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="jobs.jobdescription")),
                ("resume", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="resumes.resume")),
                (
                    "resume_template",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="templates_app.resumetemplate",
                    ),
                ),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        )
    ]
