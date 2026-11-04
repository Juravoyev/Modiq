"""Gemini orqali tavsiyalar bo'yicha qisqa xulosa.

AI qaror chiqarmaydi: qaysi tovar va necha foiz — qoidalar natijasi (services.py). AI faqat shu tayyor ro'yxatni
egasi uchun tushunarli tilda umumlashtiradi. Gemini javob bermasa yoki kalit sozlanmagan bo'lsa,
tavsiyalar baribir ishlaydi, faqat xulosa ko'rinmaydi.

Maxfiylik: Gemini'ga faqat tovar nomi, kategoriya, mavsum va umumlashtirilgan raqamlar yuboriladi.
Mijozlar, xodimlar va do'kon nomi yuborilmaydi.
"""
import hashlib
import json
import logging
import urllib.error
import urllib.request

from django.conf import settings
from django.core.cache import cache
from rest_framework import status
from rest_framework.exceptions import APIException

log = logging.getLogger(__name__)

API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
CACHE_SECONDS = 60 * 60
MAX_ITEMS = 15

PROMPT = """Sen O'zbekistondagi kiyim-kechak do'koni egasiga maslahat beruvchi yordamchisan.
Quyida tizim qoidalar asosida tanlagan "sotilmay qolish xavfi" bo'lgan tovarlar ro'yxati (JSON) berilgan.
Har bir tovar uchun chegirma foizi va sabablari tizim tomonidan hisoblangan.

Vazifa: do'kon egasi uchun o'zbek tilida (lotin yozuvida) qisqa xulosa yoz.
Qoidalar:
- Faqat berilgan raqamlarga tayan. Yangi raqam, foiz yoki tovar o'ylab topma.
- Tizim bergan chegirma foizlarini o'zgartirma va boshqa foiz tavsiya qilma.
- Avval umumiy holatni 1-2 gapda ayt (nechta tovar, jami qancha pul muzlab turibdi).
- Keyin birinchi navbatda e'tibor berish kerak bo'lgan 2-3 tovarni nomi bilan ayt va nega ekanini qisqa tushuntir.
- Mavsumiy tovarlar bo'lsa, vaqt omilini alohida ta'kidla.
- Oxirida bitta amaliy maslahat ber (masalan, aksiyani qachon boshlash yoki tovarni qayerda ko'rsatish).
- Jami 5-8 gapdan oshmasin. Markdown sarlavha ishlatma, oddiy matn yoz.

Ma'lumot:
{data}
"""


class AIUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_code = "ai_unavailable"


def _payload(recs: list[dict], totals: dict) -> dict:
    return {
        "jami_tovar": totals["count"],
        "muzlagan_pul_som": int(totals["frozen_value"]),
        "tovarlar": [{
            "nomi": r["name"], "kategoriya": r["category_name"], "mavsum": r["season_name"],
            "xavf": r["level_display"], "tavsiya_chegirma_foiz": r["discount"],
            "qoldiq_dona": r["units"], "tannarxda_som": int(r["value_cost"]),
            "oxirgi_30_kunda_sotilgan": r["sold_30"], "sabablar": r["reasons"],
            "faol_aksiya_bor": r["active_promotion"] is not None,
        } for r in recs[:MAX_ITEMS]],
    }


def _call_gemini(prompt: str) -> str:
    key = settings.GEMINI_API_KEY
    url = API_URL.format(model=settings.GEMINI_MODEL)
    body = json.dumps({
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 800},
    }).encode()
    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={"Content-Type": "application/json", "x-goog-api-key": key})
    try:
        with urllib.request.urlopen(req, timeout=settings.GEMINI_TIMEOUT) as res:
            data = json.loads(res.read())
    except urllib.error.HTTPError as e:
        log.warning("Gemini HTTP %s: %s", e.code, e.read()[:300])
        if e.code in (401, 403):
            raise AIUnavailable({"detail": "Gemini API kaliti noto'g'ri yoki ruxsati yo'q.", "code": "ai_auth"})
        if e.code == 429:
            raise AIUnavailable({"detail": "Gemini so'rovlar chegarasi tugadi. Birozdan keyin urinib ko'ring.",
                                 "code": "ai_rate_limit"})
        raise AIUnavailable({"detail": "Gemini javob bermadi. Tavsiyalar baribir ishlaydi.", "code": "ai_unavailable"})
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        log.warning("Gemini ulanish xatosi: %s", e)
        raise AIUnavailable({"detail": "Gemini bilan aloqa yo'q (internet?). Tavsiyalar baribir ishlaydi.",
                             "code": "ai_unavailable"})
    try:
        parts = data["candidates"][0]["content"]["parts"]
        text = "".join(p.get("text", "") for p in parts).strip()
    except (KeyError, IndexError, TypeError):
        text = ""
    if not text:
        raise AIUnavailable({"detail": "Gemini bo'sh javob qaytardi. Qayta urinib ko'ring.", "code": "ai_unavailable"})
    return text


def summarize(*, business_id: int, recs: list[dict], totals: dict, refresh=False) -> dict:
    """{"text", "model", "cached"}. Bir xil ma'lumot uchun javob 1 soat keshda saqlanadi (keraksiz xarajat yo'q)."""
    if not settings.GEMINI_API_KEY:
        raise AIUnavailable({"detail": "AI xulosasi sozlanmagan: backend/.env fayliga GEMINI_API_KEY qo'shing.",
                             "code": "ai_not_configured"})
    if not recs:
        return {"text": "Hozircha sotilmay qolish xavfi bo'lgan tovar yo'q. Hamma tovarlar me'yorida sotilmoqda.",
                "model": None, "cached": False}
    data = json.dumps(_payload(recs, totals), ensure_ascii=False)
    key = "insights-ai:%s:%s" % (business_id, hashlib.sha256(data.encode()).hexdigest()[:32])
    if not refresh:
        hit = cache.get(key)
        if hit:
            return {**hit, "cached": True}
    result = {"text": _call_gemini(PROMPT.format(data=data)), "model": settings.GEMINI_MODEL}
    cache.set(key, result, CACHE_SECONDS)
    return {**result, "cached": False}
