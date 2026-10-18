"""M5 · Derja assistant. Thin FastAPI wrapper: no business logic, no database.

- POST /intent: which module should answer (trained TF-IDF + SetFit ensemble)
- POST /answer: an LLM writes the reply in derja from the facts gathered by the backend
- POST /explain: an LLM explains in plain words the result of any module (M1-M6)

Routing the question to M1-M4 / M6 is done by the Spring backend (ChatService), not here.
"""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request

from app import explain as explainer
from app import predictor
from app.llm import AllProvidersFailed, LlmRouter, build_chain
from app.prompt import build_messages, is_arabic_script
from app.schemas import AnswerRequest, AnswerResponse, ExplainRequest, ExplainResponse, IntentRequest, IntentResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("m5")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load both models ONCE, then warm them up so the first farmer does not wait.
    started = time.perf_counter()
    app.state.ensemble = predictor.load()
    predictor.predict(app.state.ensemble, "aslema")
    log.info("models ready in %.1f s (loaded=%s)", time.perf_counter() - started, app.state.ensemble is not None)
    app.state.llm = LlmRouter(build_chain())
    log.info("LLM chain: %s", [m.name for m in app.state.llm.models] or "none (no API key): template answers only")
    # Explanations are longer than chat replies (and derja takes more time): more time per call, still under
    # the backend's 15 s LLM timeout.
    app.state.explain_llm = LlmRouter(build_chain(), timeout_s=8.0, deadline_s=14.0)
    yield
    app.state.llm.client.close()
    app.state.explain_llm.client.close()


app = FastAPI(
    title="Zitouna M5 · Derja assistant",
    version="2.1",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


@app.get("/health")
def health(request: Request) -> dict:
    return {
        "status": "ok",
        "module": "m5-assistant",
        "modelLoaded": request.app.state.ensemble is not None,
        "llmModels": [m.name for m in request.app.state.llm.models],
    }


@app.post("/intent", response_model=IntentResponse)
def intent(body: IntentRequest, request: Request) -> IntentResponse:
    started = time.perf_counter()
    result = predictor.predict(request.app.state.ensemble, body.text)
    log.info(
        "text=%r intent=%s confidence=%.2f clarify=%s duration_ms=%.0f",
        body.text[:60],
        result.intent,
        result.confidence,
        result.clarify,
        (time.perf_counter() - started) * 1000,
    )
    return result


@app.post("/answer", response_model=AnswerResponse, responses={503: {"description": "No LLM available"}})
def answer(body: AnswerRequest, request: Request) -> AnswerResponse:
    """503 when no LLM is configured or all are failing: the backend then uses its template answer."""
    router: LlmRouter = request.app.state.llm
    if not router.enabled:
        raise HTTPException(status_code=503, detail="No LLM configured (set GEMINI_API_KEY...)")
    try:
        done = router.complete(build_messages(body), accept=is_arabic_script)
    except AllProvidersFailed as e:
        raise HTTPException(status_code=503, detail=f"All LLMs failed: {e}") from e
    log.info("answer intent=%s facts=%d llm=%s/%s latency_ms=%d", body.intent, len(body.facts), done.provider,
             done.model, done.latency_ms)  # fmt: skip
    return AnswerResponse(answer=done.text, provider=done.provider, model=done.model, latency_ms=done.latency_ms)


@app.post("/explain", response_model=ExplainResponse)
def explain(body: ExplainRequest, request: Request) -> ExplainResponse:
    """Always 200: without any LLM the explanation is a template sentence (fallback=True)."""
    result = explainer.explain(request.app.state.explain_llm, body)
    log.info("explain module=%s language=%s by=%s/%s fallback=%s latency_ms=%d", body.module, body.language,
             result.provider, result.model, result.fallback, result.latency_ms)  # fmt: skip
    return result
