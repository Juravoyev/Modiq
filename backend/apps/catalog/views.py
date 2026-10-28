from django.db.models import IntegerField, OuterRef, Prefetch, Q, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from django_filters import rest_framework as filters
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from apps.common.permissions import IsBusinessMember, IsManagerOrReadOnly
from apps.common.views import BusinessScopedViewSet
from apps.inventory.models import Stock

from .models import Brand, Category, Color, Product, ProductVariant, Season, Size
from .serializers import (
    BrandSerializer,
    CategorySerializer,
    ColorSerializer,
    GenerateVariantsSerializer,
    ProductImageSerializer,
    ProductSerializer,
    SeasonSerializer,
    SizeSerializer,
    VariantSerializer,
)
from .services import (
    delete_or_archive_product,
    delete_or_archive_variant,
    generate_variants,
    remove_product_image,
    set_product_image,
)

MANAGER_WRITE = [permissions.IsAuthenticated, IsBusinessMember, IsManagerOrReadOnly]


def _destroy_response(archived: bool) -> Response:
    if archived:
        return Response({"archived": True, "detail": "Tarixi bor, shuning uchun o'chirilmadi, arxivlandi."})
    return Response(status=status.HTTP_204_NO_CONTENT)


class VariantFilter(filters.FilterSet):
    # Variant faqat o'zi ham, tovari ham faol bo'lsa sotiladi (tovar arxivlansa variantlari ham yashiriladi).
    is_active = filters.BooleanFilter(method="filter_active")

    class Meta:
        model = ProductVariant
        fields = ["product", "color", "size"]

    def filter_active(self, queryset, name, value):
        active = Q(is_active=True, product__is_active=True)
        return queryset.filter(active) if value else queryset.exclude(active)


def _stock_branches(request):
    """?branch=<id> bo'lsa, faqat o'sha filial (agar ruxsat bo'lsa), aks holda barcha ruxsat etilganlari."""
    allowed = request.membership.allowed_branches()
    branch_id = request.query_params.get("branch")
    if branch_id and branch_id.isdigit():
        return allowed.filter(pk=int(branch_id))
    return allowed


class _SimpleCatalogViewSet(BusinessScopedViewSet):
    permission_classes = MANAGER_WRITE
    search_fields = ["name"]


class CategoryViewSet(_SimpleCatalogViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class BrandViewSet(_SimpleCatalogViewSet):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer


class SeasonViewSet(_SimpleCatalogViewSet):
    queryset = Season.objects.all()
    serializer_class = SeasonSerializer


class ColorViewSet(_SimpleCatalogViewSet):
    queryset = Color.objects.all()
    serializer_class = ColorSerializer


class SizeViewSet(_SimpleCatalogViewSet):
    queryset = Size.objects.all()
    serializer_class = SizeSerializer


class ProductViewSet(BusinessScopedViewSet):
    permission_classes = MANAGER_WRITE
    serializer_class = ProductSerializer
    queryset = Product.objects.select_related("category", "brand", "season")
    search_fields = ["name", "article", "variants__sku", "variants__barcode"]
    filterset_fields = ["category", "brand", "season", "is_active"]
    ordering_fields = ["name", "created_at", "sale_price"]

    def get_queryset(self):
        branches = _stock_branches(self.request)
        stock_sum = (
            Stock.objects.filter(variant__product=OuterRef("pk"), branch__in=branches)
            .values("variant__product").annotate(s=Sum("quantity")).values("s")
        )
        variant_stock = (
            Stock.objects.filter(variant=OuterRef("pk"), branch__in=branches)
            .values("variant").annotate(s=Sum("quantity")).values("s")
        )
        variants = ProductVariant.objects.select_related("color", "size", "product").annotate(
            stock=Coalesce(Subquery(variant_stock, output_field=IntegerField()), Value(0))
        )
        return (
            super().get_queryset()
            .annotate(total_stock=Coalesce(Subquery(stock_sum, output_field=IntegerField()), Value(0)))
            .prefetch_related(Prefetch("variants", queryset=variants))
            .distinct()
        )

    @action(detail=True, methods=["post"], url_path="generate-variants")
    def generate(self, request, pk=None):
        product = self.get_object()
        s = GenerateVariantsSerializer(data=request.data, context={"request": request})
        s.is_valid(raise_exception=True)
        created = generate_variants(product, s.validated_data["color_ids"], s.validated_data["size_ids"])
        return Response({"created": len(created)}, status=201)

    @action(detail=True, methods=["post", "delete"], parser_classes=[MultiPartParser],
            serializer_class=ProductImageSerializer)
    def image(self, request, pk=None):
        """POST: rasmni yuklash yoki almashtirish (multipart, maydon nomi `image`). DELETE: rasmni olib tashlash."""
        product = self.get_object()
        if request.method == "DELETE":
            remove_product_image(product)
        else:
            s = ProductImageSerializer(data=request.data)
            s.is_valid(raise_exception=True)
            set_product_image(product, s.validated_data["image"])
        return Response(ProductSerializer(self.get_queryset().get(pk=product.pk), context={"request": request}).data)

    def destroy(self, request, *args, **kwargs):
        return _destroy_response(delete_or_archive_product(self.get_object()))


class VariantViewSet(BusinessScopedViewSet):
    """Variantlar: kassada SKU, shtrix-kod yoki nom bo'yicha qidirish uchun."""

    permission_classes = MANAGER_WRITE
    serializer_class = VariantSerializer
    queryset = ProductVariant.objects.select_related("product", "color", "size")
    search_fields = ["sku", "barcode", "product__name", "product__article"]
    filterset_class = VariantFilter
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_queryset(self):
        branches = _stock_branches(self.request)
        return super().get_queryset().annotate(
            stock=Coalesce(Sum("stocks__quantity", filter=Q(stocks__branch__in=branches)), Value(0))
        )

    def destroy(self, request, *args, **kwargs):
        return _destroy_response(delete_or_archive_variant(self.get_object()))
