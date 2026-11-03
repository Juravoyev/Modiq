from django.db.models import ProtectedError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


def exception_handler(exc, context):
    """DRF standart handleri + ishlatilayotgan yozuvni o'chirishga urinish (500 o'rniga 400)."""
    if isinstance(exc, ProtectedError):
        return Response(
            {"detail": "Bu yozuv boshqa ma'lumotlarda ishlatilgan, shuning uchun uni o'chirib bo'lmaydi.",
             "code": "protected"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return drf_exception_handler(exc, context)
