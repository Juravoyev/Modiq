from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import PricingSettingsView, PromotionViewSet

router = DefaultRouter()
router.register("promotions", PromotionViewSet, basename="promotion")

urlpatterns = [path("settings/", PricingSettingsView.as_view(), name="pricing-settings")] + router.urls
