"""FastAPI application exposing TTS synthesis and metrics endpoints."""

from fastapi import Depends, FastAPI, HTTPException, Response

from backend.schemas import SynthesizeRequest, SynthesizeResponse
from backend.services import TTSOrchestrator
from backend.utils import metrics
from backend.api.routes import router

app = FastAPI(title="Speech Backend", version="0.1.0")
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

