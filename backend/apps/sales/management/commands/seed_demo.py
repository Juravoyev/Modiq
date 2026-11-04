"""Taqdimot uchun namuna do'kon: filiallar, xodimlar, tovarlar, kirim, ko'chirish, 30 kunlik savdo va qaytarishlar.

Barcha qoldiq o'zgarishlari haqiqiy servislar orqali o'tadi, shuning uchun jurnal va qoldiqlar to'g'ri bo'ladi.
Tovar rasmlari Unsplash'dan yuklanadi (bepul Unsplash litsenziyasi) va backend/.cache/demo-images ga saqlanadi:
keyingi safar internet kerak emas. Internet bo'lmasa, demo rasmsiz yaratiladi.
Ishlatish: python manage.py seed_demo [--reset] [--no-images]
"""
import random
import urllib.error
import urllib.request
import uuid
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Branch, Business, Membership, User
from apps.catalog.models import Brand, Category, Color, Product, Season, Size
from apps.catalog.services import generate_variants, set_product_image
from apps.inventory.models import Receipt, ReceiptLine, Stock, StockMovement, Transfer, TransferLine
from apps.inventory.services import confirm_receipt, receive_transfer, send_transfer
from apps.customers.bonus import BONUS_HOLD
from apps.customers.models import BonusTransaction, Customer, CustomerGroup
from apps.pricing.models import Promotion
from apps.sales.models import Sale, SaleReturn
from apps.sales.services import LineInput, ReturnLineInput, create_return, create_sale

PASSWORD = "Demo-12345"
OWNER_PHONE = "+998900000001"
STAFF = [
    # telefon, ism, rol, filiallar, qaytarishni tasdiqlay oladimi
    (OWNER_PHONE, "Jasur Karimov", Membership.Role.OWNER, [], False),
    ("+998900000002", "Dilnoza Rahimova", Membership.Role.MANAGER, [], False),
    ("+998900000003", "Aziz Tursunov", Membership.Role.CASHIER, ["Chilonzor do'koni"], False),
    ("+998900000004", "Malika Yusupova", Membership.Role.CASHIER, ["Yunusobod do'koni"], True),
]
BRANCHES = [
    ("Chilonzor do'koni", Branch.Kind.STORE, "Chilonzor tumani, 9-kvartal"),
    ("Yunusobod do'koni", Branch.Kind.STORE, "Yunusobod tumani, Amir Temur ko'chasi"),
    ("Markaziy ombor", Branch.Kind.WAREHOUSE, "Sergeli tumani"),
]
COLORS = [("Qora", "BLK", "#1f2937"), ("Oq", "WHT", "#f9fafb"), ("Ko'k", "BLU", "#1d4ed8"),
          ("Kulrang", "GRY", "#9ca3af"), ("Bej", "BEJ", "#d6c4a8")]
SIZES = [("S", 1), ("M", 2), ("L", 3), ("XL", 4), ("39", 10), ("40", 11), ("41", 12), ("42", 13), ("43", 14),
         ("Standart", 20)]
# nomi, artikul, kategoriya, brend, mavsum, xarid, sotuv, ranglar, o'lchamlar, kirim (har bir variant), sotiladimi
PRODUCTS = [
    ("Futbolka Basic", "FB01", "Futbolka", "Modiq Basic", "Butun yil", 45000, 99000,
     ["Qora", "Oq", "Kulrang"], ["S", "M", "L", "XL"], 14, True),
    ("Polo futbolka", "PL02", "Futbolka", "Urban", "Bahor-Yoz", 70000, 149000,
     ["Oq", "Ko'k"], ["M", "L", "XL"], 10, True),
    ("Klassik shim", "SH03", "Shim", "Comfort", "Butun yil", 120000, 249000,
     ["Qora", "Kulrang"], ["M", "L", "XL"], 8, True),
    ("Jinsi shim Slim", "JN04", "Shim", "Urban", "Butun yil", 150000, 299000,
     ["Ko'k", "Qora"], ["S", "M", "L"], 8, True),
    ("Oq ko'ylak", "KY05", "Ko'ylak", "Comfort", "Butun yil", 95000, 199000,
     ["Oq"], ["S", "M", "L", "XL"], 10, True),
    ("Krossovka Run", "KR06", "Oyoq kiyim", "Urban", "Bahor-Yoz", 260000, 499000,
     ["Oq", "Qora"], ["40", "41", "42", "43"], 5, True),
    ("Klassik tufli", "TF07", "Oyoq kiyim", "Comfort", "Butun yil", 300000, 590000,
     ["Qora"], ["40", "41", "42", "43"], 4, True),
    ("Charm sumka", "SM08", "Sumka", "Modiq Basic", "Butun yil", 180000, 390000,
     ["Qora", "Bej"], ["Standart"], 6, True),
    # Sotilmay turgan tovarlar: hisobotda "aksiya uchun nomzod" bo'lib chiqadi.
    ("Qishki kurtka Arctic", "QK09", "Kurtka", "Urban", "Kuz-Qish", 420000, 890000,
     ["Qora", "Bej"], ["M", "L", "XL"], 4, False),
    ("Jun sviter", "SV10", "Kurtka", "Comfort", "Kuz-Qish", 160000, 329000,
     ["Kulrang"], ["M", "L"], 5, False),
]


