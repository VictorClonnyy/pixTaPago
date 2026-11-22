"""UC006 - Notificar confirmação de pagamento.

A notificação é um aviso interno persistido: se nenhum usuário estiver com a
sessão aberta no momento do recebimento, o aviso permanece pendente e é
apresentado no próximo acesso (UC006 - A1).
"""

from __future__ import annotations

import logging
import sqlite3

from ..domain.errors import NotFoundError
from ..domain.models import Notification, now_iso
from ..persistence.repositories import NotificationRepository

logger = logging.getLogger(__name__)


def format_brl(value: float) -> str:
    text = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {text}"


class NotificationService:
    def __init__(self, db: sqlite3.Connection, notifications: NotificationRepository) -> None:
        self.db = db
        self.notifications = notifications

    def notify_payment(self, receipt_e2eid: str, payer_name: str, amount: float) -> bool:
        """Gera o aviso da transação registrada. Não confirma a transação do banco."""
        created = self.notifications.add_if_absent(
            receipt_e2eid, f"Pix recebido de {payer_name}: {format_brl(amount)}", now_iso()
        )
        if created:
            logger.info("Notificação gerada para o recebimento %s.", receipt_e2eid)
        return created

    def list(self, only_unread: bool = False) -> list[Notification]:
        return self.notifications.list(only_unread=only_unread)

    def mark_read(self, notification_id: int) -> None:
        if not self.notifications.mark_read(notification_id, now_iso()):
            raise NotFoundError("Notificação não encontrada.")
        self.db.commit()

    def mark_all_read(self) -> int:
        updated = self.notifications.mark_all_read(now_iso())
        self.db.commit()
        return updated
