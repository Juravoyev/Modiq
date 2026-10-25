from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("categories", views.CategoryViewSet, basename="category")
router.register("brands", views.BrandViewSet, basename="brand")
router.register("seasons", views.SeasonViewSet, basename="season")
router.register("colors", views.ColorViewSet, basename="color")
router.register("sizes", views.SizeViewSet, basename="size")
router.register("products", views.ProductViewSet, basename="product")
router.register("variants", views.VariantViewSet, basename="variant")

urlpatterns = router.urls
