import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q

from apps.common.models import BusinessOwnedModel

MONEY = {"max_digits": 14, "decimal_places": 2}


def _unique_name(model_name):
    return models.UniqueConstraint(fields=["business", "name"], name=f"uniq_{model_name}_name_per_business")


def product_image_path(instance, filename):
    # Har bir yuklashda yangi nom: brauzer keshi eski rasmni ko'rsatib qolmaydi.
    return f"products/{instance.business_id}/{uuid.uuid4().hex}.webp"


class Category(BusinessOwnedModel):
    name = models.CharField(max_length=100)

    class Meta:
        constraints = [_unique_name("category")]
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class Brand(BusinessOwnedModel):
    name = models.CharField(max_length=100)

    class Meta:
        constraints = [_unique_name("brand")]
        ordering = ["name"]

    def __str__(self):
        return self.name


class Season(BusinessOwnedModel):
    """Mavsum oylari. Qish kabi yil oshib o'tadigan mavsum ham bo'lishi mumkin (12 -> 2)."""

    name = models.CharField(max_length=50)
    start_month = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(12)])
    end_month = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(12)])

    class Meta:
        constraints = [
            _unique_name("season"),
            models.CheckConstraint(
                condition=Q(start_month__gte=1, start_month__lte=12, end_month__gte=1, end_month__lte=12),
                name="season_months_valid",
            ),
        ]
        ordering = ["start_month"]

    def __str__(self):
        return self.name


class Color(BusinessOwnedModel):
    name = models.CharField(max_length=50)
    code = models.CharField("SKU uchun qisqa kod", max_length=10, blank=True)
    hex = models.CharField(max_length=7, blank=True)

    class Meta:
        constraints = [_unique_name("color")]
        ordering = ["name"]

    def __str__(self):
        return self.name


class Size(BusinessOwnedModel):
    name = models.CharField(max_length=20)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        constraints = [_unique_name("size")]
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class Product(BusinessOwnedModel):
    """Model (masalan, "Futbolka Basic"). Qoldiq mahsulotda emas, variantlarda yuritiladi."""

    name = models.CharField(max_length=200)
    article = models.CharField("Artikul", max_length=50)
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL)
    brand = models.ForeignKey(Brand, null=True, blank=True, on_delete=models.SET_NULL)
    season = models.ForeignKey(Season, null=True, blank=True, on_delete=models.SET_NULL)
    purchase_price = models.DecimalField("Xarid narxi", **MONEY)
    sale_price = models.DecimalField("Sotuv narxi", **MONEY)
    min_stock = models.PositiveIntegerField("Minimal qoldiq (har bir variant uchun)", default=0)
    image = models.ImageField(upload_to=product_image_path, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["business", "article"], name="uniq_product_article_per_business"),
            models.CheckConstraint(condition=Q(purchase_price__gte=0, sale_price__gte=0),
                                   name="product_prices_non_negative"),
        ]
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.article})"


class ProductVariant(BusinessOwnedModel):
    """Rang × o'lcham kombinatsiyasi. Har bir variant alohida SKU va alohida qoldiqqa ega."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    color = models.ForeignKey(Color, on_delete=models.PROTECT)
    size = models.ForeignKey(Size, on_delete=models.PROTECT)
    sku = models.CharField(max_length=64)
    barcode = models.CharField(max_length=64, blank=True)
    # Bo'sh bo'lsa, mahsulot narxi ishlatiladi.
    purchase_price = models.DecimalField(null=True, blank=True, **MONEY)
    sale_price = models.DecimalField(null=True, blank=True, **MONEY)
    min_stock = models.PositiveIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["business", "sku"], name="uniq_variant_sku_per_business"),
            models.UniqueConstraint(fields=["product", "color", "size"], name="uniq_variant_color_size"),
            models.CheckConstraint(
                condition=(Q(purchase_price__isnull=True) | Q(purchase_price__gte=0))
                & (Q(sale_price__isnull=True) | Q(sale_price__gte=0)),
                name="variant_prices_non_negative",
            ),
        ]
        indexes = [models.Index(fields=["business", "barcode"])]
        ordering = ["product_id", "color__name", "size__sort_order"]

    @property
    def effective_purchase_price(self):
        return self.purchase_price if self.purchase_price is not None else self.product.purchase_price

    @property
    def effective_sale_price(self):
        return self.sale_price if self.sale_price is not None else self.product.sale_price

    @property
    def effective_min_stock(self):
        return self.min_stock if self.min_stock is not None else self.product.min_stock

    def __str__(self):
        return f"{self.product.name} / {self.color.name} / {self.size.name}"
