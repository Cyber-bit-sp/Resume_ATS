from rest_framework import serializers

from common.file_text import extract_text_from_upload, validate_text_upload

from .models import JobDescription


class JobDescriptionSerializer(serializers.ModelSerializer):
    description_text = serializers.CharField(required=False, allow_blank=True)
    upload_file = serializers.FileField(write_only=True, required=False)

    class Meta:
        model = JobDescription
        fields = [
            "id",
            "job_title",
            "company_name",
            "description_text",
            "job_url",
            "location",
            "work_type",
            "upload_file",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate_upload_file(self, file_obj):
        return validate_text_upload(file_obj)

    def validate(self, attrs):
        upload_file = attrs.pop("upload_file", None)
        if upload_file:
            attrs["description_text"] = extract_text_from_upload(upload_file)
        if not (attrs.get("description_text") or "").strip():
            if upload_file:
                raise serializers.ValidationError({"upload_file": "No readable text was found in that file."})
            raise serializers.ValidationError({"description_text": "Enter a job description or upload a file."})
        return attrs
