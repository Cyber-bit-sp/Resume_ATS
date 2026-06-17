from django.contrib.auth import get_user_model
from rest_framework import serializers

from common.file_text import extract_text_from_upload, validate_text_upload
from templates_app.models import ResumeTemplate

from .models import Resume

User = get_user_model()


class ResumeSerializer(serializers.ModelSerializer):
    original_text = serializers.CharField(required=False, allow_blank=True)
    upload_file = serializers.FileField(write_only=True, required=False)
    template_name = serializers.CharField(source="resume_template.template_name", read_only=True, allow_null=True)
    owner_id = serializers.IntegerField(source="user.id", read_only=True)
    owner_username = serializers.CharField(source="user.username", read_only=True)
    uploaded_by = serializers.CharField(source="user.username", read_only=True)
    shared_with = serializers.PrimaryKeyRelatedField(
        many=True,
        required=False,
        queryset=User.objects.all(),
    )
    shared_with_usernames = serializers.SerializerMethodField()

    class Meta:
        model = Resume
        fields = [
            "id",
            "title",
            "original_text",
            "upload_file",
            "resume_template",
            "template_name",
            "owner_id",
            "owner_username",
            "uploaded_by",
            "shared_with",
            "shared_with_usernames",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "resume_template", "template_name", "owner_id", "owner_username", "uploaded_by", "shared_with_usernames", "created_at", "updated_at"]

    def get_shared_with_usernames(self, obj):
        return list(obj.shared_with.order_by("username").values_list("username", flat=True))

    def validate_upload_file(self, file_obj):
        return validate_text_upload(file_obj)

    def validate(self, attrs):
        upload_file = attrs.pop("upload_file", None)
        manual_text = (attrs.get("original_text") or "").strip()
        self._uploaded_resume_file = upload_file

        if upload_file:
            extracted_text = extract_text_from_upload(upload_file)
            if extracted_text.strip():
                attrs["original_text"] = extracted_text
        if not (attrs.get("original_text") or "").strip():
            if upload_file:
                raise serializers.ValidationError({"upload_file": "No readable text was found in that file."})
            raise serializers.ValidationError({"original_text": "Enter resume text or upload a file."})
        if not manual_text and upload_file and not attrs.get("title"):
            attrs["title"] = upload_file.name
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        upload_file = getattr(self, "_uploaded_resume_file", None)
        shared_with = validated_data.pop("shared_with", [])
        if upload_file and request:
            template = ResumeTemplate.objects.create(
                user=request.user,
                template_name=validated_data.get("title") or upload_file.name,
                template_file=upload_file,
                description="Created automatically from uploaded resume.",
            )
            validated_data["resume_template"] = template
        resume = super().create(validated_data)
        if request and request.user.is_staff and shared_with:
            resume.shared_with.set(shared_with)
        return resume

    def update(self, instance, validated_data):
        request = self.context.get("request")
        shared_with = validated_data.pop("shared_with", None)
        resume = super().update(instance, validated_data)
        if request and request.user.is_staff and shared_with is not None:
            resume.shared_with.set(shared_with)
        return resume
