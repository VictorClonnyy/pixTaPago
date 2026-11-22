"""Entidades e objetos de valor do domínio do PixTáPago.

As classes deste módulo não dependem de Flask, de banco de dados nem da API do
Banco do Brasil. Elas representam os conceitos documentados na seção 2 do
relatório (cobrança, recebimento, notificação e usuário) e as regras que os
acompanham.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping

from .errors import ValidationError

# Valor usado pela especificação Pix quando um pagamento não possui TXID.
NO_TXID = "***"
DESCRIPTION_MAX_LENGTH = 100
DEFAULT_PAYER_NAME = "Cliente não informado"
UNKNOWN_PAYER_NAME = "Pagador não informado"


def now_iso() -> str:
    """Data e hora atuais em UTC, no formato ISO 8601 usado na persistência."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class ChargeStatus(str, Enum):
    """Situações de uma cobrança (RF013): pendente, paga, expirada ou cancelada."""

    ACTIVE = "ACTIVE"
    PAID = "PAID"
    EXPIRED = "EXPIRED"
    CANCELED = "CANCELED"


class ReceiptOrigin(str, Enum):
    """Forma de recebimento: cobrança gerada pelo sistema ou Pix direto na chave."""

    CHARGE = "Cobrança Pix"
    PIX_KEY = "Pix chave"


class PaymentMethod(str, Enum):
    """Meio usado pelo pagador no simulador de PSP."""

    PIX_KEY = "PIX_KEY"
    PIX_QR = "PIX_QR"


@dataclass(frozen=True)
class ChargeAmount:
    """Objeto de valor do UC008 - Informar valor cobrado."""

    value: float

    @classmethod
    def parse(cls, raw: Any) -> "ChargeAmount":
        try:
            value = round(float(raw), 2)
        except (TypeError, ValueError):
            value = 0
        if value <= 0:
            raise ValidationError("Informe um valor maior que zero.")
        return cls(value)

    def to_cents(self) -> int:
        return round(self.value * 100)


def normalize_txid(raw: Any) -> str | None:
    """Converte o TXID recebido do BB em None quando o Pix não tem cobrança."""
    txid = str(raw or "").strip()
    if not txid or set(txid) == {"*"}:
        return None
    return txid


@dataclass
class User:
    id: int
    name: str
    email: str
    role: str
    active: bool = True
    password_hash: str = ""

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "User":
        return cls(
            id=row["id"], name=row["name"], email=row["email"], role=row["role"],
            active=bool(row["active"]) if "active" in row.keys() else True,
            password_hash=row["password_hash"] if "password_hash" in row.keys() else "",
        )

    def to_public_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "email": self.email, "role": self.role}


@dataclass
class Charge:
    """Cobrança Pix imediata criada na API Pix v2 do Banco do Brasil."""

    id: int
    txid: str
    payer_name: str
    amount: float
    description: str
    status: str
    pix_copy_paste: str
    location: str | None
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "Charge":
        data = dict(row)
        data["amount"] = float(data["amount"])
        return cls(**data)

    @property
    def is_pending(self) -> bool:
        return self.status == ChargeStatus.ACTIVE.value

    @property
    def is_paid(self) -> bool:
        return self.status == ChargeStatus.PAID.value

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Receipt:
    """Transação Pix confirmada (recebimento), com ou sem cobrança associada."""

    id: int
    e2eid: str
    txid: str | None
    payer_name: str
    amount: float
    origin: str
    description: str
    received_at: str

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "Receipt":
        data = dict(row)
        data["amount"] = float(data["amount"])
        return cls(**data)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Notification:
    """Aviso interno de pagamento confirmado (UC006)."""

    id: int
    receipt_e2eid: str
    message: str
    created_at: str
    read_at: str | None
    payer_name: str
    amount: float
    txid: str | None
    received_at: str

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "Notification":
        data = dict(row)
        data["amount"] = float(data["amount"])
        return cls(**data)

    def to_dict(self) -> dict:
        return asdict(self)
