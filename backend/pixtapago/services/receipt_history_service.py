"""UC005 - Consultar histórico de recebimento e indicadores do painel (T02)."""

from __future__ import annotations

from datetime import date, datetime, timezone

from ..domain.errors import ValidationError
from ..domain.models import ChargeStatus, Receipt
from ..persistence.repositories import ChargeRepository, ReceiptRepository


def _parse_date(raw: str | None) -> str | None:
    if not raw:
        return None
    try:
        return date.fromisoformat(raw).isoformat()
    except ValueError as error:
        raise ValidationError("Critério de busca inválido: informe as datas no formato AAAA-MM-DD.") from error


class ReceiptHistoryService:
    def __init__(self, receipts: ReceiptRepository) -> None:
        self.receipts = receipts

    def search(self, text: str = "", start: str | None = None, end: str | None = None) -> list[Receipt]:
        """Pesquisa por pagador, TXID ou E2E ID e, opcionalmente, por período (UC005 - A2)."""
        start_date, end_date = _parse_date(start), _parse_date(end)
        if start_date and end_date and start_date > end_date:
            raise ValidationError("Critério de busca inválido: a data inicial é posterior à data final.")
        return self.receipts.search(text.strip(), start_date, end_date)


class DashboardService:
    def __init__(self, charges: ChargeRepository, receipts: ReceiptRepository) -> None:
        self.charges = charges
        self.receipts = receipts

    def summary(self) -> dict:
        now = datetime.now(timezone.utc)
        return {
            "receivedToday": self.receipts.total_by_period(now.date().isoformat()),
            "receivedMonth": self.receipts.total_by_period(now.strftime("%Y-%m")),
            "pendingCharges": self.charges.count_by_status(ChargeStatus.ACTIVE),
            "paidCharges": self.charges.count_by_status(ChargeStatus.PAID),
            "recentCharges": [charge.to_dict() for charge in self.charges.list_recent(5)],
        }
