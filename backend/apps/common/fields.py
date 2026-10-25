from rest_framework import serializers


class BusinessScopedPKField(serializers.PrimaryKeyRelatedField):
    """Faqat joriy biznesga tegishli obyektlarni qabul qiladigan PK maydon.

    Boshqa tenantning id raqamini yuborsa, "topilmadi" xatosi qaytadi.
    """

    def get_queryset(self):
        request = self.context.get("request")
        qs = super().get_queryset()
        if request is None or not hasattr(request, "business"):
            return qs.none()
        return qs.filter(business=request.business)


class AllowedBranchPKField(serializers.PrimaryKeyRelatedField):
    """Foydalanuvchiga ruxsat berilgan filiallardan birini qabul qiladi."""

    def get_queryset(self):
        request = self.context.get("request")
        if request is None or not hasattr(request, "membership"):
            return super().get_queryset().none()
        return request.membership.allowed_branches()
