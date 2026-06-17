from rest_framework.routers import DefaultRouter

from .views import PromptViewSet


router = DefaultRouter()
router.register("", PromptViewSet, basename="prompt")

urlpatterns = router.urls
