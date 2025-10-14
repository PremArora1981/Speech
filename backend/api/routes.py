"""API routes for FastAPI app."""

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from fastapi.responses import JSONResponse

from backend.services.conversation_pipeline import ConversationPipeline
from backend.services.telephony_service import (
    SIPParticipantRequest,
    TelephonyAdapter,
    LiveKitTelephonyAdapter,
    TelephonyTrunkRegistration,
)
from .dependencies import require_api_key
import json

router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_api_key)])


def get_pipeline() -> ConversationPipeline:
    return ConversationPipeline()


def get_telephony_adapter() -> TelephonyAdapter:
    return LiveKitTelephonyAdapter()


@router.websocket("/voice-session")
async def voice_session(websocket: WebSocket, pipeline: ConversationPipeline = Depends(get_pipeline)):
    await websocket.accept()
    optimization_level: str | None = None
    try:
        while True:
            raw_message = await websocket.receive_text()
            try:
                payload = json.loads(raw_message)
            except json.JSONDecodeError:
                result = await pipeline.process_audio(raw_message, target_language="en-IN")
                await websocket.send_json({"text": result.llm_response})
                continue

            message_type = payload.get("type")
            session_id = payload.get("sessionId") or payload.get("session_id")

            if message_type == "start":
                optimization_level = payload.get("optimizationLevel")
                pipeline.start_session(session_id, optimization_level)
                continue

            if message_type == "audio":
                optimization_level = payload.get("optimizationLevel", optimization_level)
                result = await pipeline.process_audio_chunk(
                    audio_base64=payload.get("audio"),
                    session_id=session_id,
                    timestamp=payload.get("timestamp"),
                    optimization_level=optimization_level,
                )
                if result:
                    await websocket.send_json({"text": result.llm_response})
                continue

            if message_type == "stop":
                optimization_level = payload.get("optimizationLevel", optimization_level)
                await pipeline.finish_session(session_id, optimization_level)
                continue

    except WebSocketDisconnect:
        await websocket.close()


@router.post("/telephony/calls")
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


@router.get("/telephony/trunks")
async def list_trunks(adapter: TelephonyAdapter = Depends(get_telephony_adapter)) -> JSONResponse:
    trunks = await adapter.list_trunks()
    return JSONResponse({"trunks": [trunk.__dict__ for trunk in trunks]})


@router.post("/telephony/trunks")
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


@router.get("/health")
async def health_check() -> JSONResponse:
    return JSONResponse({"status": "ok"}, status_code=status.HTTP_200_OK)

