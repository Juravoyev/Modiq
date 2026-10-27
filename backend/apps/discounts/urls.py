from rest_framework.routers import DefaultRouter

from .views import DiscountViewSet

router = DefaultRouter()
router.register("", DiscountViewSet, basename="discount")

urlpatterns = router.urls
