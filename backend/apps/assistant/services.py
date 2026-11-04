"""Yordamchi: dasturdan foydalanishni o'rgatadi. Faqat qo'llanmaga (guide.py) tayanadi.

Yordamchi xodimning o'rniga ish qilmaydi va do'kon ma'lumotlarini (savdo, qoldiq, mijozlar) bilmaydi:
u qadamlarni tushuntiradi, xodim o'zi bajaradi. AI'ga faqat savol, suhbat tarixi va qo'llanma yuboriladi.
"""
import hashlib
import re

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException

from .guide import TOPICS, allowed, page_name, topics_for

ANSWER_CACHE_SECONDS = 24 * 60 * 60

ROLE_NAMES = {"owner": "do'kon egasi", "manager": "menejer", "cashier": "sotuvchi"}

SYSTEM = """Sen «Modiq» dasturining yordamchisisan. Modiq — kiyim-kechak do'koni uchun kassa, ombor va hisobot dasturi.
Vazifang: xodimga dasturdan foydalanishni o'rgatish.

Qat'iy qoidalar:
1. Faqat quyidagi QO'LLANMA asosida javob ber. Qo'llanmada yo'q tugma, sahifa yoki imkoniyatni o'ylab topma.
   Javob qo'llanmada bo'lmasa: "Bu haqda ma'lumotim yo'q. Do'kon egasi yoki menejerga murojaat qiling." de.
2. Xodim ishni o'zi bajarsin: qadamlarni tushuntir, uning o'rniga hech narsa qilmaysan va qila olmaysan.
3. Do'kon ma'lumotlarini (bugungi savdo, qoldiq soni, mijoz ma'lumoti, foyda) bilmaysan. Bunday savolga
   raqam aytma, faqat qaysi bo'limda o'zi ko'rishini ayt.
4. Foydalanuvchi roli: {role}. {role_note}
5. Tugma va bo'lim nomlarini «» ichida qo'llanmadagidek aynan yoz.
6. Javob qisqa bo'lsin: 2-6 ta raqamlangan qadam, kerak bo'lsa 1-2 gap izoh. Oddiy matn, sarlavhasiz.
   Muhim so'zni **qalin** qilish mumkin.
7. O'zbek tilida (lotin yozuvida) javob ber. Savol rus tilida bo'lsa, rus tilida javob ber.
8. Dasturga aloqasi yo'q savollarga (siyosat, uy vazifasi, umumiy suhbat) muloyimlik bilan:
   "Men faqat Modiq dasturidan foydalanish bo'yicha yordam beraman." de.
{page_line}
QO'LLANMA:
{guide}
"""


class AssistantLimit(APIException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_code = "assistant_limit"


def role_key(membership) -> str:
    return f"{membership.role}:{int(membership.may_approve_returns)}"


def system_prompt(membership, page: str) -> str:
    own = topics_for(membership)
    guide = "\n\n".join(f"## {t['title']}\n{t['body']}" for t in own)
    hidden = [t["title"] for t in TOPICS if not allowed(t, membership)]
    role_note = ""
    if hidden:
        role_note = ("Quyidagi ishlar bu xodimga ruxsat etilmagan: " + ", ".join(hidden) + ". Savol shulardan biriga "
                     "tegishli bo'lsa, \"ma'lumotim yo'q\" dema, aniq ayt: \"Bu ishni do'kon egasi yoki menejer "
                     "bajaradi, ularga murojaat qiling.\"")
    name = page_name(page)
    page_line = f"Xodim hozir «{name}» sahifasida turibdi.\n" if name else ""
    return SYSTEM.format(role=ROLE_NAMES.get(membership.role, membership.role), role_note=role_note,
                         page_line=page_line, guide=guide)


def check_rate_limit(user):
    """Bitta xodim soatiga ASSISTANT_HOURLY_LIMIT tadan ko'p savol bera olmaydi."""
    key = "assistant-rl:%s:%s" % (user.pk, timezone.now().strftime("%Y%m%d%H"))
    cache.add(key, 0, 60 * 60)
    try:
        count = cache.incr(key)
    except ValueError:
        cache.set(key, 1, 60 * 60)
        count = 1
    if count > settings.ASSISTANT_HOURLY_LIMIT:
        raise AssistantLimit({"detail": "Bir soatlik savollar chegarasi tugadi. Tayyor mavzulardan foydalaning "
                                        "yoki birozdan keyin qayta so'rang.", "code": "assistant_limit"})


def _normalize(text: str) -> str:
    return re.sub(r"[\s?!.,]+", " ", text.lower()).strip()


def answer_cache_key(membership, page: str, question: str) -> str:
    """Bir xil rol, sahifa va savol uchun javob qayta ishlatiladi (birinchi savol, suhbat tarixisiz)."""
    raw = f"{role_key(membership)}|{page_name(page)}|{_normalize(question)}"
    return "assistant-ans:%s:%s" % (membership.business_id, hashlib.sha256(raw.encode()).hexdigest()[:32])


def contents(history: list[dict], question: str) -> list[dict]:
    msgs = [{"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["text"]}]}
            for m in history[-6:]]
    msgs.append({"role": "user", "parts": [{"text": question}]})
    return msgs
