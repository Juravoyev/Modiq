import re
from io import BytesIO

from django.core.files.base import ContentFile
from django.db import transaction
from PIL import Image, ImageOps, UnidentifiedImageError
from rest_framework.exceptions import ValidationError

from .models import Product, ProductVariant


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


def _variant_ids_with_history(variant_ids):
    """Ombor harakati, kirim, ko'chirish yoki savdoda ishtirok etgan variantlar."""
    from apps.inventory.models import ReceiptLine, StockMovement, TransferLine
    from apps.sales.models import SaleLine

    used = set()
    for model in (StockMovement, ReceiptLine, TransferLine, SaleLine):
        used.update(model.objects.filter(variant_id__in=variant_ids).values_list("variant_id", flat=True))
    return used


@transaction.atomic
def delete_or_archive_variant(variant) -> bool:
    """Tarixi yo'q variant o'chiriladi, tarixi bor variant arxivlanadi. Arxivlangan bo'lsa True."""
    if _variant_ids_with_history([variant.id]):
        variant.is_active = False
        variant.save(update_fields=["is_active", "updated_at"])
        return True
    variant.delete()
    return False


@transaction.atomic
def delete_or_archive_product(product) -> bool:
    """Birorta varianti tarixga ega bo'lsa, tovar arxivlanadi (hisobotlar uchun). Aks holda o'chiriladi."""
    product = Product.objects.select_for_update().get(pk=product.pk)
    if _variant_ids_with_history(list(product.variants.values_list("id", flat=True))):
        product.is_active = False
        product.save(update_fields=["is_active", "updated_at"])
        return True
    old_image = product.image.name
    product.delete()
    _delete_file_on_commit(old_image)
    return False


IMAGE_MAX_UPLOAD_BYTES = 10 * 1024 * 1024
IMAGE_MAX_SIDE = 1200
IMAGE_QUALITY = 80


def _delete_file_on_commit(name):
    # Fayl tranzaksiya muvaffaqiyatli tugagandan keyingina o'chiriladi: xato bo'lsa rasm yo'qolib qolmaydi.
    if name:
        storage = Product._meta.get_field("image").storage
        transaction.on_commit(lambda: storage.delete(name))


def _compress_image(uploaded) -> ContentFile:
    """Rasmni eng katta tomoni IMAGE_MAX_SIDE bo'lguncha kichraytirib, WebP formatida siqadi."""
    if uploaded.size > IMAGE_MAX_UPLOAD_BYTES:
        raise ValidationError({"image": "Rasm hajmi 10 MB dan oshmasligi kerak."})
    try:
        img = Image.open(uploaded)
        img.load()
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError):
        raise ValidationError({"image": "Fayl rasm emas yoki shikastlangan. JPG, PNG yoki WebP yuklang."})
    img = ImageOps.exif_transpose(img)  # telefonda olingan rasm yonboshlab qolmasligi uchun
    img = img.convert("RGBA" if "A" in img.getbands() or "transparency" in img.info else "RGB")
    img.thumbnail((IMAGE_MAX_SIDE, IMAGE_MAX_SIDE))
    out = BytesIO()
    img.save(out, format="WEBP", quality=IMAGE_QUALITY, method=6)
    return ContentFile(out.getvalue())


@transaction.atomic
def set_product_image(product, uploaded):
    content = _compress_image(uploaded)
    product = Product.objects.select_for_update().get(pk=product.pk)
    old_image = product.image.name
    product.image.save("image.webp", content, save=False)
    product.save(update_fields=["image", "updated_at"])
    _delete_file_on_commit(old_image)
    return product


@transaction.atomic
def remove_product_image(product):
    product = Product.objects.select_for_update().get(pk=product.pk)
    old_image = product.image.name
    product.image = None
    product.save(update_fields=["image", "updated_at"])
    _delete_file_on_commit(old_image)
    return product
