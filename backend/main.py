"""FastAPI application exposing TTS synthesis and metrics endpoints."""

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware

from backend.schemas import SynthesizeRequest, SynthesizeResponse
from backend.services import TTSOrchestrator
from backend.utils import metrics
from backend.utils import custom_metrics  # Import to register custom metrics
from backend.api.routes import router
from backend.api.middleware import (
    RateLimitMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
)

app = FastAPI(title="Speech Backend", version="0.1.0")

# Add middleware (order matters - first added = outermost layer)
# 1. CORS (must be first to allow cross-origin requests)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Docker frontend
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "*",  # Allow all for development
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# 2. Security headers
app.add_middleware(SecurityHeadersMiddleware)

# 3. Request logging
app.add_middleware(RequestLoggingMiddleware)

# 4. Rate limiting
app.add_middleware(RateLimitMiddleware)

app.include_router(router)


def get_tts_orchestrator() -> TTSOrchestrator:
    return TTSOrchestrator()


@app.post("/api/v1/tts", response_model=SynthesizeResponse)
async def synthesize_speech(
    payload: SynthesizeRequest,
    orchestrator: TTSOrchestrator = Depends(get_tts_orchestrator),
) -> SynthesizeResponse:
    try:
        return await orchestrator.synthesize(payload)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/metrics")
async def get_metrics() -> Response:
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

    payload = generate_latest()  # type: ignore[arg-type]
    return Response(content=payload, media_type=CONTENT_TYPE_LATEST)

