from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel
from apps.common.utils import normalize_phone


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, phone, password, **extra):
        if not phone:
            raise ValueError("Telefon raqami majburiy.")
        user = self.model(phone=normalize_phone(phone), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, phone, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create_user(phone, password, **extra)

    def create_superuser(self, phone, password=None, **extra):
        extra["is_staff"] = True
        extra["is_superuser"] = True
        return self._create_user(phone, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    """Telefon raqami + parol orqali kiradigan foydalanuvchi. Parol Django hasher bilan saqlanadi."""

    phone = models.CharField("Telefon", max_length=13, unique=True)
    full_name = models.CharField("F.I.Sh.", max_length=150, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.phone


class Business(TimeStampedModel):
    """Tenant: bitta mijoz biznesi (bir yoki bir nechta do'kon)."""

    name = models.CharField("Do'kon nomi", max_length=150)
    phone = models.CharField(max_length=13, blank=True)
    address = models.CharField(max_length=255, blank=True)
    currency = models.CharField(max_length=3, default="UZS")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Branch(TimeStampedModel):
    class Kind(models.TextChoices):
        STORE = "store", "Do'kon"
        WAREHOUSE = "warehouse", "Ombor"

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="branches")
    name = models.CharField(max_length=150)
    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.STORE)
    address = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["business", "name"], name="uniq_branch_name_per_business"),
        ]
        ordering = ["id"]

    def __str__(self):
        return self.name


class Membership(TimeStampedModel):
    """Foydalanuvchining biznesdagi roli. MVPda bitta foydalanuvchi = bitta biznes."""

    class Role(models.TextChoices):
        OWNER = "owner", "Egasi"
        MANAGER = "manager", "Menejer"
        CASHIER = "cashier", "Sotuvchi"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="membership")
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.CASHIER)
    # Sotuvchi faqat shu filiallarni ko'radi. Egasi va menejer barcha filiallarni ko'radi.
    branches = models.ManyToManyField(Branch, blank=True, related_name="members")
    is_active = models.BooleanField(default=True)

    @property
    def is_manager(self) -> bool:
        return self.role in (self.Role.OWNER, self.Role.MANAGER)

    def allowed_branches(self):
        qs = Branch.objects.filter(business=self.business, is_active=True)
        if self.is_manager:
            return qs
        return qs.filter(members=self)

    def __str__(self):
        return f"{self.user} @ {self.business} ({self.role})"
