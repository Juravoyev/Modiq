from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.common.fields import BusinessScopedPKField
from apps.common.utils import normalize_phone

from .models import Customer, CustomerGroup


class CustomerGroupSerializer(serializers.ModelSerializer):
    customers_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = CustomerGroup
        fields = ["id", "name", "discount_percent", "customers_count"]

    def validate_name(self, value):
        business = self.context["request"].business
        qs = CustomerGroup.objects.filter(business=business, name__iexact=value.strip())
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Bu nomdagi toifa allaqachon bor.")
        return value.strip()

    def validate_discount_percent(self, value):
        if value > 50:
            raise serializers.ValidationError("Imtiyoz 50% dan oshmasligi kerak.")
        return value


class CustomerSerializer(serializers.ModelSerializer):
    group = BusinessScopedPKField(queryset=CustomerGroup.objects.all(), allow_null=True, required=False)
    group_name = serializers.CharField(source="group.name", read_only=True, default=None)
    discount_percent = serializers.IntegerField(read_only=True)
    purchases_count = serializers.IntegerField(read_only=True, default=0)
    total_spent = serializers.DecimalField(max_digits=16, decimal_places=2, read_only=True, default=0)

    class Meta:
        model = Customer
        fields = ["id", "phone", "full_name", "group", "group_name", "discount_percent", "note", "created_at",
                  "purchases_count", "total_spent"]

    def validate_phone(self, value):
        try:
            phone = normalize_phone(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.messages[0])
        qs = Customer.objects.filter(business=self.context["request"].business, phone=phone)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Bu telefon raqamli mijoz allaqachon bor.")
        return phone

    def validate_group(self, group):
        # Sotuvchi o'ziga tanish odamga VIP berib qo'ymasligi uchun toifani faqat egasi yoki menejer belgilaydi.
        membership = self.context["request"].membership
        current = self.instance.group if self.instance else None
        if group != current and not membership.is_manager:
            raise serializers.ValidationError("Imtiyoz toifasini faqat egasi yoki menejer belgilaydi.")
        return group
