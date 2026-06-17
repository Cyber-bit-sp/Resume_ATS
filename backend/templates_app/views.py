from rest_framework import viewsets

from .models import ResumeTemplate
from .serializers import ResumeTemplateSerializer


class ResumeTemplateViewSet(viewsets.ModelViewSet):
    serializer_class = ResumeTemplateSerializer

    def get_queryset(self):
        return ResumeTemplate.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
