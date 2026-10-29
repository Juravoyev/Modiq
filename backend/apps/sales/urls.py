from rest_framework.routers import DefaultRouter

from .views import SaleReturnViewSet, SaleViewSet

router = DefaultRouter()
# "returns" birinchi ro'yxatdan o'tadi: aks holda "" prefiksli savdo marshruti uni savdo id deb qabul qiladi.
router.register("returns", SaleReturnViewSet, basename="sale-return")
router.register("", SaleViewSet, basename="sale")

urlpatterns = router.urls
