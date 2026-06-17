from rest_framework import serializers

from common.file_text import extract_text_from_upload, validate_text_upload

from .models import Prompt


class PromptSerializer(serializers.ModelSerializer):
    prompt_text = serializers.CharField(required=False, allow_blank=True)
    upload_file = serializers.FileField(write_only=True, required=False)

    class Meta:
        model = Prompt
        fields = ["id", "title", "prompt_text", "upload_file", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_upload_file(self, file_obj):
        return validate_text_upload(file_obj)

    def validate(self, attrs):
        upload_file = attrs.pop("upload_file", None)
        if upload_file:
            extracted_text = extract_text_from_upload(upload_file)
            if extracted_text.strip():
                attrs["prompt_text"] = extracted_text
            if not attrs.get("title"):
                attrs["title"] = upload_file.name
        if not (attrs.get("prompt_text") or "").strip():
            if upload_file:
                raise serializers.ValidationError({"upload_file": "No readable text was found in that file."})
            raise serializers.ValidationError({"prompt_text": "Enter prompt text or upload a prompt file."})
        return attrs
