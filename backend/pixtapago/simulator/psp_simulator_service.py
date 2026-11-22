"""Simulador do PSP pagador (contas fictícias de Pedro e João).

Não faz parte do escopo funcional do PixTáPago: o produto não movimenta
valores. O simulador representa o banco do cliente pagador, que liquida o Pix
e comunica o crédito ao recebedor, papel exercido pela instituição financeira
em produção. Ao liquidar um Pix destinado à chave acompanhada, ele entrega a
confirmação ao PaymentConfirmationService, o mesmo serviço que trata o webhook
do BB.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from uuid import uuid4

from ..domain.errors import NotFoundError, PixAlreadyPaidError, ValidationError
from ..domain.models import NO_TXID, now_iso
from ..domain.pix_payload import parse_pix_payload
from ..persistence.repositories import (
    BankAccountRepository, BankTransactionRepository, ChargeRepository,
)
from ..services.payment_confirmation_service import PaymentConfirmationService

RECEIVER_ACTOR = "dono"


def transaction_view(row: sqlite3.Row, account_id: int) -> dict:
    direction = "OUT" if row["sender_id"] == account_id else "IN"
    return {
        "id": row["id"], "e2eid": row["e2eid"], "txid": row["txid"],
        "amount": row["amount_cents"] / 100, "description": row["description"],
        "paymentMethod": row["payment_method"], "createdAt": row["created_at"],
        "direction": direction,
        "counterparty": row["receiver_name"] if direction == "OUT" else row["sender_name"],
        "counterpartyKey": row["receiver_key"] if direction == "OUT" else row["sender_key"],
    }


class PspSimulatorService:
    def __init__(
        self,
        db: sqlite3.Connection,
        accounts: BankAccountRepository,
        transactions: BankTransactionRepository,
        charges: ChargeRepository,
        confirmation: PaymentConfirmationService,
    ) -> None:
        self.db = db
        self.accounts = accounts
        self.transactions = transactions
        self.charges = charges
        self.confirmation = confirmation

    def account_statement(self, actor: str) -> dict:
        account = self.accounts.find_by_actor(actor)
        if not account:
            raise NotFoundError("Conta não encontrada.")
        return {
            "actor": account["actor"], "name": account["name"], "document": account["document"],
            "pixKey": account["pix_key"], "balance": account["balance_cents"] / 100,
            "transactions": self._history(account["id"]),
        }

    def resolve_key(self, pix_key: str) -> dict:
        receiver = self.accounts.find_by_pix_key(pix_key.strip())
        if not receiver:
            raise NotFoundError("Chave Pix não encontrada.")
        return {"name": receiver["name"], "document": receiver["document"], "pixKey": receiver["pix_key"]}

    def preview_code(self, payload: str) -> dict:
        parsed = parse_pix_payload(payload)  # ValueError -> 400
        receiver, amount, _txid = self._resolve_payload_receiver(parsed)  # NotFoundError -> 404
        return {
            "name": receiver["name"], "document": receiver["document"],
            "pixKey": parsed["pixKey"] or os.getenv("BB_PIX_KEY", receiver["pix_key"]),
            "amount": amount,
        }

    def transfer_to_key(self, actor: str, pix_key: str, amount: float, description: str, idempotency_key: str) -> dict:
        return self._settle(actor, pix_key, amount, description, "PIX_KEY", idempotency_key)

    def pay_code(self, actor: str, payload: str, informed_amount: float, description: str, idempotency_key: str) -> dict:
        parsed = parse_pix_payload(payload)
        receiver, code_amount, txid = self._resolve_payload_receiver(parsed)
        amount = code_amount if code_amount is not None else informed_amount
        return self._settle(actor, receiver["pix_key"], amount, description, "PIX_QR", idempotency_key, txid)

    def _history(self, account_id: int, limit: int = 30) -> list[dict]:
        return [transaction_view(row, account_id) for row in self.transactions.list_for_account(account_id, limit)]

    def _find_transaction(self, account_id: int, e2eid: str) -> dict:
        return next(item for item in self._history(account_id, 100) if item["e2eid"] == e2eid)

    def _resolve_payload_receiver(self, parsed: dict) -> tuple[sqlite3.Row, float | None, str]:
        """Localiza o recebedor de um QR estático ou de uma cobrança dinâmica criada pelo BB."""
        if parsed["pixKey"]:
            receiver = self.accounts.find_by_pix_key(parsed["pixKey"])
            if not receiver:
                raise NotFoundError("Não foi possível localizar o recebedor deste código Pix.")
            return receiver, parsed["amount"], NO_TXID
        charge = self.charges.find_by_copy_paste(parsed["payload"])
        receiver = self.accounts.find_by_actor(RECEIVER_ACTOR)
        if not charge or not receiver:
            raise NotFoundError("Esta cobrança dinâmica não foi gerada pelo PixTáPago.")
        return receiver, charge.amount, charge.txid

    def _settle(self, actor: str, pix_key: str, amount: float, description: str,
                method: str, idempotency_key: str, txid: str = NO_TXID) -> dict:
        sender = self.accounts.find_by_actor(actor)
        receiver = self.accounts.find_by_pix_key(pix_key)
        if not sender:
            raise ValidationError("Conta pagadora não encontrada.")
        if not receiver:
            raise ValidationError("Chave Pix não encontrada.")
        if sender["id"] == receiver["id"]:
            raise ValidationError("A chave informada pertence à própria conta.")
        amount_cents = round(float(amount) * 100)
        if amount_cents <= 0:
            raise ValidationError("Informe um valor maior que zero.")
        previous = self.transactions.find_by_idempotency_key(idempotency_key)
        if previous:
            return self._find_transaction(sender["id"], previous["e2eid"])

        db = self.db
        try:
            db.execute("BEGIN IMMEDIATE")
            if txid != NO_TXID and self.transactions.exists_for_txid(txid):
                db.rollback()
                raise PixAlreadyPaidError("Esta cobrança Pix já foi paga.")
            if self.accounts.balance_cents(sender["id"]) < amount_cents:
                db.rollback()
                raise ValidationError("Saldo insuficiente para concluir o Pix.")
            self.accounts.move_balance(sender["id"], receiver["id"], amount_cents)
            e2eid = f"E00000000{datetime.now(timezone.utc):%Y%m%d%H%M}{uuid4().hex[:11].upper()}"
            paid_at = now_iso()
            self.transactions.add(e2eid, idempotency_key, sender["id"], receiver["id"], amount_cents,
                                  description[:140], method, txid, paid_at)
            if receiver["actor"] == RECEIVER_ACTOR:
                # O PSP comunica o crédito na chave acompanhada, como faria o webhook do BB.
                self.confirmation.register_transaction({
                    "endToEndId": e2eid, "txid": txid, "valor": amount_cents / 100,
                    "horario": paid_at, "pagador": {"nome": sender["name"]},
                    "infoPagador": description[:140],
                })
            db.commit()
        except Exception:
            if db.in_transaction:
                db.rollback()
            raise
        return self._find_transaction(sender["id"], e2eid)
