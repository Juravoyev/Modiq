"""Gemini orqali tavsiyalar bo'yicha qisqa xulosa.

AI qaror chiqarmaydi: qaysi tovar va necha foiz — qoidalar natijasi (services.py). AI faqat shu tayyor ro'yxatni
egasi uchun tushunarli tilda umumlashtiradi. Gemini javob bermasa yoki kalit sozlanmagan bo'lsa,
tavsiyalar baribir ishlaydi, faqat xulosa ko'rinmaydi.

Maxfiylik: Gemini'ga faqat tovar nomi, kategoriya, mavsum va umumlashtirilgan raqamlar yuboriladi.
Mijozlar, xodimlar va do'kon nomi yuborilmaydi.
"""
import hashlib
import json

from django.core.cache import cache

from apps.common import llm
from apps.common.llm import LLMUnavailable as AIUnavailable  # noqa: F401  (eski nom)

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


def summarize(*, business_id: int, recs: list[dict], totals: dict, refresh=False) -> dict:
    """{"text", "model", "cached"}. Bir xil ma'lumot uchun javob 1 soat keshda saqlanadi (keraksiz xarajat yo'q)."""
    if not llm.configured():
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
    text, model = llm.generate([llm.user_message(PROMPT.format(data=data))])
    result = {"text": text, "model": model}
    cache.set(key, result, CACHE_SECONDS)
    return {**result, "cached": False}
