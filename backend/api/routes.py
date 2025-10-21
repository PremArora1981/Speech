"""API routes for FastAPI app."""

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from backend.services.conversation_pipeline import ConversationPipeline
from backend.services.telephony_service import (
    SIPParticipantRequest,
    TelephonyAdapter,
    LiveKitTelephonyAdapter,
    TelephonyTrunkRegistration,
)
from backend.database import get_db
from backend.database.repositories import (
    CostEntryRepository,
    SessionMetricsRepository,
    UserFeedbackRepository,
)
from .dependencies import require_api_key
import json

router = APIRouter(prefix="/api/v1")  # Remove global dependency - apply per-route instead


def get_pipeline() -> ConversationPipeline:
    return ConversationPipeline()


def get_telephony_adapter() -> TelephonyAdapter:
    """Get telephony adapter with graceful error handling for missing credentials."""
    try:
        return LiveKitTelephonyAdapter()
    except ValueError as e:
        # LiveKit credentials not configured - return friendly error
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Telephony service not configured: {str(e)}. Please configure LiveKit credentials in your .env file."
        )


@router.websocket("/voice-session")
async def voice_session(
    websocket: WebSocket,
    pipeline: ConversationPipeline = Depends(get_pipeline),
    api_key: str = None
):
    # Validate API key from query parameter (WebSocket can't use headers)
    from backend.config.settings import settings
    if api_key != settings.api_key:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    optimization_level: str | None = None
    target_language: str = "hi-IN"  # Default target language

    try:
        while True:
            raw_message = await websocket.receive_text()
            try:
                payload = json.loads(raw_message)
            except json.JSONDecodeError:
                # Fallback: treat as raw audio URL
                result = await pipeline.process_audio(raw_message, target_language=target_language)
                await websocket.send_json({"text": result.llm_response})
                continue

            message_type = payload.get("type")
            session_id = payload.get("sessionId") or payload.get("session_id")

            if message_type == "start":
                optimization_level = payload.get("optimizationLevel")
                target_language = payload.get("targetLanguage", target_language)
                await pipeline.start_session(session_id, optimization_level)
                await websocket.send_json({"type": "session_started", "sessionId": session_id})
                continue

            if message_type == "audio":
                optimization_level = payload.get("optimizationLevel", optimization_level)
                target_language = payload.get("targetLanguage", target_language)
                result = await pipeline.process_audio_chunk(
                    audio_base64=payload.get("audio"),
                    session_id=session_id,
                    timestamp=payload.get("timestamp"),
                    optimization_level=optimization_level,
                    target_language=target_language,
                )
                if result:
                    await websocket.send_json({
                        "type": "response",
                        "text": result.llm_response,
                        "translated_text": result.translated_text,
                        "audio": result.audio_response.audio_base64 if result.audio_response else None,
                        "transcript": result.transcript.text,
                    })
                continue

            if message_type == "stop":
                optimization_level = payload.get("optimizationLevel", optimization_level)
                await pipeline.finish_session(session_id, optimization_level)
                await websocket.send_json({"type": "session_stopped", "sessionId": session_id})
                continue

    except WebSocketDisconnect:
        # WebSocket already closed, no need to close again
        pass


@router.post("/telephony/calls", dependencies=[Depends(require_api_key)])
async def create_outbound_call(payload: dict, adapter: TelephonyAdapter = Depends(get_telephony_adapter)) -> JSONResponse:
    request = SIPParticipantRequest(
        trunk_id=payload["trunk_id"],
        call_to=payload["call_to"],
        participant_identity=payload.get("participant_identity", payload["call_to"]),
        room_name=payload["room_name"],
        wait_until_answered=payload.get("wait_until_answered", True),
    )
    await adapter.initiate_call(request)
    return JSONResponse({"status": "call_initiated"})


@router.get("/telephony/trunks", dependencies=[Depends(require_api_key)])
async def list_trunks(adapter: TelephonyAdapter = Depends(get_telephony_adapter)) -> JSONResponse:
    trunks = await adapter.list_trunks()
    return JSONResponse({"trunks": [trunk.__dict__ for trunk in trunks]})


@router.post("/telephony/trunks", dependencies=[Depends(require_api_key)])
async def register_trunk(payload: dict, adapter: TelephonyAdapter = Depends(get_telephony_adapter)) -> JSONResponse:
    registration = TelephonyTrunkRegistration(
        provider=payload["provider"],
        trunk_id=payload["trunk_id"],
        direction=payload["direction"],
        sip_uri=payload["sip_uri"],
        transport=payload.get("transport"),
        metadata=payload.get("metadata"),
        credentials=payload.get("credentials"),
    )
    trunk = await adapter.save_trunk_details(registration)
    return JSONResponse({"trunk": trunk.__dict__}, status_code=status.HTTP_201_CREATED)


@router.get("/health")  # No API key required for health check
async def health_check() -> JSONResponse:
    return JSONResponse({"status": "ok"}, status_code=status.HTTP_200_OK)


# Pydantic models for request/response
class FeedbackRequest(BaseModel):
    session_id: str
    turn_id: Optional[str] = None
    message_id: Optional[str] = None
    rating: int  # 1 for thumbs up, -1 for thumbs down, or 1-5 for stars
    rating_type: str = "thumbs"  # thumbs or stars
    feedback_text: Optional[str] = None
    feedback_category: Optional[str] = None
    incorrect_response: bool = False
    too_slow: bool = False
    unhelpful: bool = False
    offensive: bool = False
    user_input: Optional[str] = None
    assistant_response: Optional[str] = None
    metadata: Optional[dict] = None


