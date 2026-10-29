from rest_framework.permissions import BasePermission


class IsBusinessMember(BasePermission):
    """Foydalanuvchi faol biznes a'zosi bo'lishi shart.

    Muvaffaqiyatli tekshiruvdan so'ng request.membership va request.business o'rnatiladi,
    shuning uchun barcha viewlar tenantni shu yerdan oladi.
    """

    message = "Siz hech qaysi do'konga biriktirilmagansiz."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        membership = getattr(user, "membership", None)
        if membership is None or not membership.is_active or not membership.business.is_active:
            return False
        request.membership = membership
        request.business = membership.business
        return True


class IsManagerOrReadOnly(BasePermission):
    """O'qish hammaga, yozish faqat egasi va menejerga."""

    message = "Bu amal uchun menejer yoki do'kon egasi huquqi kerak."

    def has_permission(self, request, view):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        membership = getattr(request, "membership", None)
        return bool(membership and membership.is_manager)


class IsManager(BasePermission):
    message = "Bu amal uchun menejer yoki do'kon egasi huquqi kerak."

    def has_permission(self, request, view):
        membership = getattr(request, "membership", None)
        return bool(membership and membership.is_manager)


class IsOwnerOrReadOnly(BasePermission):
    """O'qish menejerga ham, yozish (xodim qo'shish, rolini o'zgartirish) faqat do'kon egasiga."""

    message = "Bu amal uchun do'kon egasi huquqi kerak."

    def has_permission(self, request, view):
        membership = getattr(request, "membership", None)
        if membership is None:
            return False
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return membership.is_manager
        return membership.role == membership.Role.OWNER
