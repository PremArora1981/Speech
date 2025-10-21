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
from backend.services.voice_discovery import VoiceDiscoveryService
from backend.services.tts_service import TTSService
from backend.services.llm_provider_registry import LLMProviderRegistry
from backend.services.system_prompt_service import SystemPromptService
from backend.schemas.tts import SynthesizeRequest, VoiceSelection
from backend.database import get_db
from backend.database.repositories import (
    CostEntryRepository,
    SessionMetricsRepository,
    UserFeedbackRepository,
    SessionConfigRepository,
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


def get_voice_discovery() -> VoiceDiscoveryService:
    """Get voice discovery service instance."""
    return VoiceDiscoveryService()


def get_tts_service() -> TTSService:
    """Get TTS service instance."""
    return TTSService()


def get_llm_registry() -> LLMProviderRegistry:
    """Get LLM provider registry instance."""
    return LLMProviderRegistry()


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


# Voice Discovery Endpoints

@router.get("/tts/providers", dependencies=[Depends(require_api_key)])
async def list_tts_providers() -> JSONResponse:
    """List all available TTS providers."""
    providers = [
        {
            "id": "sarvam",
            "name": "Sarvam AI",
            "description": "Indian language specialist with 10+ Indian languages",
            "supports_tuning": True,
            "languages": ["hi-IN", "en-IN", "bn-IN", "gu-IN", "ta-IN", "te-IN", "ml-IN", "kn-IN", "mr-IN", "pa-IN"],
        },
        {
            "id": "elevenlabs",
            "name": "ElevenLabs",
            "description": "Premium quality voices with custom voice cloning",
            "supports_tuning": False,
            "languages": ["en-US", "en-IN"],
        },
    ]
    return JSONResponse({"providers": providers})


@router.get("/tts/voices", dependencies=[Depends(require_api_key)])
async def list_voices(
    provider: Optional[str] = None,
    language: Optional[str] = None,
    include_custom: bool = True,
    voice_service: VoiceDiscoveryService = Depends(get_voice_discovery),
) -> JSONResponse:
    """List all available voices, optionally filtered by provider and language.

    Args:
        provider: Filter by provider (sarvam or elevenlabs)
        language: Filter by language code (e.g., en-IN)
        include_custom: Include custom/cloned voices (default: true)
    """
    voices = await voice_service.fetch_all_voices(
        provider=provider,
        language=language,
        include_custom=include_custom,
    )

    # Convert to dict for JSON response
    return JSONResponse({
        "voices": [v.model_dump() for v in voices],
        "total": len(voices),
    })


@router.get("/tts/voices/elevenlabs/custom", dependencies=[Depends(require_api_key)])
async def list_custom_elevenlabs_voices(
    api_key: Optional[str] = None,
    voice_service: VoiceDiscoveryService = Depends(get_voice_discovery),
) -> JSONResponse:
    """List only custom/cloned voices from user's ElevenLabs account.

    Args:
        api_key: Optional user's ElevenLabs API key (if different from default)
    """
    voices = await voice_service.fetch_custom_elevenlabs_voices(api_key=api_key)

    return JSONResponse({
        "voices": [v.model_dump() for v in voices],
        "total": len(voices),
    })


class VoicePreviewRequest(BaseModel):
    """Request model for voice preview."""
    voice_id: str
    provider: str
    text: str = "Hello! This is a preview of this voice."
    language_code: str = "en-IN"
    pitch: Optional[float] = None
    pace: Optional[float] = None
    loudness: Optional[float] = None


@router.post("/tts/voices/preview", dependencies=[Depends(require_api_key)])
async def preview_voice(
    request: VoicePreviewRequest,
    tts_service: TTSService = Depends(get_tts_service),
) -> JSONResponse:
    """Preview a voice with custom text and optional tuning parameters.

    Args:
        request: Preview request containing voice details and text
    """
    try:
        # Create synthesize request
        synth_request = SynthesizeRequest(
            text=request.text,
            language_code=request.language_code,
            optimization_level="balanced",  # Use balanced for preview
            voice=VoiceSelection(
                provider=request.provider,  # type: ignore
                voice_id=request.voice_id,
            ),
            pitch=request.pitch,
            pace=request.pace,
            loudness=request.loudness,
        )

        # Synthesize speech
        result = await tts_service.synthesize(synth_request)

        return JSONResponse({
            "audio_b64": result.audio_b64,
            "mime_type": result.mime_type,
            "voice_id": request.voice_id,
            "provider": request.provider,
        })

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to preview voice: {str(e)}"
        )


