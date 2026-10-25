from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import BranchViewSet, LoginView, MemberViewSet, MeView, RegisterView

router = DefaultRouter()
router.register("branches", BranchViewSet, basename="branch")
router.register("members", MemberViewSet, basename="member")

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("me/", MeView.as_view(), name="me"),
] + router.urls
