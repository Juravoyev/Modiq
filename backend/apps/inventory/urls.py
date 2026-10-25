from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("stock", views.StockViewSet, basename="stock")
router.register("movements", views.StockMovementViewSet, basename="movement")
router.register("receipts", views.ReceiptViewSet, basename="receipt")
router.register("transfers", views.TransferViewSet, basename="transfer")

urlpatterns = router.urls
