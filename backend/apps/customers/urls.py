from rest_framework.routers import DefaultRouter

from .views import CustomerGroupViewSet, CustomerViewSet

router = DefaultRouter()
# "groups" birinchi: aks holda "" prefiksli mijoz marshruti uni id deb qabul qiladi.
router.register("groups", CustomerGroupViewSet, basename="customer-group")
router.register("", CustomerViewSet, basename="customer")

urlpatterns = router.urls
