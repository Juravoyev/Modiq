from rest_framework import generics, mixins, permissions, viewsets
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.common.permissions import IsBusinessMember, IsManagerOrReadOnly, IsOwnerOrReadOnly
from apps.common.views import BusinessScopedViewSet

from .models import Branch, Membership
from .serializers import (
    BranchSerializer,
    MemberSerializer,
    MemberUpdateSerializer,
    MeSerializer,
    PhoneTokenObtainPairSerializer,
    RegisterSerializer,
)


class RegisterView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(MeSerializer(user).data, status=201)


class LoginView(TokenObtainPairView):
    serializer_class = PhoneTokenObtainPairSerializer


class MeView(generics.RetrieveAPIView):
    serializer_class = MeSerializer

    def get_object(self):
        return self.request.user


class BranchViewSet(BusinessScopedViewSet):
    serializer_class = BranchSerializer
    permission_classes = [permissions.IsAuthenticated, IsBusinessMember, IsManagerOrReadOnly]
    queryset = Branch.objects.all()
    # Filial o'chirilmaydi (savdo va qoldiq tarixi bor), faqat nofaol qilinadi.
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        if self.request.membership.is_manager:
            # Menejer nofaol filiallarni ham ko'radi, aks holda ularni qayta faollashtirib bo'lmaydi.
            return super().get_queryset()
        return self.request.membership.allowed_branches()


class MemberViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, mixins.RetrieveModelMixin,
                    mixins.UpdateModelMixin, viewsets.GenericViewSet):
    serializer_class = MemberSerializer
    permission_classes = [permissions.IsAuthenticated, IsBusinessMember, IsOwnerOrReadOnly]
    queryset = Membership.objects.select_related("user").prefetch_related("branches").order_by("id")
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_serializer_class(self):
        return MemberUpdateSerializer if self.action == "partial_update" else MemberSerializer

    def get_queryset(self):
        return super().get_queryset().filter(business=self.request.business)

    def perform_create(self, serializer):
        serializer.save(business=self.request.business)
