from rest_framework.routers import DefaultRouter

from .views import JobDescriptionViewSet


router = DefaultRouter()
router.register("", JobDescriptionViewSet, basename="job-description")
urlpatterns = router.urls
