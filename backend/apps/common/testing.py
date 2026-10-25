"""Testlar uchun yordamchi: biznes, filial, tovar va variantlarni tez yaratish."""
from decimal import Decimal

from django.db import transaction
from rest_framework.test import APIClient

from apps.accounts.models import Branch, Business, Membership, User
from apps.catalog.models import Color, Product, ProductVariant, Size
from apps.inventory.models import Stock, StockMovement
from apps.inventory.services import change_stock

_counter = {"n": 0}


def _next():
    _counter["n"] += 1
    return _counter["n"]


def make_business(name="Do'kon", branches=("Markaz",)):
    n = _next()
    business = Business.objects.create(name=f"{name} {n}")
    created = [Branch.objects.create(business=business, name=b) for b in branches]
    owner = User.objects.create_user(phone=f"+99890{n:07d}", password="Parol-12345")
    membership = Membership.objects.create(user=owner, business=business, role=Membership.Role.OWNER)
    return business, created, owner, membership


def make_member(business, role, branches=()):
    n = _next()
    user = User.objects.create_user(phone=f"+99891{n:07d}", password="Parol-12345")
    m = Membership.objects.create(user=user, business=business, role=role)
    m.branches.set(branches)
    return user, m


def make_variant(business, purchase="50000", sale="100000", color="Qora", size="M", article=None):
    color_obj, _ = Color.objects.get_or_create(business=business, name=color)
    size_obj, _ = Size.objects.get_or_create(business=business, name=size)
    article = article or f"ART{_next()}"
    product, _ = Product.objects.get_or_create(
        business=business, article=article,
        defaults={"name": f"Futbolka {article}", "purchase_price": Decimal(purchase), "sale_price": Decimal(sale)},
    )
    return ProductVariant.objects.create(business=business, product=product, color=color_obj, size=size_obj,
                                         sku=f"{article}-{color}-{size}")


def put_stock(branch, variant, qty):
    with transaction.atomic():
        change_stock(business=branch.business, branch=branch, variant=variant, delta=qty,
                     kind=StockMovement.Kind.ADJUSTMENT)


def stock_of(branch, variant):
    s = Stock.objects.filter(branch=branch, variant=variant).first()
    return s.quantity if s else 0


def client_for(user):
    c = APIClient()
    c.force_authenticate(user)
    return c
