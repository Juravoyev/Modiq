import logging

from django.core.cache import cache
from django.http import StreamingHttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common import llm

from .guide import topics_for
from .serializers import AskSerializer
from .services import ANSWER_CACHE_SECONDS, answer_cache_key, check_rate_limit, contents, system_prompt

log = logging.getLogger(__name__)
CUT_NOTE = "\n\n(Javob uzilib qoldi. Qayta so'rab ko'ring.)"


def _stream_response(chunks):
    res = StreamingHttpResponse(chunks, content_type="text/plain; charset=utf-8")
    res["Cache-Control"] = "no-cache"
    res["X-Accel-Buffering"] = "no"  # Nginx javobni bo'laklab yuborsin
    return res


@extend_schema(responses=OpenApiTypes.OBJECT)
class TopicsView(APIView):
    """Xodimning roliga mos tayyor mavzular (AI'siz, darhol)."""

    def get(self, request):
        topics = [{k: t[k] for k in ("id", "icon", "title", "subtitle", "body", "page", "link")}
                  for t in topics_for(request.membership)]
        return Response({"topics": topics, "ai_configured": llm.configured()})


@extend_schema(request=AskSerializer, responses={
    (200, "text/plain"): OpenApiResponse(OpenApiTypes.STR, description="Javob matni bo'lak-bo'lak (stream)")})
class AskView(APIView):
    """Erkin savol. Javob oddiy matn sifatida bo'lak-bo'lak (stream) qaytadi.

    Xato (AI sozlanmagan, band, limit) javob boshlanishidan oldin JSON ko'rinishida qaytadi.
    """

    def post(self, request):
        s = AskSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        question, page, history = s.validated_data["question"], s.validated_data["page"], s.validated_data["history"]
        if not llm.configured():
            raise llm.LLMUnavailable({"detail": "AI yordamchi sozlanmagan. Tayyor mavzulardan foydalaning.",
                                      "code": "ai_not_configured"})
        check_rate_limit(request.user)

        key = answer_cache_key(request.membership, page, question) if not history else None
        if key and (hit := cache.get(key)):
            return _stream_response(iter([hit]))

        chunks = llm.stream(contents(history, question), system=system_prompt(request.membership, page),
                            max_tokens=1024, temperature=0.2)
        try:
            first = next(chunks)
        except StopIteration:
            raise llm.LLMUnavailable({"detail": "AI bo'sh javob qaytardi. Qayta so'rab ko'ring.",
                                      "code": "ai_unavailable"})
        except OSError:
            raise llm.LLMUnavailable({"detail": llm.ERRORS["ai_unavailable"], "code": "ai_unavailable"})

        def body():
            parts = [first]
            yield first
            try:
                for piece in chunks:
                    parts.append(piece)
                    yield piece
            except Exception:  # noqa: BLE001 — oqim o'rtasida uzilish: foydalanuvchiga ayon qilinadi
                log.warning("Yordamchi javobi uzilib qoldi", exc_info=True)
                yield CUT_NOTE
                return
            if key:
                cache.set(key, "".join(parts), ANSWER_CACHE_SECONDS)

        return _stream_response(body())
