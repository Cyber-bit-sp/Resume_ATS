from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.response import Response

from .models import Resume
from .serializers import ResumeSerializer


class ResumeViewSet(viewsets.ModelViewSet):
    serializer_class = ResumeSerializer

    def get_queryset(self):
        if self.request.user.is_staff:
            return Resume.objects.all().distinct()
        return Resume.objects.filter(
            Q(user=self.request.user) | Q(shared_with=self.request.user)
        ).distinct()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def update(self, request, *args, **kwargs):
        resume = self.get_object()
        if resume.user_id != request.user.id and not request.user.is_staff:
            return Response({"detail": "Shared resumes cannot be edited."}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        resume = self.get_object()
        if resume.user_id != request.user.id and not request.user.is_staff:
            return Response({"detail": "Shared resumes cannot be deleted."}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)