# Artikul -> Unsplash rasmi (photo-... identifikatori). Bepul Unsplash License: tijoriy foydalanish mumkin,
# muallifni ko'rsatish shart emas. Manba sahifalari: unsplash.com/photos/<id> (sharhda).
IMAGES = {
    "FB01": "1618354691373-d851c5c3a990",  # black-crew-neck-t-shirt-6Nub980bI3I
    "PL02": "1625910513394-ea511bed44ca",  # gray-polo-shirt-on-blue-textile-Y-00g_VgQTc
    "SH03": "1473966968600-fa801b869a1a",  # man wearing brown fitted pants
    "JN04": "1624378439575-d8705ad7ae80",  # blue denim jeans on white textile
    "KY05": "1579664531470-ac357f8f8e2b",  # white-dress-shirt-hanging-on-clothes-hanger-e8sbQNYEwX8
    "KR06": "1608229751021-ed4bd8677753",  # white-nike-athletic-shoes-on-white-background-A8HaTLON5Gg
    "TF07": "1668069226492-508742b03147",  # a pair of black shoes
    "SM08": "1691480250099-a63081ecfcb8",  # a-brown-leather-handbag-on-a-white-background-zxPo13geJ5U
    "QK09": "1769689387719-f11faac08cbe",  # man wearing a shiny black puffer jacket
    "SV10": "1574201635302-388dd92a4c3f",  # person-wearing-grey-knit-sweater-mU88MlEFcoU
}
IMAGE_URL = "https://images.unsplash.com/photo-{id}?fm=jpg&q=85&w=1200&h=1200&fit=crop"
IMAGE_CACHE = settings.BASE_DIR / ".cache" / "demo-images"

# telefon, ism, toifa (None — oddiy mijoz)
CUSTOMERS = [
    ("+998901234501", "Nodira Aliyeva", "VIP"),
    ("+998901234502", "Bekzod Qodirov", "Doimiy mijoz"),
    ("+998901234503", "Sardor Ergashev", "Doimiy mijoz"),
    ("+998901234504", "Gulnora Saidova", None),
    ("+998901234505", "Otabek Mirzayev", None),
    ("+998901234506", "Zarina Hamidova", "Xodim"),
]
GROUPS = [("Doimiy mijoz", 5), ("VIP", 10), ("Xodim", 15)]


def _at(day, hour, minute=0):
    return timezone.make_aware(datetime.combine(day, time(hour, minute)))