# Analytics & Monitoring Endpoints

@router.get("/sessions/{session_id}/costs", dependencies=[Depends(require_api_key)])
async def get_session_costs(session_id: str, db: Session = Depends(get_db)) -> JSONResponse:
    """Get cost summary for a session."""
    cost_repo = CostEntryRepository(db)

    # Get all cost entries for the session
    entries = cost_repo.get_session_costs(session_id)

    if not entries:
        return JSONResponse({
            "total_cost_usd": 0.0,
            "breakdown_by_service": {},
            "breakdown_by_provider": {},
            "total_entries": 0,
            "cache_savings_usd": 0.0,
            "optimization_level": None,
        })

    # Calculate breakdowns
    breakdown_by_service = {}
    breakdown_by_provider = {}
    cache_savings_usd = 0.0
    optimization_level = None

    for entry in entries:
        # Service breakdown
        service = entry.service
        if service not in breakdown_by_service:
            breakdown_by_service[service] = 0.0
        breakdown_by_service[service] += float(entry.cost_usd)

        # Provider breakdown
        provider = entry.provider
        if provider not in breakdown_by_provider:
            breakdown_by_provider[provider] = 0.0
        breakdown_by_provider[provider] += float(entry.cost_usd)

        # Cache savings (would have cost if not cached)
        if entry.cached:
            # Estimate what it would have cost
            cache_savings_usd += float(entry.cost_usd) * 0.5  # Assume 50% saving

        # Get optimization level from last entry
        if entry.optimization_level:
            optimization_level = entry.optimization_level

    total_cost = cost_repo.get_session_total_cost(session_id)

    return JSONResponse({
        "total_cost_usd": float(total_cost),
        "breakdown_by_service": breakdown_by_service,
        "breakdown_by_provider": breakdown_by_provider,
        "total_entries": len(entries),
        "cache_savings_usd": cache_savings_usd,
        "optimization_level": optimization_level,
    })


@router.get("/sessions/{session_id}/metrics", dependencies=[Depends(require_api_key)])
async def get_session_metrics(session_id: str, db: Session = Depends(get_db)) -> JSONResponse:
    """Get aggregated metrics for a session."""
    metrics_repo = SessionMetricsRepository(db)

    # Get or create metrics
    metrics = metrics_repo.get_or_create(session_id)

    return JSONResponse({
        "total_turns": metrics.total_turns,
        "successful_turns": metrics.successful_turns,
        "failed_turns": metrics.failed_turns,
        "interrupted_turns": metrics.interrupted_turns,
        "avg_asr_latency_ms": metrics.avg_asr_latency_ms,
        "avg_llm_latency_ms": metrics.avg_llm_latency_ms,
        "avg_translation_latency_ms": metrics.avg_translation_latency_ms,
        "avg_tts_latency_ms": metrics.avg_tts_latency_ms,
        "avg_total_latency_ms": metrics.avg_total_latency_ms,
        "cache_hit_rate": metrics.cache_hit_rate,
        "llm_cache_hits": metrics.llm_cache_hits,
        "llm_cache_misses": metrics.llm_cache_misses,
        "tts_cache_hits": metrics.tts_cache_hits,
        "tts_cache_misses": metrics.tts_cache_misses,
        "guardrail_violations": metrics.guardrail_violations,
        "guardrail_blocks": metrics.guardrail_blocks,
        "total_cost_usd": float(metrics.total_cost_usd) if metrics.total_cost_usd else 0.0,
        "optimization_level": metrics.optimization_level,
        "language_code": metrics.language_code,
    })


@router.post("/feedback", dependencies=[Depends(require_api_key)])
async def submit_feedback(request: FeedbackRequest, db: Session = Depends(get_db)) -> JSONResponse:
    """Submit user feedback for a conversation turn."""
    feedback_repo = UserFeedbackRepository(db)

    # Validate rating based on type
    if request.rating_type == "thumbs":
        if request.rating not in [-1, 1]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rating must be -1 (thumbs down) or 1 (thumbs up) for thumbs type"
            )
    elif request.rating_type == "stars":
        if not 1 <= request.rating <= 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rating must be between 1 and 5 for stars type"
            )

    # Store feedback
    feedback = feedback_repo.add_feedback(
        session_id=request.session_id,
        turn_id=request.turn_id,
        message_id=request.message_id,
        rating=request.rating,
        rating_type=request.rating_type,
        feedback_text=request.feedback_text,
        feedback_category=request.feedback_category,
        incorrect_response=request.incorrect_response,
        too_slow=request.too_slow,
        unhelpful=request.unhelpful,
        offensive=request.offensive,
        user_input=request.user_input,
        assistant_response=request.assistant_response,
        metadata=request.metadata or {},
    )

    return JSONResponse({
        "id": feedback.id,
        "session_id": feedback.session_id,
        "rating": feedback.rating,
        "rating_type": feedback.rating_type,
        "created_at": feedback.created_at.isoformat(),
    }, status_code=status.HTTP_201_CREATED)

