import mimetypes

from django.conf import settings
from rest_framework import serializers

from .models import ResumeTemplate


ALLOWED_TEMPLATE_EXTENSIONS = {".docx", ".doc", ".pdf"}
DOCX_MIME_TYPES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/zip",
}
DOC_MIME_TYPES = {
    "application/msword",
    "application/vnd.ms-word",
    "application/octet-stream",
}
PDF_MIME_TYPES = {
    "application/pdf",
}


class ResumeTemplateSerializer(serializers.ModelSerializer):
    template_file_url = serializers.SerializerMethodField()

    class Meta:
        model = ResumeTemplate
        fields = [
            "id",
            "template_name",
            "template_file",
            "template_file_url",
            "description",
            "is_default",
            "created_at",
        ]
        read_only_fields = ["id", "template_file_url", "created_at"]

    def get_template_file_url(self, obj):
        request = self.context.get("request")
        if obj.template_file and request:
            return request.build_absolute_uri(obj.template_file.url)
        return obj.template_file.url if obj.template_file else None

    def validate_template_file(self, file_obj):
        file_name = file_obj.name.lower()
        guessed_type, _ = mimetypes.guess_type(file_name)
        content_type = getattr(file_obj, "content_type", None)

        extension = ".docx" if file_name.endswith(".docx") else ".doc" if file_name.endswith(".doc") else ".pdf" if file_name.endswith(".pdf") else ""
        if extension not in ALLOWED_TEMPLATE_EXTENSIONS:
            raise serializers.ValidationError("Upload a .docx, .doc, or .pdf template file.")

        if file_obj.size > settings.MAX_TEMPLATE_UPLOAD_SIZE:
            raise serializers.ValidationError("Template file is too large.")

        if extension == ".docx" and content_type and content_type not in DOCX_MIME_TYPES and guessed_type not in DOCX_MIME_TYPES:
            raise serializers.ValidationError("Uploaded DOCX file type is invalid.")
        if extension == ".doc" and content_type and content_type not in DOC_MIME_TYPES and guessed_type not in DOC_MIME_TYPES:
            raise serializers.ValidationError("Uploaded DOC file type is invalid.")
        if extension == ".pdf" and content_type and content_type not in PDF_MIME_TYPES and guessed_type not in PDF_MIME_TYPES:
            raise serializers.ValidationError("Uploaded PDF file type is invalid.")

        return file_obj
