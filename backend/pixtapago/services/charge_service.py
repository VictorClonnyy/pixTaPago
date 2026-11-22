"""UC002 - Gerar cobrança Pix (inclui UC008) e UC003 - Consultar status da cobrança."""

from __future__ import annotations

import logging
import sqlite3
from typing import Callable
from uuid import uuid4

from ..domain.errors import NotFoundError
from ..domain.models import (
    DEFAULT_PAYER_NAME, DESCRIPTION_MAX_LENGTH, Charge, ChargeAmount, now_iso,
)
from ..integration.bb_pix_client import BancoDoBrasilPixClient, PixIntegrationError
from ..persistence.repositories import ChargeRepository, ReceiptRepository
from .payment_confirmation_service import PaymentConfirmationService

logger = logging.getLogger(__name__)


class ChargeService:
    def __init__(
        self,
        db: sqlite3.Connection,
        charges: ChargeRepository,
        receipts: ReceiptRepository,
        confirmation: PaymentConfirmationService,
        client_factory: Callable[[], BancoDoBrasilPixClient] = BancoDoBrasilPixClient,
    ) -> None:
        self.db = db
        self.charges = charges
        self.receipts = receipts
        self.confirmation = confirmation
        self.client_factory = client_factory

    def create(self, amount: object, description: object = "", payer_name: object = None) -> Charge:
        """Cria a cobrança na API Pix e a registra com situação pendente.

        Lança ValidationError (UC008 - A1) ou PixIntegrationError (UC002 - A1/A2);
        nos dois casos nenhuma cobrança é gravada.
        """
        value = ChargeAmount.parse(amount)
        text = str(description or "")[:DESCRIPTION_MAX_LENGTH]
        txid = uuid4().hex
        try:
            pix = self.client_factory().create_immediate_charge(txid=txid, amount=value.value, description=text)
        except PixIntegrationError as error:
            logger.warning("Cobrança não criada no BB: %s", error)
            raise
        self.charges.add(
            txid=txid,
            payer_name=str(payer_name or "") or DEFAULT_PAYER_NAME,
            amount=value.value,
            description=text,
            pix_copy_paste=pix["pixCopyPaste"],
            location=pix.get("location"),
            created_at=now_iso(),
        )
        self.db.commit()
        logger.info("Cobrança %s criada (R$ %.2f).", txid, value.value)
        return self.charges.find_by_txid(txid)

    def list(self) -> list[Charge]:
        return self.charges.list_all()

    def get_status(self, txid: str) -> Charge:
        """Consulta a situação atual junto ao BB e devolve o último estado conhecido.

        Se a integração falhar (UC003 - A2), mantém o estado armazenado e nunca
        apresenta a cobrança como paga sem evidência.
        """
        charge = self.charges.find_by_txid(txid)
        if not charge:
            raise NotFoundError("Cobrança não encontrada.")
        if charge.is_paid and self.receipts.exists_for_txid(txid):
            return charge
        try:
            self.confirmation.refresh_charge(charge, self.client_factory())
            self.db.commit()
            charge = self.charges.find_by_txid(txid)
        except PixIntegrationError as error:
            self.db.rollback()
            logger.warning("Situação da cobrança %s não atualizada: %s", txid, error)
        return charge
