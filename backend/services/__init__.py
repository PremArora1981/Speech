"""Telephony service abstractions and LiveKit SIP adapter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class SIPTrunkConnectionInfo:
    trunk_id: str
    name: str
    direction: str  # inbound | outbound
    sip_uri: str
    transport: str


@dataclass
class SIPParticipantRequest:
    trunk_id: str
    call_to: str
    participant_identity: str
    room_name: str
    wait_until_answered: bool = True


class TelephonyAdapter(Protocol):
    async def list_trunks(self) -> list[SIPTrunkConnectionInfo]:
        ...

    async def initiate_call(self, request: SIPParticipantRequest) -> None:
        ...
"""Service layer exports."""

"""Service layer exports."""

from .tts_service import TTSOrchestrator
from .telephony_service import (
    TelephonyAdapter,
    SIPTrunkConnectionInfo,
    SIPParticipantRequest,
    LiveKitTelephonyAdapter,
)

__all__ = [
    "TTSOrchestrator",
    "TelephonyAdapter",
    "SIPTrunkConnectionInfo",
    "SIPParticipantRequest",
    "LiveKitTelephonyAdapter",
]

