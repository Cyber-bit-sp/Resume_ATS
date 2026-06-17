from django.urls import path

from .views import (
    GenerateResumeView,
    ResumeGenerationDetailView,
    ResumeGenerationDownloadDocxView,
    ResumeGenerationDownloadView,
    ResumeGenerationSaveDocxView,
    ResumeGenerationSaveView,
    ResumeGenerationListView,
)


urlpatterns = [
    path("generate-resume/", GenerateResumeView.as_view(), name="generate-resume"),
    path("generations/", ResumeGenerationListView.as_view(), name="generation-list"),
    path("generations/<int:pk>/", ResumeGenerationDetailView.as_view(), name="generation-detail"),
    path("generations/<int:pk>/download/", ResumeGenerationDownloadView.as_view(), name="generation-download"),
    path("generations/<int:pk>/download-docx/", ResumeGenerationDownloadDocxView.as_view(), name="generation-download-docx"),
    path("generations/<int:pk>/save/", ResumeGenerationSaveView.as_view(), name="generation-save"),
    path("generations/<int:pk>/save-docx/", ResumeGenerationSaveDocxView.as_view(), name="generation-save-docx"),
]
