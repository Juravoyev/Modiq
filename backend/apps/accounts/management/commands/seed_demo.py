"""Sinov uchun namunaviy do'kon: python manage.py seed_demo [--reset]

Barcha ma'lumotlar o'ylab topilgan (demo). Real do'kon ma'lumoti sifatida ishlatmang.
Qoldiq, savdo va qaytarishlar oddiy servislar orqali yaratiladi, shuning uchun qoldiq jurnali bilan mos keladi.
Sanalar o'tgan 100 kunga tarqatiladi, shunda "Aqlli tavsiyalar" va dashboard haqiqiy ko'rinishda ishlaydi.
"""
import random
import uuid
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Branch, Business, Membership, User
from apps.catalog.models import Brand, Category, Color, Product, ProductVariant, Season, Size
from apps.catalog.services import generate_variants
from apps.discounts import services as disc
from apps.discounts.models import Discount
from apps.inventory import services as inv
from apps.inventory.models import Receipt, ReceiptLine, Stock, StockCount, StockMovement, Transfer, TransferLine
from apps.sales.models import Sale, SaleReturn
from apps.sales.services import LineInput, create_sale, return_sale_items

OWNER_PHONE = "+998900000001"
CASHIER_PHONE = "+998900000002"
PASSWORD = "Demo-parol-2026"
DEMO_NAME = "Modiq Demo do'koni"
# seed_demo va seed_presentation bir xil telefon raqamlardan foydalanadi: --reset ikkalasining do'konini ham o'chiradi.
DEMO_NAMES = (DEMO_NAME, "Moda Uz")

# (nom, artikul, kategoriya, brend, mavsum, xarid, sotuv, ranglar, o'lchamlar, kirim har variantga, mashhurlik 0..1)
PRODUCTS = [
    ("Futbolka Basic", "FB01", "Futbolka", "Basic Line", "Yoz", 45000, 99000, ["Qora", "Oq", "Kulrang"], ["S", "M", "L", "XL"], 8, 0.9),
    ("Polo futbolka", "PL02", "Futbolka", "Classic Wear", "Yoz", 70000, 149000, ["Oq", "Ko'k"], ["M", "L", "XL"], 6, 0.35),
    ("Jinsi shim Slim", "JS10", "Shim", "Urban Style", None, 120000, 249000, ["Ko'k", "Qora"], ["30", "32", "34", "36"], 6, 0.6),
    ("Klassik shim", "KS11", "Shim", "Classic Wear", None, 110000, 229000, ["Qora", "Kulrang"], ["30", "32", "34"], 30, 0.5),
    ("Ko'ylak Oxford", "KO20", "Ko'ylak", "Classic Wear", None, 95000, 199000, ["Oq", "Ko'k"], ["S", "M", "L", "XL"], 5, 0.45),
    ("Kuzgi kurtka", "KK30", "Kurtka", "Urban Style", "Kuz", 280000, 549000, ["Qora", "Bej"], ["M", "L", "XL"], 6, 0.4),
    ("Qishki kurtka", "QK31", "Kurtka", "Urban Style", "Qish", 420000, 849000, ["Qora", "Kulrang"], ["M", "L", "XL"], 4, 0.15),
    ("Yozgi shorti", "YS40", "Shim", "Basic Line", "Yoz", 55000, 119000, ["Bej", "Ko'k"], ["M", "L"], 12, 0.05),
    ("Krossovka Run", "KR50", "Oyoq kiyim", "Urban Style", None, 260000, 499000, ["Oq", "Qora"], ["40", "41", "42", "43"], 4, 0.55),
    ("Klassik tufli", "KT51", "Oyoq kiyim", "Classic Wear", None, 300000, 599000, ["Qora"], ["40", "41", "42", "43"], 3, 0.1),
    ("Ayollar sumkasi", "AS60", "Sumka", "Classic Wear", None, 180000, 359000, ["Qora", "Bej", "Qizil"], ["Standart"], 4, 0.3),
    ("Hoodie Oversize", "HO70", "Kofta", "Urban Style", "Kuz", 150000, 299000, ["Qora", "Kulrang"], ["S", "M", "L", "XL"], 5, 0.7),
    ("Sviter jun", "SV71", "Kofta", "Classic Wear", "Qish", 140000, 279000, ["Kulrang", "Jigarrang"], ["M", "L", "XL"], 5, 0.3),
    ("Ayollar ko'ylagi", "AP80", "Ayollar kiyimi", "Moda Line", "Yoz", 160000, 329000, ["Qizil", "Qora", "Yashil"], ["S", "M", "L"], 5, 0.6),
    ("Yubka midi", "YM81", "Ayollar kiyimi", "Moda Line", None, 90000, 189000, ["Qora", "Bej"], ["S", "M", "L"], 5, 0.4),
    ("Ayollar tuflisi", "AT52", "Oyoq kiyim", "Moda Line", None, 200000, 399000, ["Qora", "Bej"], ["36", "37", "38", "39"], 3, 0.45),
    ("Qishki botinka", "QB53", "Oyoq kiyim", "Urban Style", "Qish", 320000, 649000, ["Qora", "Jigarrang"], ["41", "42", "43"], 3, 0.12),
    ("Ryukzak City", "RC61", "Sumka", "Urban Style", None, 150000, 299000, ["Qora", "Kulrang"], ["Standart"], 6, 0.5),
    ("Charm hamyon", "CH62", "Aksessuar", "Classic Wear", None, 70000, 149000, ["Qora", "Jigarrang"], ["Standart"], 8, 0.35),
    ("Kepka", "KP90", "Aksessuar", "Basic Line", "Yoz", 30000, 69000, ["Qora", "Oq", "Ko'k"], ["Standart"], 10, 0.5),
]