@router.get("/health")  # No API key required for health check
async def health_check() -> JSONResponse:
    return JSONResponse({"status": "ok"}, status_code=status.HTTP_200_OK)


# LLM Provider Endpoints

@router.get("/llm/providers", dependencies=[Depends(require_api_key)])
async def list_llm_providers(
    registry: LLMProviderRegistry = Depends(get_llm_registry),
) -> JSONResponse:
    """List all available LLM providers."""
    providers = registry.list_providers()

    return JSONResponse({
        "providers": [
            {
                "id": p.id,
                "name": p.name,
                "display_name": p.display_name,
                "description": p.description,
                "requires_api_key": p.requires_api_key,
                "supports_streaming": p.supports_streaming,
                "model_count": len(p.models),
            }
            for p in providers
        ],
        "total": len(providers),
    })


@router.get("/llm/models", dependencies=[Depends(require_api_key)])
async def list_llm_models(
    provider: Optional[str] = None,
    registry: LLMProviderRegistry = Depends(get_llm_registry),
) -> JSONResponse:
    """List all available LLM models, optionally filtered by provider.

    Args:
        provider: Filter by provider ID (e.g., sarvam, openai, anthropic)
    """
    if provider:
        # Get models for specific provider
        models = registry.get_models(provider)
        if not models:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Provider '{provider}' not found"
            )
    else:
        # Get all models from all providers
        models = []
        for prov in registry.list_providers():
            models.extend(prov.models)

    return JSONResponse({
        "models": [
            {
                "id": m.id,
                "name": m.name,
                "provider": m.provider,
                "context_window": m.context_window,
                "max_output_tokens": m.max_output_tokens,
                "supports_streaming": m.supports_streaming,
                "cost_per_1k_input_tokens": m.cost_per_1k_input_tokens,
                "cost_per_1k_output_tokens": m.cost_per_1k_output_tokens,
                "description": m.description,
            }
            for m in models
        ],
        "total": len(models),
    })


# System Prompt Endpoints

class SystemPromptCreate(BaseModel):
    """Request model for creating a system prompt."""
    name: str
    prompt_text: str
    category: str
    is_default: bool = False
    variables: Optional[list] = None
    meta_data: Optional[dict] = None


class SystemPromptUpdate(BaseModel):
    """Request model for updating a system prompt."""
    name: Optional[str] = None
    prompt_text: Optional[str] = None
    category: Optional[str] = None
    is_default: Optional[bool] = None
    variables: Optional[list] = None
    meta_data: Optional[dict] = None


