"""UC004 - Registrar transação confirmada (inclui UC006 - Notificar confirmação).

As confirmações chegam por três caminhos, todos tratados pelo mesmo método
``register_transaction``:

* webhook da API Pix do BB (caminho preferencial, ambiente público);
* consulta periódica ``GET /pix`` e ``GET /cob/{txid}`` (contingência);
* simulador de PSP, que representa o banco do pagador nas demonstrações.
"""

from __future__ import annotations

import logging
import sqlite3
from typing import Callable

from ..domain.models import (
    UNKNOWN_PAYER_NAME, Charge, ChargeStatus, ReceiptOrigin, normalize_txid, now_iso,
)
from ..integration.bb_pix_client import BancoDoBrasilPixClient, PixIntegrationError
from ..persistence.repositories import ChargeRepository, ReceiptRepository
from .notification_service import NotificationService

logger = logging.getLogger(__name__)


class PaymentConfirmationService:
    def __init__(
        self,
        db: sqlite3.Connection,
        charges: ChargeRepository,
        receipts: ReceiptRepository,
        notifier: NotificationService,
        client_factory: Callable[[], BancoDoBrasilPixClient] = BancoDoBrasilPixClient,
    ) -> None:
        self.db = db
        self.charges = charges
        self.receipts = receipts
        self.notifier = notifier
        self.client_factory = client_factory

    def register_transaction(
        self,
        event: dict,
        fallback_txid: str | None = None,
        fallback_payer_name: str | None = None,
    ) -> bool:
        """Persiste uma confirmação uma única vez, usando o EndToEndId.

        Retorna True quando a transação é nova. Não executa commit: quem chama
        controla a transação do banco de dados.
        """
        e2eid = str(event.get("endToEndId") or "").strip()
        if not e2eid:
            logger.warning("Confirmação descartada: mensagem sem EndToEndId.")
            return False

        txid = normalize_txid(event.get("txid") or fallback_txid)
        try:
            amount = float(event.get("valor", 0))
        except (TypeError, ValueError):
            amount = 0
        linked_charge = self.charges.find_by_txid(txid) if txid else None
        if txid and not linked_charge:
            # UC004 - A3: cobrança indicada não localizada; registra sem vínculo.
            logger.info("Recebimento %s com TXID sem cobrança local; registrado sem vínculo.", e2eid)

        payer = (event.get("pagador") or {}).get("nome") or fallback_payer_name
        if not payer and linked_charge:
            payer = linked_charge.payer_name
        payer = payer or UNKNOWN_PAYER_NAME
        received_at = event.get("horario") or now_iso()

        created = self.receipts.add_if_absent(
            e2eid=e2eid,
            txid=txid,
            payer_name=payer,
            amount=amount,
            origin=(ReceiptOrigin.CHARGE if linked_charge else ReceiptOrigin.PIX_KEY).value,
            description=event.get("infoPagador", ""),
            received_at=received_at,
        )
        if linked_charge:
            self.charges.update_status(linked_charge.txid, ChargeStatus.PAID.value, received_at)
        if created:
            logger.info("Recebimento %s registrado.", e2eid)
            self.notifier.notify_payment(e2eid, payer, amount)
        else:
            # UC004 - A1: transação já registrada; não gera novo aviso.
            logger.debug("Recebimento %s já registrado; ignorado.", e2eid)
        return created

    def refresh_charge(self, charge: Charge, client: BancoDoBrasilPixClient) -> int:
        """Atualiza a cobrança local a partir da consulta oficial GET /cob/{txid}."""
        remote = client.get_charge(charge.txid, fallback_status=charge.status)
        new_receipts = 0
        for payment in remote["payments"]:
            if self.register_transaction(payment, charge.txid, charge.payer_name):
                new_receipts += 1
        if remote["status"] != charge.status:
            self.charges.update_status(charge.txid, remote["status"], now_iso())
            logger.info("Cobrança %s: situação %s -> %s.", charge.txid, charge.status, remote["status"])
        return new_receipts

    def synchronize(self) -> dict:
        """Consulta periódica de contingência, usada quando o webhook não alcança o sistema."""
        pending = self.charges.list_awaiting_confirmation()
        client = self.client_factory()
        checked = new_receipts = failures = 0
        try:
            for payment in client.list_received_pix():
                if self.register_transaction(payment):
                    new_receipts += 1
            checked += 1
        except PixIntegrationError as error:
            failures += 1
            logger.warning("Falha ao consultar Pix recebidos: %s", error)
        for charge in pending:
            try:
                new_receipts += self.refresh_charge(charge, client)
                checked += 1
            except PixIntegrationError as error:
                failures += 1
                logger.warning("Falha ao consultar a cobrança %s: %s", charge.txid, error)
        self.db.commit()
        return {"checked": checked, "newReceipts": new_receipts, "failures": failures}

    def process_webhook(self, events: list[dict]) -> int:
        processed = sum(1 for event in events if self.register_transaction(event))
        self.db.commit()
        return processed
