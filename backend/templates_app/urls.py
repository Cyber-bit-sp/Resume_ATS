from rest_framework.routers import DefaultRouter

from .views import ResumeTemplateViewSet


router = DefaultRouter()
router.register("", ResumeTemplateViewSet, basename="resume-template")
urlpatterns = router.urls
