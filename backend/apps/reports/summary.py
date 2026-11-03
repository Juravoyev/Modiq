"""Haftalik xulosa. Raqamlarni faqat tizim hisoblaydi, til modeli ularni oddiy matnga aylantiradi xolos.

Til modeli bilan aloqa standart urllib orqali (yangi kutubxona kerak emas). Kalit faqat backend .env da turadi.
"""
import json
import logging
import time
import urllib.error
import urllib.request
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from apps.discounts.services import active_discounts
from apps.insights.engine import compute_insights

from .reports import products_report, sales_report

log = logging.getLogger(__name__)

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

SYSTEM = (
    "Sen kichik kiyim do'koni egasiga haftalik qisqa xulosa yozasan. O'zbek tilida (lotin), sodda va aniq yoz. "
    "Faqat berilgan JSON dagi raqam va faktlardan foydalan. Yangi raqam, foiz, prognoz yoki sabab o'ylab topma. "
    "Agar biror narsa uchun ma'lumot bo'lmasa, shuni ochiq ayt. 'Yalpi foyda' ni sof foyda deb atama: unda ijara, "
    "maosh va boshqa xarajatlar hisobga olinmagan. Javob tuzilishi: 3-5 gaplik umumiy holat, keyin "
    "'Shu hafta nima qilish kerak:' sarlavhasi va 2-4 ta qisqa band (har biri '- ' bilan). Sarlavha va markdown "
    "belgilarini (#, **) ishlatma."
)


class SummaryUnavailable(Exception):
    def __init__(self, message, code):
        super().__init__(message)
        self.code = code


def _totals(report):
    t = report["totals"]
    return {k: str(t.get(k, 0)) for k in ("sales_count", "items", "revenue", "returns", "gross_profit")}


def weekly_facts(business, branches, today=None, donor_branches=None):
    """Oxirgi 7 kun va undan oldingi 7 kun: faqat bazadagi haqiqiy ma'lumotlar."""
    today = today or timezone.localdate()
    week = {"date_from": (today - timedelta(days=6)).isoformat(), "date_to": today.isoformat()}
    prev = {"date_from": (today - timedelta(days=13)).isoformat(), "date_to": (today - timedelta(days=7)).isoformat()}
    top = products_report(business, branches, week)["rows"][:5]
    insights = compute_insights(business, branches, today=today, donor_branches=donor_branches)
    counts = {}
    for item in insights:
        for r in item.risks:
            counts[r.type] = counts.get(r.type, 0) + 1
    high = [{"tovar": f"{i.product_name} {i.variant_name}", "filial": i.branch_name, "qoldiq": i.quantity,
             "xavf": r.title, "sabab": r.reason, "tavsiya": r.action}
            for i in insights for r in i.risks if r.level == "high"][:5]
    return {
        "davr": f"{week['date_from']} — {week['date_to']}",
        "filiallar": [b.name for b in branches],
        "shu_hafta": _totals(sales_report(business, branches, {**week, "group": "day"})),
        "oldingi_hafta": _totals(sales_report(business, branches, {**prev, "group": "day"})),
        "eng_kop_sotilgan": [{"tovar": f"{r['product']} {r['variant']}", "dona": r["quantity"],
                              "tushum": str(r["revenue"])} for r in top],
        "xavflar_soni": {"sotilmay_qolish": counts.get("no_sale", 0), "ortiqcha_zaxira": counts.get("overstock", 0),
                         "mavsumiy": counts.get("seasonal", 0), "qayta_toldirish": counts.get("restock", 0)},
        "yuqori_xavflar": high,
        "amaldagi_chegirmalar": active_discounts(business, today).count(),
        "izoh": "Pul summalari so'mda. yalpi foyda = tushum − tannarx, sof foyda emas.",
    }


def _send(req, attempts=2):
    """Xizmat vaqtincha band (503) yoki javob kechiksa, bir marta qayta urinadi."""
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code != 503 or attempt == attempts - 1:
                raise
        except (urllib.error.URLError, TimeoutError):
            if attempt == attempts - 1:
                raise
        time.sleep(2)


def generate_text(facts) -> str:
    key = settings.GEMINI_API_KEY
    if not key:
        raise SummaryUnavailable("Haftalik xulosa sozlanmagan: backend/.env faylida GEMINI_API_KEY yo'q.",
                                 "not_configured")
    body = {
        "systemInstruction": {"parts": [{"text": SYSTEM}]},
        "contents": [{"role": "user", "parts": [{"text": json.dumps(facts, ensure_ascii=False)}]}],
        # Yangi modellar javobdan oldin "o'ylash"ga ham token sarflaydi, shuning uchun limit katta.
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 4096},
    }
    req = urllib.request.Request(
        GEMINI_URL.format(model=settings.GEMINI_MODEL), data=json.dumps(body).encode(), method="POST",
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
    )
    try:
        data = _send(req)
    except urllib.error.HTTPError as e:
        # Javob matnida kalit bo'lmaydi, lekin baribir faqat holat kodini yozamiz.
        log.warning("Gemini HTTP %s", e.code)
        message = {400: "So'rov noto'g'ri yoki model nomi xato (GEMINI_MODEL).",
                   403: "API kaliti noto'g'ri yoki bu xizmatga ruxsat yo'q.",
                   429: "So'rovlar limiti tugadi, birozdan keyin qayta urinib ko'ring.",
                   503: "Xulosa xizmati hozir band, bir necha daqiqadan keyin qayta urinib ko'ring."}.get(
            e.code, "Xulosa xizmati javob bermadi.")
        raise SummaryUnavailable(message, "provider_error") from e
    except (urllib.error.URLError, TimeoutError) as e:
        log.warning("Gemini ulanish xatosi: %s", type(e).__name__)
        raise SummaryUnavailable("Xulosa xizmatiga ulanib bo'lmadi. Internetni tekshiring.", "network") from e
    try:
        candidate = data["candidates"][0]
        parts = candidate["content"]["parts"]
        text = "".join(p.get("text", "") for p in parts if not p.get("thought")).strip()
    except (KeyError, IndexError, TypeError):
        candidate, text = {}, ""
    if candidate.get("finishReason") == "MAX_TOKENS":
        # Chala matnni ko'rsatmaymiz va keshlamaymiz.
        raise SummaryUnavailable("Xulosa matni to'liq chiqmadi (javob uzunligi limiti). Qayta urinib ko'ring.",
                                 "truncated")
    if not text:
        raise SummaryUnavailable("Xulosa xizmati bo'sh javob qaytardi.", "empty")
    return text
