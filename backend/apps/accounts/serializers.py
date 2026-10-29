from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.common.utils import normalize_phone

from .models import Branch, Business, Membership, User


class PhoneField(serializers.CharField):
    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        try:
            return normalize_phone(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages)


class RegisterSerializer(serializers.Serializer):
    """Yangi do'kon egasini, biznesni va birinchi filialni yaratadi."""

    phone = PhoneField()
    password = serializers.CharField(write_only=True, min_length=8)
    full_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    business_name = serializers.CharField(max_length=150)
    branch_name = serializers.CharField(max_length=150, required=False, default="Asosiy do'kon")

    def validate_phone(self, value):
        if User.objects.filter(phone=value).exists():
            raise serializers.ValidationError("Bu telefon raqami allaqachon ro'yxatdan o'tgan.")
        return value

    def validate(self, attrs):
        try:
            password_validation.validate_password(attrs["password"], User(phone=attrs["phone"]))
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": exc.messages})
        return attrs

    @transaction.atomic
    def create(self, validated):
        user = User.objects.create_user(
            phone=validated["phone"], password=validated["password"], full_name=validated.get("full_name", "")
        )
        business = Business.objects.create(name=validated["business_name"], phone=validated["phone"])
        Branch.objects.create(business=business, name=validated["branch_name"])
        Membership.objects.create(user=user, business=business, role=Membership.Role.OWNER)
        return user


class PhoneTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Login: telefonni normallashtirib, keyin standart JWT tekshiruvini bajaradi."""

    def validate(self, attrs):
        try:
            attrs[self.username_field] = normalize_phone(attrs.get(self.username_field, ""))
        except DjangoValidationError:
            pass  # noto'g'ri formatdagi raqam oddiy "login xato" bilan qaytadi
        return super().validate(attrs)


class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = ["id", "name", "kind", "address", "is_active"]

    def validate_name(self, value):
        qs = Branch.objects.filter(business=self.context["request"].business, name__iexact=value)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Bu nomli filial allaqachon mavjud.")
        return value

    def validate_is_active(self, value):
        # Oxirgi faol filial yopilsa, hech kim savdo qila olmay qoladi.
        if not value and self.instance is not None and self.instance.is_active:
            others = Branch.objects.filter(business=self.instance.business, is_active=True).exclude(pk=self.instance.pk)
            if not others.exists():
                raise serializers.ValidationError("Kamida bitta faol filial qolishi kerak.")
        return value


class BusinessSerializer(serializers.ModelSerializer):
    class Meta:
        model = Business
        fields = ["id", "name", "phone", "address", "currency"]
        read_only_fields = ["currency"]


class MeSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source="membership.role", read_only=True)
    business = BusinessSerializer(source="membership.business", read_only=True)
    branches = serializers.SerializerMethodField()
    can_approve_returns = serializers.BooleanField(source="membership.may_approve_returns", read_only=True)

    class Meta:
        model = User
        fields = ["id", "phone", "full_name", "role", "business", "branches", "can_approve_returns"]

    @extend_schema_field(BranchSerializer(many=True))
    def get_branches(self, user):
        return BranchSerializer(user.membership.allowed_branches(), many=True).data


class MemberSerializer(serializers.ModelSerializer):
    """Egasi yangi xodim qo'shadi (menejer yoki sotuvchi)."""

    phone = PhoneField(source="user.phone")
    full_name = serializers.CharField(source="user.full_name", required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, min_length=8)
    branch_ids = serializers.PrimaryKeyRelatedField(
        source="branches", many=True, queryset=Branch.objects.all(), required=False
    )

    class Meta:
        model = Membership
        fields = ["id", "phone", "full_name", "password", "role", "branch_ids", "can_approve_returns", "is_active"]

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get("request")
        if request is not None and hasattr(request, "business"):
            fields["branch_ids"].child_relation.queryset = Branch.objects.filter(business=request.business)
        return fields

    def validate_role(self, value):
        if value == Membership.Role.OWNER:
            raise serializers.ValidationError("Ikkinchi egani bu yerdan qo'shib bo'lmaydi.")
        return value

    def validate(self, attrs):
        phone = attrs.get("user", {}).get("phone")
        if phone and User.objects.filter(phone=phone).exists():
            raise serializers.ValidationError({"phone": "Bu telefon raqami allaqachon ro'yxatdan o'tgan."})
        return attrs

    @transaction.atomic
    def create(self, validated):
        user_data = validated.pop("user")
        branches = validated.pop("branches", [])
        password = validated.pop("password")
        user = User.objects.create_user(phone=user_data["phone"], password=password,
                                        full_name=user_data.get("full_name", ""))
        membership = Membership.objects.create(user=user, **validated)
        membership.branches.set(branches)
        return membership


class MemberUpdateSerializer(MemberSerializer):
    """Xodimni tahrirlash: telefon o'zgarmaydi, parol faqat berilsa almashtiriladi."""

    phone = serializers.CharField(source="user.phone", read_only=True)
    password = serializers.CharField(write_only=True, min_length=8, required=False)

    def validate(self, attrs):
        if self.instance.role == Membership.Role.OWNER and ("role" in attrs or attrs.get("is_active") is False):
            raise serializers.ValidationError({"detail": "Do'kon egasining roli va holatini o'zgartirib bo'lmaydi."})
        return attrs

    @transaction.atomic
    def update(self, instance, validated):
        user_data = validated.pop("user", {})
        branches = validated.pop("branches", None)
        password = validated.pop("password", None)
        user = instance.user
        if "full_name" in user_data:
            user.full_name = user_data["full_name"]
        if password:
            user.set_password(password)
        user.save()
        for name, value in validated.items():
            setattr(instance, name, value)
        instance.save()
        if branches is not None:
            instance.branches.set(branches)
        return instance
