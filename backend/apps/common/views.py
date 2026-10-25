from rest_framework import viewsets


class BusinessScopedMixin:
    """Queryset'ni joriy biznes bilan cheklaydi va yaratishda biznesni o'rnatadi."""

    def get_queryset(self):
        return super().get_queryset().filter(business=self.request.business)

    def perform_create(self, serializer):
        serializer.save(business=self.request.business)


class BusinessScopedViewSet(BusinessScopedMixin, viewsets.ModelViewSet):
    pass