@router.get("/system-prompts", dependencies=[Depends(require_api_key)])
async def list_system_prompts(
    category: Optional[str] = None,
    is_template: Optional[bool] = None,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """List all system prompts with optional filters.

    Args:
        category: Filter by category
        is_template: Filter for templates (true) or user prompts (false)
    """
    service = SystemPromptService(db)
    prompts = service.list_prompts(category=category, is_template=is_template)

    return JSONResponse({
        "prompts": [
            {
                "id": p.id,
                "name": p.name,
                "prompt_text": p.prompt_text,
                "category": p.category,
                "is_default": p.is_default,
                "is_template": p.is_template,
                "variables": p.variables,
                "meta_data": p.meta_data,
                "created_at": p.created_at.isoformat(),
                "updated_at": p.updated_at.isoformat(),
            }
            for p in prompts
        ],
        "total": len(prompts),
    })


@router.get("/system-prompts/templates", dependencies=[Depends(require_api_key)])
async def list_prompt_templates(
    db: Session = Depends(get_db),
) -> JSONResponse:
    """List all built-in system prompt templates."""
    service = SystemPromptService(db)
    templates = service.list_prompts(is_template=True)

    return JSONResponse({
        "templates": [
            {
                "id": t.id,
                "name": t.name,
                "prompt_text": t.prompt_text,
                "category": t.category,
                "variables": t.variables,
                "meta_data": t.meta_data,
            }
            for t in templates
        ],
        "total": len(templates),
    })


@router.get("/system-prompts/{prompt_id}", dependencies=[Depends(require_api_key)])
async def get_system_prompt(
    prompt_id: str,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Get a specific system prompt by ID."""
    service = SystemPromptService(db)
    prompt = service.get_prompt(prompt_id)

    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"System prompt '{prompt_id}' not found"
        )

    return JSONResponse({
        "id": prompt.id,
        "name": prompt.name,
        "prompt_text": prompt.prompt_text,
        "category": prompt.category,
        "is_default": prompt.is_default,
        "is_template": prompt.is_template,
        "variables": prompt.variables,
        "meta_data": prompt.meta_data,
        "created_at": prompt.created_at.isoformat(),
        "updated_at": prompt.updated_at.isoformat(),
    })


@router.post("/system-prompts", dependencies=[Depends(require_api_key)])
async def create_system_prompt(
    request: SystemPromptCreate,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Create a new system prompt."""
    service = SystemPromptService(db)

    try:
        prompt = service.create_prompt(
            name=request.name,
            prompt_text=request.prompt_text,
            category=request.category,
            is_default=request.is_default,
            is_template=False,  # User-created prompts are not templates
            variables=request.variables,
            meta_data=request.meta_data,
        )

        return JSONResponse({
            "id": prompt.id,
            "name": prompt.name,
            "prompt_text": prompt.prompt_text,
            "category": prompt.category,
            "is_default": prompt.is_default,
            "variables": prompt.variables,
            "created_at": prompt.created_at.isoformat(),
        }, status_code=status.HTTP_201_CREATED)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create system prompt: {str(e)}"
        )


@router.put("/system-prompts/{prompt_id}", dependencies=[Depends(require_api_key)])
async def update_system_prompt(
    prompt_id: str,
    request: SystemPromptUpdate,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Update a system prompt."""
    service = SystemPromptService(db)

    try:
        prompt = service.update_prompt(
            prompt_id=prompt_id,
            name=request.name,
            prompt_text=request.prompt_text,
            category=request.category,
            is_default=request.is_default,
            variables=request.variables,
            meta_data=request.meta_data,
        )

        if not prompt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"System prompt '{prompt_id}' not found"
            )

        return JSONResponse({
            "id": prompt.id,
            "name": prompt.name,
            "prompt_text": prompt.prompt_text,
            "category": prompt.category,
            "is_default": prompt.is_default,
            "updated_at": prompt.updated_at.isoformat(),
        })

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update system prompt: {str(e)}"
        )


@router.delete("/system-prompts/{prompt_id}", dependencies=[Depends(require_api_key)])
async def delete_system_prompt(
    prompt_id: str,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Delete a system prompt."""
    service = SystemPromptService(db)

    try:
        deleted = service.delete_prompt(prompt_id)

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"System prompt '{prompt_id}' not found"
            )

        return JSONResponse({"message": "System prompt deleted successfully"})

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete system prompt: {str(e)}"
        )


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


# Session Configuration Endpoints

class SessionConfigCreate(BaseModel):
    """Request model for creating a session configuration."""
    name: str
    user_id: Optional[str] = None
    llm_provider: str
    llm_model: str
    tts_provider: str
    tts_voice_id: str
    voice_tuning: Optional[dict] = None
    system_prompt_id: Optional[str] = None
    system_prompt_text: Optional[str] = None
    optimization_level: str = "balanced"
    target_language: str = "en-IN"
    enable_rag: bool = False
    is_default: bool = False
    metadata: Optional[dict] = None