class Command(BaseCommand):
    help = "Taqdimot uchun namuna do'kon ma'lumotlarini yaratadi."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Avvalgi demo do'konni o'chirib, qaytadan yaratadi.")
        parser.add_argument("--no-images", action="store_true", help="Tovar rasmlarini yuklamaslik.")

    def handle(self, *args, reset=False, no_images=False, **options):
        # Rasmlar tranzaksiyadan oldin yuklanadi: tarmoq kutilayotganda baza qulflanib turmaydi.
        self.images = {} if no_images else self._load_images()
        existing = User.objects.filter(phone=OWNER_PHONE).select_related("membership__business").first()
        if existing:
            if not reset:
                raise CommandError("Demo do'kon allaqachon bor. Qaytadan yaratish uchun: seed_demo --reset")
            self._delete(existing)
        self.rng = random.Random(2026)
        with transaction.atomic():
            self._build()
        self.stdout.write(self.style.SUCCESS("Demo do'kon tayyor."))
        self.stdout.write(f"Parol (hammasi uchun): {PASSWORD}")
        for phone, name, role, _, _ in STAFF:
            self.stdout.write(f"  {phone}  {name}  ({Membership.Role(role).label})")

    def _load_images(self) -> dict[str, bytes]:
        """Artikul -> rasm baytlari. Avval keshdan, bo'lmasa internetdan. Yuklanmaganlari o'tkazib yuboriladi."""
        IMAGE_CACHE.mkdir(parents=True, exist_ok=True)
        result, failed = {}, []
        for article, photo_id in IMAGES.items():
            path = IMAGE_CACHE / f"{article}-{photo_id}.jpg"
            if not path.exists():
                try:
                    req = urllib.request.Request(IMAGE_URL.format(id=photo_id), headers={"User-Agent": "Modiq seed_demo"})
                    with urllib.request.urlopen(req, timeout=20) as res:
                        data = res.read()
                    if not data.startswith(b"\xff\xd8"):  # JPEG emas (masalan, xato sahifasi)
                        raise ValueError("rasm emas")
                    path.write_bytes(data)
                except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
                    failed.append(f"{article} ({e})")
                    continue
            result[article] = path.read_bytes()
        if failed:
            self.stdout.write(self.style.WARNING(
                "Ba'zi rasmlar yuklanmadi, tovarlar rasmsiz yaratiladi: " + ", ".join(failed)))
        self.stdout.write(f"Tovar rasmlari: {len(result)} / {len(IMAGES)}")
        return result

    @transaction.atomic
    def _delete(self, owner):
        business = owner.membership.business
        users = list(User.objects.filter(membership__business=business))
        # PROTECT bog'lanishlar sababli hujjatlar avval o'chiriladi.
        BonusTransaction.objects.filter(business=business).delete()
        SaleReturn.objects.filter(business=business).delete()
        Sale.objects.filter(business=business).delete()
        Promotion.objects.filter(business=business).delete()
        Customer.objects.filter(business=business).delete()
        Transfer.objects.filter(business=business).delete()
        Receipt.objects.filter(business=business).delete()
        Stock.objects.filter(business=business).delete()
        # Rasm fayllari ham o'chiriladi (aks holda har --reset da media/ papkasi to'lib boradi).
        storage = Product._meta.get_field("image").storage
        images = [n for n in Product.objects.filter(business=business).values_list("image", flat=True) if n]
        transaction.on_commit(lambda: [storage.delete(n) for n in images])
        Product.objects.filter(business=business).delete()
        business.delete()
        User.objects.filter(pk__in=[u.pk for u in users]).delete()
        self.stdout.write("Avvalgi demo do'kon o'chirildi.")

    def _build(self):
        business = Business.objects.create(name="Moda Uz", phone=OWNER_PHONE, address="Toshkent")
        self.branches = {name: Branch.objects.create(business=business, name=name, kind=kind, address=address)
                         for name, kind, address in BRANCHES}
        self.members = {}
        for phone, name, role, branch_names, can_approve in STAFF:
            user = User.objects.create_user(phone=phone, password=PASSWORD, full_name=name)
            m = Membership.objects.create(user=user, business=business, role=role, can_approve_returns=can_approve)
            m.branches.set([self.branches[b] for b in branch_names])
            self.members[role if role != Membership.Role.CASHIER else phone] = m
        owner = self.members[Membership.Role.OWNER]
        manager = self.members[Membership.Role.MANAGER]

        colors = {n: Color.objects.create(business=business, name=n, code=c, hex=h) for n, c, h in COLORS}
        sizes = {n: Size.objects.create(business=business, name=n, sort_order=o) for n, o in SIZES}
        categories, brands = {}, {}
        seasons = {
            "Bahor-Yoz": Season.objects.create(business=business, name="Bahor-Yoz", start_month=3, end_month=8),
            "Kuz-Qish": Season.objects.create(business=business, name="Kuz-Qish", start_month=9, end_month=2),
            "Butun yil": Season.objects.create(business=business, name="Butun yil", start_month=1, end_month=12),
        }

        today = timezone.localdate()
        start = today - timedelta(days=29)
        warehouse = self.branches["Markaziy ombor"]
        stores = [self.branches["Chilonzor do'koni"], self.branches["Yunusobod do'koni"]]

        self.sellable = []
        # Tovar savdolardan ancha oldin kelgan: sotilmagan kurtkalar tavsiyalarda "60 kundan beri sotilmagan" bo'ladi.
        received = start - timedelta(days=40)
        receipt = Receipt.objects.create(business=business, branch=warehouse, supplier_name="Toshkent Tekstil MChJ",
                                         document_number="TT-1024", document_date=received,
                                         created_by=owner.user)
        for (name, article, cat, brand, season, buy, sell, c_names, s_names, qty, sells) in PRODUCTS:
            if cat not in categories:
                categories[cat] = Category.objects.create(business=business, name=cat)
            if brand not in brands:
                brands[brand] = Brand.objects.create(business=business, name=brand)
            product = Product.objects.create(
                business=business, name=name, article=article, category=categories[cat], brand=brands[brand],
                season=seasons[season], purchase_price=Decimal(buy), sale_price=Decimal(sell), min_stock=2,
            )
            if article in self.images:
                set_product_image(product, ContentFile(self.images[article], name=f"{article}.jpg"))
            variants = generate_variants(product, [colors[c] for c in c_names], [sizes[s] for s in s_names])
            for v in variants:
                ReceiptLine.objects.create(receipt=receipt, variant=v, quantity=qty * 3, purchase_price=Decimal(buy))
            if sells:
                self.sellable.extend(variants)
        confirm_receipt(receipt.pk, owner.user)

        # Ombordan do'konlarga: har bir variantning uchdan biri har bir do'konga, qolgani omborda.
        for store in stores:
            t = Transfer.objects.create(business=business, from_branch=warehouse, to_branch=store,
                                        note="Boshlang'ich tovar", created_by=manager.user)
            for line in receipt.lines.all():
                TransferLine.objects.create(transfer=t, variant=line.variant, quantity=line.quantity // 3)
            send_transfer(t.pk, manager.user)
            receive_transfer(t.pk, manager.user)
            Transfer.objects.filter(pk=t.pk).update(created_at=_at(start - timedelta(days=1), 10),
                                                    sent_at=_at(start - timedelta(days=1), 11),
                                                    received_at=_at(start - timedelta(days=1), 15))
        Receipt.objects.filter(pk=receipt.pk).update(created_at=_at(received, 9), confirmed_at=_at(received, 12))
        # Ombor jurnali ham hujjat sanasiga ko'chadi (tavsiyalar tovar omborda qancha turganini shundan oladi).
        StockMovement.objects.filter(ref_type="receipt", ref_id=receipt.pk).update(created_at=_at(received, 12))
        StockMovement.objects.filter(business=business, ref_type="transfer").update(
            created_at=_at(start - timedelta(days=1), 15))

        groups = {n: CustomerGroup.objects.create(business=business, name=n, discount_percent=p) for n, p in GROUPS}
        self.customers = [Customer.objects.create(business=business, phone=ph, full_name=nm,
                                                  group=groups[g] if g else None) for ph, nm, g in CUSTOMERS]

        # 30 kunlik savdo. Dam olish kunlari savdo ko'proq.
        cashiers = {stores[0]: self.members["+998900000003"], stores[1]: self.members["+998900000004"]}
        n_sales = 0
        for offset in range(30):
            day = start + timedelta(days=offset)
            per_store = self.rng.randint(2, 4) + (2 if day.weekday() >= 5 else 0)
            for store in stores:
                for _ in range(per_store if day < today else 2):
                    sale = self._random_sale(business, store, cashiers[store], day)
                    if sale and day < today:
                        hour, minute = self.rng.randint(10, 20), self.rng.randint(0, 59)
                        when = _at(day, hour, minute)
                        Sale.objects.filter(pk=sale.pk).update(created_at=when)
                        StockMovement.objects.filter(ref_type="sale", ref_id=sale.pk).update(created_at=when)
                        # Bonus ham savdo vaqtiga ko'chadi: o'tgan kunlardagi bonus allaqachon ishlatish mumkin.
                        BonusTransaction.objects.filter(sale=sale).update(created_at=when,
                                                                          available_at=when + BONUS_HOLD)
                    n_sales += bool(sale)

        # Qaytarishlar bugungi savdolar ustida (24 soatlik muddat ichida):
        # biri menejer tomonidan darhol bajarilgan, biri huquqi yo'q sotuvchining kutilayotgan so'rovi.
        todays = Sale.objects.filter(business=business, created_at__date=today).prefetch_related("lines")
        by_store = {store: [s for s in todays if s.branch_id == store.id] for store in stores}
        if by_store[stores[1]]:
            sale = by_store[stores[1]][0]
            create_return(sale=sale, user=manager.user, membership=manager,
                          lines=[ReturnLineInput(sale.lines.first(), 1)], reason="Tikuvi so'kilgan")
        if by_store[stores[0]]:
            sale = by_store[stores[0]][0]
            cashier = cashiers[stores[0]]
            create_return(sale=sale, user=cashier.user, membership=cashier,
                          lines=[ReturnLineInput(sale.lines.first(), 1)], reason="Matoda dog' bor")

        # Demo davomida ko'rsatish uchun: yo'ldagi ko'chirish va qoralama kirim.
        t = Transfer.objects.create(business=business, from_branch=warehouse, to_branch=stores[1],
                                    note="Qo'shimcha futbolkalar", created_by=manager.user)
        for v in self.sellable[:3]:
            TransferLine.objects.create(transfer=t, variant=v, quantity=3)
        send_transfer(t.pk, manager.user)
        draft = Receipt.objects.create(business=business, branch=warehouse, supplier_name="Urban Style",
                                       document_number="US-77", document_date=today, created_by=manager.user)
        for v in self.sellable[-4:]:
            ReceiptLine.objects.create(receipt=draft, variant=v, quantity=5, purchase_price=v.effective_purchase_price)
        # Aksiyalar savdolardan keyin yaratiladi: o'tgan kunlardagi savdolarga ta'sir qilmaydi.
        # Mavsumiy aksiyani taqdimotda "Tavsiyalar" sahifasidan yaratish ko'rsatiladi.
        Promotion.objects.create(business=business, name="Futbolka haftaligi", kind=Promotion.Kind.PERCENT,
                                 value=Decimal(10), scope=Promotion.Scope.CATEGORY, category=categories["Futbolka"],
                                 starts_on=today - timedelta(days=2), ends_on=today + timedelta(days=5),
                                 created_by=manager.user)
        new_year = date(today.year, 12, 25) if today < date(today.year, 12, 25) else date(today.year + 1, 12, 25)
        Promotion.objects.create(business=business, name="Yangi yil", kind=Promotion.Kind.PERCENT, value=Decimal(15),
                                 scope=Promotion.Scope.ALL, starts_on=new_year,
                                 ends_on=date(new_year.year + 1, 1, 5), created_by=owner.user)
        self.stdout.write(f"{len(PRODUCTS)} ta tovar, {n_sales} ta savdo yaratildi.")

    def _random_sale(self, business, store, cashier, day):
        stock = {s.variant_id: s.quantity for s in Stock.objects.filter(branch=store, quantity__gt=0)}
        candidates = [v for v in self.sellable if stock.get(v.id, 0) > 0]
        if not candidates:
            return None
        lines = []
        for v in self.rng.sample(candidates, k=min(len(candidates), self.rng.choice([1, 1, 1, 2, 2, 3]))):
            qty = min(stock[v.id], self.rng.choice([1, 1, 1, 2]))
            # Ba'zan sotuvchi kichik chegirma beradi (yaxlitlash uchun), 10% chegarasidan oshmaydi.
            limit = (v.effective_sale_price * qty / 10 // 1000) * 1000
            discount = min(Decimal(self.rng.choice([0, 0, 0, 0, 5000, 10000])), limit) if qty else Decimal(0)
            lines.append(LineInput(v, qty, discount))
        sale, _ = create_sale(
            business=business, branch=store, user=cashier.user, membership=cashier, lines=lines,
            payment_type=self.rng.choice([Sale.PaymentType.CASH] * 3 + [Sale.PaymentType.CARD] * 2
                                         + [Sale.PaymentType.ONLINE]),
            idempotency_key=uuid.uuid4(),
            # Har uchinchi xaridor o'zini tanishtiradi (telefon raqami bilan).
            customer=self.rng.choice(self.customers) if self.rng.random() < 0.35 else None,
        )
        return sale