def _shift(qs, days_ago, rnd):
    if days_ago == 0:
        # Bugungi savdolar: bugun ichida qoladigan vaqt (dashboard "bugun" ko'rsatkichlari uchun)
        local_now = timezone.localtime()
        elapsed = int((local_now - local_now.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds() // 60)
        when = timezone.now() - timedelta(minutes=rnd.randint(0, max(0, elapsed - 1)))
    else:
        when = timezone.now() - timedelta(days=days_ago, hours=rnd.randint(0, 9), minutes=rnd.randint(0, 59))
    qs.update(created_at=when)
    return when


@transaction.atomic
def delete_demo_business(biz):
    """Demo do'konni o'chiradi. Demo bo'lmagan biznesga tegmaydi."""
    if biz.name not in DEMO_NAMES:
        raise CommandError(f"{OWNER_PHONE} demo bo'lmagan biznesga tegishli, hech narsa o'chirilmadi.")
    # PROTECT bog'lanishlar sababli tartib bilan o'chiriladi. Faqat demo biznes ma'lumotlari.
    SaleReturn.objects.filter(business=biz).delete()
    Sale.objects.filter(business=biz).delete()
    Discount.objects.filter(business=biz).delete()
    Receipt.objects.filter(business=biz).delete()
    Transfer.objects.filter(business=biz).delete()
    StockCount.objects.filter(business=biz).delete()
    StockMovement.objects.filter(business=biz).delete()
    Stock.objects.filter(business=biz).delete()
    ProductVariant.objects.filter(business=biz).delete()
    Product.objects.filter(business=biz).delete()
    for model in (Color, Size, Category, Brand, Season):
        model.objects.filter(business=biz).delete()
    User.objects.filter(membership__business=biz).delete()
    biz.delete()


class Command(BaseCommand):
    help = "Namunaviy (demo) do'kon ma'lumotlarini yaratadi."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Avvalgi DEMO do'konni o'chirib, qaytadan yaratadi")

    def handle(self, *args, **opts):
        existing = User.objects.filter(phone=OWNER_PHONE).first()
        if existing:
            if not opts["reset"]:
                raise CommandError("Demo do'kon allaqachon bor. Qaytadan yaratish uchun: python manage.py seed_demo --reset")
            delete_demo_business(existing.membership.business)
        rnd = random.Random(42)
        with transaction.atomic():
            self._create(rnd)
        self.stdout.write(self.style.SUCCESS("Demo do'kon yaratildi."))
        self.stdout.write(f"  Egasi:    {OWNER_PHONE} / {PASSWORD}")
        self.stdout.write(f"  Sotuvchi: {CASHIER_PHONE} / {PASSWORD}")

    def _create(self, rnd):
        biz = Business.objects.create(name=DEMO_NAME, phone=OWNER_PHONE, address="Toshkent (demo)")
        store1 = Branch.objects.create(business=biz, name="Chilonzor do'koni")
        store2 = Branch.objects.create(business=biz, name="Yunusobod do'koni")
        warehouse = Branch.objects.create(business=biz, name="Markaziy ombor", kind=Branch.Kind.WAREHOUSE)
        owner = User.objects.create_user(phone=OWNER_PHONE, password=PASSWORD, full_name="Demo Egasi")
        owner_m = Membership.objects.create(user=owner, business=biz, role=Membership.Role.OWNER)
        cashier = User.objects.create_user(phone=CASHIER_PHONE, password=PASSWORD, full_name="Demo Sotuvchi")
        cashier_m = Membership.objects.create(user=cashier, business=biz, role=Membership.Role.CASHIER)
        cashier_m.branches.set([store1])

        seasons = {n: Season.objects.create(business=biz, name=n, start_month=a, end_month=b)
                   for n, a, b in [("Bahor", 3, 5), ("Yoz", 6, 8), ("Kuz", 9, 11), ("Qish", 12, 2)]}
        colors = {n: Color.objects.create(business=biz, name=n, code=c) for n, c in
                  [("Qora", "BLK"), ("Oq", "WHT"), ("Kulrang", "GRY"), ("Ko'k", "BLU"), ("Bej", "BEG"), ("Qizil", "RED"),
                   ("Yashil", "GRN"), ("Jigarrang", "BRN")]}
        size_names = ["S", "M", "L", "XL", "30", "32", "34", "36", "37", "38", "39", "40", "41", "42", "43", "Standart"]
        sizes = {n: Size.objects.create(business=biz, name=n, sort_order=i) for i, n in enumerate(size_names)}
        cats, brands = {}, {}

        catalog = []
        for name, art, cat, brand, season, buy, sell, cols, szs, qty, pop in PRODUCTS:
            if cat not in cats:
                cats[cat] = Category.objects.create(business=biz, name=cat)
            if brand not in brands:
                brands[brand] = Brand.objects.create(business=biz, name=brand)
            p = Product.objects.create(
                business=biz, name=name, article=art, category=cats[cat], brand=brands[brand],
                season=seasons.get(season) if season else None, purchase_price=Decimal(buy), sale_price=Decimal(sell),
                min_stock=2,
            )
            generate_variants(p, [colors[c] for c in cols], [sizes[s] for s in szs])
            catalog.append((p, qty, pop))

        # 1) ~100 kun oldin ikkala do'konga va omborga kirim
        for branch, factor in ((store1, 1.0), (store2, 0.7), (warehouse, 1.5)):
            receipt = Receipt.objects.create(business=biz, branch=branch, supplier_name="Demo Tekstil MChJ",
                                             document_number=f"DM-{branch.id}-001",
                                             document_date=timezone.localdate() - timedelta(days=100), created_by=owner)
            for p, qty, _ in catalog:
                for v in p.variants.all():
                    ReceiptLine.objects.create(receipt=receipt, variant=v, quantity=max(1, round(qty * factor)),
                                               purchase_price=p.purchase_price)
            inv.confirm_receipt(receipt.id, owner)
            _shift(StockMovement.objects.filter(ref_type="receipt", ref_id=receipt.id), 100, rnd)

        # 2) 90 kunlik savdolar. 45-kunda mashhur tovarlar do'konlarga qayta keltiriladi.: mashhur tovarlar tez-tez, ba'zilari umuman sotilmaydi
        for day in range(90, -1, -1):
            if day == 45:
                for branch in (store1, store2):
                    receipt = Receipt.objects.create(business=biz, branch=branch, supplier_name="Demo Tekstil MChJ",
                                                     document_number=f"DM-{branch.id}-002",
                                                     document_date=timezone.localdate() - timedelta(days=45),
                                                     created_by=owner)
                    for p, qty, pop in catalog:
                        if pop >= 0.5 and p.article != "KS11":
                            for v in p.variants.all():
                                ReceiptLine.objects.create(receipt=receipt, variant=v, quantity=qty,
                                                           purchase_price=p.purchase_price)
                    inv.confirm_receipt(receipt.id, owner)
                    _shift(StockMovement.objects.filter(ref_type="receipt", ref_id=receipt.id), 45, rnd)
            for branch, traffic in ((store1, 20), (store2, 13)):
                for _ in range(rnd.randint(traffic // 2, traffic)):
                    p, _, pop = rnd.choice(catalog)
                    if rnd.random() > pop:
                        continue
                    # Shorti va tufli 60 kundan beri sotilmaydi: sotilmay qolish xavfi namunasi
                    if p.article in ("YS40", "KT51") and day < 60:
                        continue
                    options = list(Stock.objects.filter(branch=branch, variant__product=p, quantity__gt=0)
                                   .select_related("variant__size", "variant__product"))
                    if not options:
                        continue
                    # O'rta o'lchamlar (M, L, 32, 41, 42) ko'proq sotiladi
                    weights = [3 if o.variant.size.name in ("M", "L", "32", "41", "42") else 1 for o in options]
                    stock = rnd.choices(options, weights)[0]
                    discount = Decimal(rnd.choice([0, 0, 0, 0, 10000, 20000]))
                    sale, _ = create_sale(
                        business=biz, branch=branch, user=cashier if branch == store1 else owner,
                        membership=cashier_m if branch == store1 else owner_m,
                        lines=[LineInput(stock.variant, 1, min(discount, stock.variant.effective_sale_price))],
                        payment_type=rnd.choice(["cash", "cash", "card", "online"]), idempotency_key=uuid.uuid4(),
                    )
                    when = _shift(Sale.objects.filter(pk=sale.pk), day, rnd)
                    StockMovement.objects.filter(ref_type="sale", ref_id=sale.pk).update(created_at=when)

        # 3) Bir nechta qaytarish va ombordan do'konga ko'chirish
        for sale in Sale.objects.filter(business=biz).order_by("?")[:4]:
            line = sale.lines.first()
            ret = return_sale_items(sale_id=sale.id, user=owner, membership=owner_m, items=[(line.id, 1)],
                                   reason="O'lcham to'g'ri kelmadi")
            when = sale.created_at + timedelta(days=1)
            SaleReturn.objects.filter(pk=ret.pk).update(created_at=when)
            StockMovement.objects.filter(ref_type="salereturn", ref_id=ret.pk).update(created_at=when)

        hoodie = next(p for p, _, _ in catalog if p.article == "HO70")
        transfer = Transfer.objects.create(business=biz, from_branch=warehouse, to_branch=store1, created_by=owner,
                                           note="Hoodie ko'p sotilyapti")
        for v in hoodie.variants.all()[:4]:
            TransferLine.objects.create(transfer=transfer, variant=v, quantity=3)
        inv.send_transfer(transfer.id, owner)
        inv.receive_transfer(transfer.id, owner)
        Transfer.objects.create(business=biz, from_branch=warehouse, to_branch=store2, created_by=owner,
                                note="Qoralama: krossovkalar")

        # 4) Chegirmalar: ortiqcha zaxiradagi shimga tasdiqlangan -20%, shortiga tannarxdan past qoralama
        today = timezone.localdate()
        trousers = next(p for p, _, _ in catalog if p.article == "KS11").variants.first()
        promo = disc.create_discount(business=biz, user=owner, variant=trousers, kind=Discount.Kind.PERCENT,
                                     value=Decimal("20"), starts_on=today, ends_on=today + timedelta(days=13),
                                     note="Ortiqcha zaxira")
        disc.approve_discount(promo.id, user=owner, membership=owner_m)
        shorts = next(p for p, _, _ in catalog if p.article == "YS40").variants.first()
        disc.create_discount(business=biz, user=owner, variant=shorts, kind=Discount.Kind.FIXED_PRICE,
                             value=Decimal("49000"), starts_on=today, ends_on=today + timedelta(days=6),
                             note="Mavsum oxiri, tannarxdan past")
