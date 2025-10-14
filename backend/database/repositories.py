"""Repository layer for database operations."""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from backend.database.models import (
    CostTracking,
    Message,
    Session as SessionModel,
    Document,
    TelephonyTrunk,
    Secret,
)


class SessionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_session(self, language_code: str, optimization_level: str) -> SessionModel:
        session = SessionModel(language_code=language_code, optimization_level=optimization_level)
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def get_session(self, session_id: str) -> Optional[SessionModel]:
        return self.db.query(SessionModel).filter(SessionModel.id == session_id).first()

    def add_message(
        self,
        session_id: str,
        role: str,
        transcript: str,
        translated_text: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> Message:
        message = Message(
            session_id=session_id,
            role=role,
            transcript=transcript,
            translated_text=translated_text,
            details=details or {},
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message


class CostRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def log_cost(self, service: str, cost_usd: float) -> CostTracking:
        record = CostTracking(service=service, cost_usd=cost_usd)
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record


class DocumentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def upsert_document(self, source_url: str, checksum: str, title: str | None = None) -> Document:
        doc = self.db.query(Document).filter(Document.source_url == source_url).first()
        if doc:
            doc.checksum = checksum
            doc.title = title
        else:
            doc = Document(source_url=source_url, checksum=checksum, title=title)
            self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)
        return doc


class SecretRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def store_or_update(self, ref: str, encrypted_value: str) -> Secret:
        secret = self.db.query(Secret).filter(Secret.ref == ref).first()
        if secret:
            secret.encrypted_value = encrypted_value
        else:
            secret = Secret(ref=ref, encrypted_value=encrypted_value)
            self.db.add(secret)
        self.db.commit()
        self.db.refresh(secret)
        return secret

    def get_secret(self, ref: str) -> Secret | None:
        return self.db.query(Secret).filter(Secret.ref == ref).first()

    def delete_secret(self, ref: str) -> None:
        secret = self.get_secret(ref)
        if secret:
            self.db.delete(secret)
            self.db.commit()


class TelephonyRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def upsert_trunk(
        self,
        provider: str,
        trunk_id: str,
        direction: str,
        sip_uri: str,
        transport: str | None,
        metadata: dict | None,
        credential_ref: str | None,
    ) -> TelephonyTrunk:
        trunk = self.db.query(TelephonyTrunk).filter(TelephonyTrunk.trunk_id == trunk_id).first()
        if trunk:
            trunk.provider = provider
            trunk.direction = direction
            trunk.sip_uri = sip_uri
            trunk.transport = transport
            trunk.metadata = metadata or {}
            trunk.credential_ref = credential_ref
        else:
            trunk = TelephonyTrunk(
                provider=provider,
                trunk_id=trunk_id,
                direction=direction,
                sip_uri=sip_uri,
                transport=transport,
                metadata=metadata or {},
                credential_ref=credential_ref,
            )
            self.db.add(trunk)
        self.db.commit()
        self.db.refresh(trunk)
        return trunk

    def list_trunks(self) -> list[TelephonyTrunk]:
        return self.db.query(TelephonyTrunk).all()

    def get_trunk(self, trunk_id: str) -> TelephonyTrunk | None:
        return self.db.query(TelephonyTrunk).filter(TelephonyTrunk.trunk_id == trunk_id).first()