class SessionConfigUpdate(BaseModel):
    """Request model for updating a session configuration."""
    name: Optional[str] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    tts_provider: Optional[str] = None
    tts_voice_id: Optional[str] = None
    voice_tuning: Optional[dict] = None
    system_prompt_id: Optional[str] = None
    system_prompt_text: Optional[str] = None
    optimization_level: Optional[str] = None
    target_language: Optional[str] = None
    enable_rag: Optional[bool] = None
    is_default: Optional[bool] = None
    metadata: Optional[dict] = None


@router.get("/config/sessions", dependencies=[Depends(require_api_key)])
async def list_session_configs(
    user_id: Optional[str] = None,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """List all session configurations, optionally filtered by user.

    Args:
        user_id: Filter by user ID (optional)
    """
    config_repo = SessionConfigRepository(db)
    configs = config_repo.list(user_id=user_id)

    return JSONResponse({
        "configs": [
            {
                "id": c.id,
                "name": c.name,
                "user_id": c.user_id,
                "llm_provider": c.llm_provider,
                "llm_model": c.llm_model,
                "tts_provider": c.tts_provider,
                "tts_voice_id": c.tts_voice_id,
                "voice_tuning": c.voice_tuning,
                "system_prompt_id": c.system_prompt_id,
                "system_prompt_text": c.system_prompt_text,
                "optimization_level": c.optimization_level,
                "target_language": c.target_language,
                "enable_rag": c.enable_rag,
                "is_default": c.is_default,
                "metadata": c.metadata,
                "created_at": c.created_at.isoformat(),
                "updated_at": c.updated_at.isoformat(),
            }
            for c in configs
        ],
        "total": len(configs),
    })


@router.get("/config/sessions/{config_id}", dependencies=[Depends(require_api_key)])
async def get_session_config(
    config_id: str,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Get a specific session configuration by ID."""
    config_repo = SessionConfigRepository(db)
    config = config_repo.get(config_id)

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session configuration '{config_id}' not found"
        )

    return JSONResponse({
        "id": config.id,
        "name": config.name,
        "user_id": config.user_id,
        "llm_provider": config.llm_provider,
        "llm_model": config.llm_model,
        "tts_provider": config.tts_provider,
        "tts_voice_id": config.tts_voice_id,
        "voice_tuning": config.voice_tuning,
        "system_prompt_id": config.system_prompt_id,
        "system_prompt_text": config.system_prompt_text,
        "optimization_level": config.optimization_level,
        "target_language": config.target_language,
        "enable_rag": config.enable_rag,
        "is_default": config.is_default,
        "metadata": config.metadata,
        "created_at": config.created_at.isoformat(),
        "updated_at": config.updated_at.isoformat(),
    })


@router.get("/config/sessions/default", dependencies=[Depends(require_api_key)])
async def get_default_config(
    user_id: Optional[str] = None,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Get the default session configuration for a user.

    Args:
        user_id: User ID (optional)
    """
    config_repo = SessionConfigRepository(db)
    config = config_repo.get_default(user_id=user_id)

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No default configuration found"
        )

    return JSONResponse({
        "id": config.id,
        "name": config.name,
        "user_id": config.user_id,
        "llm_provider": config.llm_provider,
        "llm_model": config.llm_model,
        "tts_provider": config.tts_provider,
        "tts_voice_id": config.tts_voice_id,
        "voice_tuning": config.voice_tuning,
        "system_prompt_id": config.system_prompt_id,
        "system_prompt_text": config.system_prompt_text,
        "optimization_level": config.optimization_level,
        "target_language": config.target_language,
        "enable_rag": config.enable_rag,
        "is_default": config.is_default,
        "metadata": config.metadata,
        "created_at": config.created_at.isoformat(),
        "updated_at": config.updated_at.isoformat(),
    })


@router.post("/config/sessions", dependencies=[Depends(require_api_key)])
async def create_session_config(
    request: SessionConfigCreate,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Create a new session configuration."""
    config_repo = SessionConfigRepository(db)

    try:
        config = config_repo.create(
            name=request.name,
            user_id=request.user_id,
            llm_provider=request.llm_provider,
            llm_model=request.llm_model,
            tts_provider=request.tts_provider,
            tts_voice_id=request.tts_voice_id,
            voice_tuning=request.voice_tuning,
            system_prompt_id=request.system_prompt_id,
            system_prompt_text=request.system_prompt_text,
            optimization_level=request.optimization_level,
            target_language=request.target_language,
            enable_rag=request.enable_rag,
            is_default=request.is_default,
            metadata=request.metadata,
        )

        return JSONResponse({
            "id": config.id,
            "name": config.name,
            "user_id": config.user_id,
            "llm_provider": config.llm_provider,
            "llm_model": config.llm_model,
            "tts_provider": config.tts_provider,
            "tts_voice_id": config.tts_voice_id,
            "voice_tuning": config.voice_tuning,
            "system_prompt_id": config.system_prompt_id,
            "optimization_level": config.optimization_level,
            "target_language": config.target_language,
            "enable_rag": config.enable_rag,
            "is_default": config.is_default,
            "created_at": config.created_at.isoformat(),
        }, status_code=status.HTTP_201_CREATED)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create session configuration: {str(e)}"
        )


@router.put("/config/sessions/{config_id}", dependencies=[Depends(require_api_key)])
async def update_session_config(
    config_id: str,
    request: SessionConfigUpdate,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Update a session configuration."""
    config_repo = SessionConfigRepository(db)

    try:
        # Build update kwargs from non-None fields
        update_kwargs = {}
        if request.name is not None:
            update_kwargs["name"] = request.name
        if request.llm_provider is not None:
            update_kwargs["llm_provider"] = request.llm_provider
        if request.llm_model is not None:
            update_kwargs["llm_model"] = request.llm_model
        if request.tts_provider is not None:
            update_kwargs["tts_provider"] = request.tts_provider
        if request.tts_voice_id is not None:
            update_kwargs["tts_voice_id"] = request.tts_voice_id
        if request.voice_tuning is not None:
            update_kwargs["voice_tuning"] = request.voice_tuning
        if request.system_prompt_id is not None:
            update_kwargs["system_prompt_id"] = request.system_prompt_id
        if request.system_prompt_text is not None:
            update_kwargs["system_prompt_text"] = request.system_prompt_text
        if request.optimization_level is not None:
            update_kwargs["optimization_level"] = request.optimization_level
        if request.target_language is not None:
            update_kwargs["target_language"] = request.target_language
        if request.enable_rag is not None:
            update_kwargs["enable_rag"] = request.enable_rag
        if request.is_default is not None:
            update_kwargs["is_default"] = request.is_default
        if request.metadata is not None:
            update_kwargs["metadata"] = request.metadata

        config = config_repo.update(config_id, **update_kwargs)

        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session configuration '{config_id}' not found"
            )

        return JSONResponse({
            "id": config.id,
            "name": config.name,
            "user_id": config.user_id,
            "llm_provider": config.llm_provider,
            "llm_model": config.llm_model,
            "tts_provider": config.tts_provider,
            "tts_voice_id": config.tts_voice_id,
            "voice_tuning": config.voice_tuning,
            "system_prompt_id": config.system_prompt_id,
            "optimization_level": config.optimization_level,
            "target_language": config.target_language,
            "enable_rag": config.enable_rag,
            "is_default": config.is_default,
            "updated_at": config.updated_at.isoformat(),
        })

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update session configuration: {str(e)}"
        )


@router.delete("/config/sessions/{config_id}", dependencies=[Depends(require_api_key)])
async def delete_session_config(
    config_id: str,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Delete a session configuration."""
    config_repo = SessionConfigRepository(db)

    try:
        deleted = config_repo.delete(config_id)

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session configuration '{config_id}' not found"
            )

        return JSONResponse({"message": "Session configuration deleted successfully"})

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete session configuration: {str(e)}"
        )

