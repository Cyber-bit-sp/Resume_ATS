from django.http import FileResponse
from django.db.models import Q
from django.utils import timezone
from django.utils.text import slugify
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from jobs.models import JobDescription
from prompts.models import Prompt
from resumes.models import Resume

from .docx_builder import build_generated_doc
from .keyword_matcher import score_resume
from .models import ResumeGeneration
from .pdf_builder import build_resume_pdf_bytes
from .registry import registry_response_payload, save_bytes_to_resume_registry, save_file_to_resume_registry
from .serializers import GenerateResumeSerializer, ResumeGenerationSerializer
from .services import build_automatic_job_description, generate_resume_sections, render_resume_text


def _filename_token(value, fallback):
    token = slugify((value or "").strip())
    return token if token else fallback


def _generation_download_name(generation, ext="docx"):
    timestamp = timezone.localtime(generation.created_at).strftime("%Y%m%d_%H%M%S")
    resume_part = _filename_token(generation.resume.title, "resume")
    job_description_part = _filename_token(generation.job_description.company_name, "job-description")
    position_part = _filename_token(generation.job_description.job_title, "position")
    return f"{resume_part}_{job_description_part}_{position_part}_{timestamp}.{ext}"


class GenerateResumeView(APIView):
    def post(self, request):
        serializer = GenerateResumeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        resume = Resume.objects.filter(
            Q(id=data["resume_id"], user=request.user) | Q(id=data["resume_id"], shared_with=request.user)
        ).distinct().first()
        prompt = None
        job = None

        if not resume:
            return Response({"detail": "Resume was not found."}, status=status.HTTP_404_NOT_FOUND)

        if data.get("prompt_id"):
            prompt = Prompt.objects.filter(id=data["prompt_id"], user=request.user).first()
            if not prompt:
                return Response({"detail": "Selected prompt was not found."}, status=status.HTTP_404_NOT_FOUND)

        if data.get("job_description_id"):
            job = JobDescription.objects.filter(id=data["job_description_id"], user=request.user).first()
            if not job:
                return Response({"detail": "Selected job description was not found."}, status=status.HTTP_404_NOT_FOUND)

        if not job:
            job = JobDescription.objects.create(
                user=request.user,
                job_title="Generated Role",
                company_name="Generated Company",
                description_text=build_automatic_job_description(resume.original_text, prompt.prompt_text if prompt else data.get("custom_prompt", ""))["description_text"],
                job_url="",
                location="",
                work_type="",
            )

        template = None
        if resume.resume_template_id:
            template = resume.resume_template

        custom_prompt = prompt.prompt_text if prompt else data.get("custom_prompt", "")
        sections = generate_resume_sections(resume.original_text, job.description_text, custom_prompt)
        generated_text = render_resume_text(sections)
        score = score_resume(job.description_text, generated_text)

        generation = ResumeGeneration.objects.create(
            user=request.user,
            resume=resume,
            job_description=job,
            resume_template=template,
            custom_prompt=custom_prompt,
            generated_resume_text=generated_text,
            ats_score=score["score"],
            matched_keywords=score["matched_keywords"],
            missing_keywords=score["missing_keywords"],
        )

        try:
            relative_path = build_generated_doc(template.template_file.path if template else None, sections, generation.id)
        except ValueError as exc:
            generation.delete()
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        generation.generated_file.name = str(relative_path).replace("\\", "/")
        generation.save(update_fields=["generated_file"])
        response_data = ResumeGenerationSerializer(generation, context={"request": request}).data
        response_data["generation_id"] = generation.id
        return Response(response_data, status=status.HTTP_201_CREATED)


class ResumeGenerationListView(generics.ListAPIView):
    serializer_class = ResumeGenerationSerializer

    def get_queryset(self):
        return ResumeGeneration.objects.filter(user=self.request.user)


class ResumeGenerationDetailView(generics.RetrieveDestroyAPIView):
    serializer_class = ResumeGenerationSerializer

    def get_queryset(self):
        return ResumeGeneration.objects.filter(user=self.request.user)

    def perform_destroy(self, instance):
        if instance.generated_file:
            instance.generated_file.delete(save=False)
        instance.delete()


class ResumeGenerationDownloadView(APIView):
    def get(self, request, pk):
        generation = ResumeGeneration.objects.filter(pk=pk, user=request.user).first()
        if not generation:
            return Response({"detail": "Generated resume file was not found."}, status=status.HTTP_404_NOT_FOUND)
        try:
            pdf_buffer = build_resume_pdf_bytes(generation)
        except RuntimeError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        filename = _generation_download_name(generation, "pdf")
        save_bytes_to_resume_registry(generation, filename, pdf_buffer.getvalue())
        pdf_buffer.seek(0)
        return FileResponse(pdf_buffer, as_attachment=True, filename=filename, content_type="application/pdf")


class ResumeGenerationSaveView(APIView):
    def post(self, request, pk):
        generation = ResumeGeneration.objects.filter(pk=pk, user=request.user).first()
        if not generation:
            return Response({"detail": "Generated resume file was not found."}, status=status.HTTP_404_NOT_FOUND)
        try:
            pdf_buffer = build_resume_pdf_bytes(generation)
        except RuntimeError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        filename = _generation_download_name(generation, "pdf")
        target_path = save_bytes_to_resume_registry(
            generation,
            filename,
            pdf_buffer.getvalue(),
            request.data.get("target_folder"),
        )
        return Response(registry_response_payload(target_path), status=status.HTTP_200_OK)


class ResumeGenerationDownloadDocxView(APIView):
    def get(self, request, pk):
        generation = ResumeGeneration.objects.filter(pk=pk, user=request.user).first()
        if not generation or not generation.generated_file:
            return Response({"detail": "Generated resume file was not found."}, status=status.HTTP_404_NOT_FOUND)
        filename = _generation_download_name(generation, "docx")
        try:
            with generation.generated_file.open("rb") as source_handle:
                save_file_to_resume_registry(generation, filename, source_handle)
            file_handle = generation.generated_file.open("rb")
        except Exception:
            return Response({"detail": "Could not open the generated file."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return FileResponse(
            file_handle,
            as_attachment=True,
            filename=filename,
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )


class ResumeGenerationSaveDocxView(APIView):
    def post(self, request, pk):
        generation = ResumeGeneration.objects.filter(pk=pk, user=request.user).first()
        if not generation or not generation.generated_file:
            return Response({"detail": "Generated resume file was not found."}, status=status.HTTP_404_NOT_FOUND)
        filename = _generation_download_name(generation, "docx")
        try:
            with generation.generated_file.open("rb") as source_handle:
                target_path = save_file_to_resume_registry(
                    generation,
                    filename,
                    source_handle,
                    request.data.get("target_folder"),
                )
        except Exception:
            return Response({"detail": "Could not open the generated file."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(registry_response_payload(target_path), status=status.HTTP_200_OK)
