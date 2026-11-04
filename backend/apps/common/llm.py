"""Til modeli (LLM) bilan aloqa. Hozir Google Gemini, keyinchalik boshqa provayder (masalan, OpenRouter) shu yerga qo'shiladi.

- GEMINI_MODEL vergul bilan bir nechta model bo'lishi mumkin: birinchisi band (503), eskirgan (404) yoki javob
  bermasa, keyingisi sinaladi.
- Xatolar foydalanuvchiga tushunarli o'zbekcha xabar va `code` bilan qaytadi (HTTP 503).
"""
import json
import logging
import urllib.error
import urllib.request

from django.conf import settings
from rest_framework import status
from rest_framework.exceptions import APIException

log = logging.getLogger(__name__)

BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:{method}"

ERRORS = {
    "ai_busy": "AI hozir band (Google serverida yuklama yuqori). Bir-ikki daqiqadan keyin qayta urinib ko'ring.",
    "ai_model": "backend/.env dagi GEMINI_MODEL modeli Gemini'da yo'q yoki eskirgan. Uni almashtiring "
                "(masalan, gemini-flash-lite-latest).",
    "ai_unavailable": "AI bilan aloqa yo'q yoki javob juda kech keldi.",
}


class LLMUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_code = "ai_unavailable"


def configured() -> bool:
    return bool(settings.GEMINI_API_KEY)


def models() -> list[str]:
    return [m.strip() for m in settings.GEMINI_MODEL.split(",") if m.strip()]


def _require_key():
    if not configured():
        raise LLMUnavailable({"detail": "AI sozlanmagan: backend/.env fayliga GEMINI_API_KEY qo'shing.",
                              "code": "ai_not_configured"})


def _request(model: str, method: str, contents: list, system: str | None, max_tokens: int, temperature: float):
    body = {"contents": contents, "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens}}
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    url = BASE_URL.format(model=model, method=method)
    if method == "streamGenerateContent":
        url += "?alt=sse"
    return urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                  headers={"Content-Type": "application/json",
                                           "x-goog-api-key": settings.GEMINI_API_KEY})


def _text(data) -> str:
    try:
        parts = data["candidates"][0]["content"]["parts"]
        return "".join(p.get("text", "") for p in parts)
    except (KeyError, IndexError, TypeError):
        return ""


def _classify(e: urllib.error.HTTPError, model: str) -> str:
    """HTTP xatoni kodga aylantiradi. Kalit yoki limit xatosida darhol to'xtaydi (boshqa model yordam bermaydi)."""
    log.warning("Gemini HTTP %s (%s): %s", e.code, model, e.read()[:300])
    if e.code in (401, 403):
        raise LLMUnavailable({"detail": "Gemini API kaliti noto'g'ri yoki ruxsati yo'q.", "code": "ai_auth"})
    if e.code == 429:
        raise LLMUnavailable({"detail": "AI so'rovlar chegarasi tugadi. Birozdan keyin urinib ko'ring.",
                              "code": "ai_rate_limit"})
    return "ai_model" if e.code == 404 else "ai_busy" if e.code in (500, 503) else "ai_unavailable"


def user_message(text: str) -> dict:
    return {"role": "user", "parts": [{"text": text}]}


def generate(contents: list, *, system: str | None = None, max_tokens=4096, temperature=0.3) -> tuple[str, str]:
    """To'liq javob: (matn, model)."""
    _require_key()
    last = "ai_unavailable"
    for model in models():
        try:
            req = _request(model, "generateContent", contents, system, max_tokens, temperature)
            with urllib.request.urlopen(req, timeout=settings.GEMINI_TIMEOUT) as res:
                text = _text(json.loads(res.read())).strip()
            if text:
                return text, model
            log.warning("Gemini (%s) bo'sh javob qaytardi", model)
            last = "ai_unavailable"
        except urllib.error.HTTPError as e:
            last = _classify(e, model)
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            log.warning("Gemini ulanish xatosi (%s): %s", model, e)
            last = "ai_unavailable"
    raise LLMUnavailable({"detail": ERRORS[last], "code": last})


def stream(contents: list, *, system: str | None = None, max_tokens=2048, temperature=0.3):
    """Javobni bo'lak-bo'lak qaytaradigan generator. Zaxira model faqat birinchi bo'lak kelmaguncha sinaladi.

    Birinchi bo'lakni olishdan oldin xato bo'lsa LLMUnavailable ko'tariladi (chaqiruvchi JSON xato qaytara oladi).
    """
    _require_key()
    last = "ai_unavailable"
    for model in models():
        try:
            req = _request(model, "streamGenerateContent", contents, system, max_tokens, temperature)
            res = urllib.request.urlopen(req, timeout=settings.GEMINI_TIMEOUT)
        except urllib.error.HTTPError as e:
            last = _classify(e, model)
            continue
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            log.warning("Gemini ulanish xatosi (%s): %s", model, e)
            continue
        return _sse_chunks(res, model)
    raise LLMUnavailable({"detail": ERRORS[last], "code": last})


def _sse_chunks(res, model):
    """Server-Sent Events oqimidan matn bo'laklarini ajratadi."""
    with res:
        for raw in res:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue
            try:
                piece = _text(json.loads(line[5:].strip()))
            except json.JSONDecodeError:
                log.warning("Gemini (%s) noto'g'ri SSE qatori", model)
                continue
            if piece:
                yield piece
