from rest_framework import serializers

from common.file_text import extract_text_from_upload

from .models import ResumeGeneration


class GenerateResumeSerializer(serializers.Serializer):
    resume_id = serializers.IntegerField()
    job_description_id = serializers.IntegerField()
    prompt_id = serializers.IntegerField(required=False, allow_null=True)
    prompt = serializers.FileField(required=False)

    def validate_prompt(self, file_obj):
        file_name = file_obj.name.lower()
        if not (file_name.endswith(".txt") or file_name.endswith(".doc")):
            raise serializers.ValidationError("Upload a .txt or .doc file for prompt.")
        return file_obj

    def validate(self, attrs):
        prompt_file = attrs.pop("prompt", None)
        attrs["custom_prompt"] = extract_text_from_upload(prompt_file) if prompt_file else ""
        return attrs


class ResumeGenerationSerializer(serializers.ModelSerializer):
    generated_file_url = serializers.SerializerMethodField()
    resume_title = serializers.CharField(source="resume.title", read_only=True)
    job_title = serializers.CharField(source="job_description.job_title", read_only=True)
    company_name = serializers.CharField(source="job_description.company_name", read_only=True)
    job_url = serializers.CharField(source="job_description.job_url", read_only=True)
    template_name = serializers.CharField(source="resume_template.template_name", read_only=True, allow_null=True)

    class Meta:
        model = ResumeGeneration
        fields = [
            "id",
            "resume",
            "resume_title",
            "job_description",
            "job_title",
            "company_name",
            "job_url",
            "resume_template",
            "template_name",
            "custom_prompt",
            "generated_resume_text",
            "generated_file",
            "generated_file_url",
            "ats_score",
            "matched_keywords",
            "missing_keywords",
            "created_at",
        ]
        read_only_fields = fields

    def get_generated_file_url(self, obj):
        request = self.context.get("request")
        if obj.generated_file and request:
            return request.build_absolute_uri(f"/api/generations/{obj.id}/download/")
        return f"/api/generations/{obj.id}/download/" if obj.generated_file else None
