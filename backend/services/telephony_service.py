"""Telephony service abstractions and LiveKit SIP adapter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Any
import json

from livekit import api

from backend.config.settings import settings
from backend.database.repositories import TelephonyRepository, SecretRepository
from backend.utils.secrets import encrypt_secret
from backend.database import SessionLocal


@dataclass
class SIPTrunkConnectionInfo:
    trunk_id: str
    name: str
    direction: str  # inbound | outbound
    sip_uri: str
    transport: str
    provider: str
    metadata: dict[str, Any] | None = None


@dataclass
class SIPParticipantRequest:
    trunk_id: str
    call_to: str
    participant_identity: str
    room_name: str
    wait_until_answered: bool = True


@dataclass
class TelephonyTrunkRegistration:
    provider: str
    trunk_id: str
    direction: str
    sip_uri: str
    transport: str | None = None
    metadata: dict[str, Any] | None = None
    credentials: dict[str, str] | None = None


class TelephonyAdapter(Protocol):
    async def list_trunks(self) -> list[SIPTrunkConnectionInfo]:
        """List available SIP trunks."""

    async def initiate_call(self, request: SIPParticipantRequest) -> None:
        """Initiate an outbound call."""

    async def save_trunk_details(self, registration: TelephonyTrunkRegistration) -> SIPTrunkConnectionInfo:
        """Persist trunk metadata and credentials."""


class LiveKitTelephonyAdapter:
    """Adapter that proxies telephony operations to LiveKit Cloud SIP APIs."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        api_secret: str | None = None,
    ) -> None:
        self.base_url = base_url or settings.livekit_project_url
        self.api_key = api_key or settings.livekit_api_key
        self.api_secret = api_secret or settings.livekit_api_secret
        if not self.base_url or not self.api_key or not self.api_secret:
            raise ValueError("LiveKit credentials are not configured")
        self.client = api.LiveKitAPI(self.base_url, self.api_key, self.api_secret)

    async def list_trunks(self) -> list[SIPTrunkConnectionInfo]:
        outbound = await self.client.sip.list_sip_outbound_trunks(api.ListSIPOutboundTrunksRequest())
        inbound = await self.client.sip.list_sip_inbound_trunks(api.ListSIPInboundTrunksRequest())

        with SessionLocal() as session:
            telephony_repo = TelephonyRepository(session)
            existing = {trunk.trunk_id: trunk for trunk in telephony_repo.list_trunks()}

            trunks: list[SIPTrunkConnectionInfo] = []
            secret_repo = SecretRepository(session)
            for trunk in outbound.outbound_trunks:
                trunks.append(
                    SIPTrunkConnectionInfo(
                        trunk_id=trunk.sip_trunk_id,
                        name=trunk.name,
                        direction="outbound",
                        sip_uri=trunk.address,
                        transport=str(trunk.transport),
                        provider="livekit",
                        metadata={"name": trunk.name},
                    )
                )
                if trunk.sip_trunk_id not in existing:
                    telephony_repo.upsert_trunk(
                        provider="livekit",
                        trunk_id=trunk.sip_trunk_id,
                        direction="outbound",
                        sip_uri=trunk.address,
                        transport=str(trunk.transport),
                        meta_data={"name": trunk.name},
                        credential_ref=None,
                    )

            for trunk in inbound.inbound_trunks:
                trunks.append(
                    SIPTrunkConnectionInfo(
                        trunk_id=trunk.sip_trunk_id,
                        name=trunk.name,
                        direction="inbound",
                        sip_uri=trunk.address,
                        transport=str(trunk.transport),
                        provider="livekit",
                        metadata={"name": trunk.name},
                    )
                )
                if trunk.sip_trunk_id not in existing:
                    telephony_repo.upsert_trunk(
                        provider="livekit",
                        trunk_id=trunk.sip_trunk_id,
                        direction="inbound",
                        sip_uri=trunk.address,
                        transport=str(trunk.transport),
                        meta_data={"name": trunk.name},
                        credential_ref=None,
                    )

        return trunks

    async def initiate_call(self, request: SIPParticipantRequest) -> None:
        await self.client.sip.create_sip_participant(
            api.CreateSIPParticipantRequest(
                room_name=request.room_name,
                sip_trunk_id=request.trunk_id,
                sip_call_to=request.call_to,
                participant_identity=request.participant_identity,
                wait_until_answered=request.wait_until_answered,
            )
        )

    async def save_trunk_details(self, registration: TelephonyTrunkRegistration) -> SIPTrunkConnectionInfo:
        with SessionLocal() as session:
            telephony_repo = TelephonyRepository(session)
            secret_repo = SecretRepository(session)

            credential_ref = None
            if registration.credentials:
                secret_payload = encrypt_secret(json.dumps(registration.credentials))
                ref = f"trunk:{registration.trunk_id}:credentials"
                secret_repo.store_or_update(ref, secret_payload)
                credential_ref = ref

            trunk = telephony_repo.upsert_trunk(
                provider=registration.provider,
                trunk_id=registration.trunk_id,
                direction=registration.direction,
                sip_uri=registration.sip_uri,
                transport=registration.transport,
                meta_data=registration.metadata,
                credential_ref=credential_ref,
            )

            return SIPTrunkConnectionInfo(
                trunk_id=trunk.trunk_id,
                name=trunk.meta_data.get("name") if trunk.meta_data else trunk.trunk_id,
                direction=trunk.direction,
                sip_uri=trunk.sip_uri,
                transport=trunk.transport or "",
                provider=trunk.provider,
                metadata=trunk.meta_data,
            )

