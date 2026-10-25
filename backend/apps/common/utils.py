import re

from django.core.exceptions import ValidationError

PHONE_RE = re.compile(r"^\+998\d{9}$")


def normalize_phone(raw: str) -> str:
    """'90 123-45-67', '998901234567', '+998 90 123 45 67' -> '+998901234567'."""
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 9:
        digits = "998" + digits
    phone = "+" + digits
    if not PHONE_RE.match(phone):
        raise ValidationError("Telefon raqami +998XXXXXXXXX ko'rinishida bo'lishi kerak.")
    return phone
