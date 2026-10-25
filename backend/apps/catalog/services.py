import re

from django.db import transaction

from .models import ProductVariant


def _code(text: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", text.upper())[:6] or "X"


def build_sku(product, color, size) -> str:
    return f"{_code(product.article)}-{color.code.upper() if color.code else _code(color.name)}-{_code(size.name)}"


@transaction.atomic
def generate_variants(product, colors, sizes):
    """Rang × o'lcham matritsasidan yetishmayotgan variantlarni yaratadi. Mavjudlariga tegmaydi."""
    existing = set(product.variants.values_list("color_id", "size_id"))
    used_skus = set(ProductVariant.objects.filter(business=product.business).values_list("sku", flat=True))
    created = []
    for color in colors:
        for size in sizes:
            if (color.id, size.id) in existing:
                continue
            sku = base = build_sku(product, color, size)
            n = 2
            while sku in used_skus:
                sku = f"{base}-{n}"
                n += 1
            used_skus.add(sku)
            created.append(ProductVariant(business=product.business, product=product, color=color, size=size, sku=sku))
    ProductVariant.objects.bulk_create(created)
    return created
