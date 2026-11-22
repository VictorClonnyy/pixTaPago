"""Composição das dependências: monta os serviços sobre a conexão da requisição."""

from __future__ import annotations

from ..persistence.database import get_db
from ..persistence.repositories import (
    BankAccountRepository, BankTransactionRepository, ChargeRepository,
    NotificationRepository, ReceiptRepository, UserRepository,
)
from ..services.auth_service import AuthService
from ..services.charge_service import ChargeService
from ..services.notification_service import NotificationService
from ..services.payment_confirmation_service import PaymentConfirmationService
from ..services.receipt_history_service import DashboardService, ReceiptHistoryService
from ..simulator.psp_simulator_service import PspSimulatorService


def auth_service() -> AuthService:
    return AuthService(UserRepository(get_db()))


def notification_service() -> NotificationService:
    db = get_db()
    return NotificationService(db, NotificationRepository(db))


def payment_confirmation_service() -> PaymentConfirmationService:
    db = get_db()
    return PaymentConfirmationService(db, ChargeRepository(db), ReceiptRepository(db), notification_service())


def charge_service() -> ChargeService:
    db = get_db()
    return ChargeService(db, ChargeRepository(db), ReceiptRepository(db), payment_confirmation_service())


def receipt_history_service() -> ReceiptHistoryService:
    return ReceiptHistoryService(ReceiptRepository(get_db()))


def dashboard_service() -> DashboardService:
    db = get_db()
    return DashboardService(ChargeRepository(db), ReceiptRepository(db))


def psp_simulator_service() -> PspSimulatorService:
    db = get_db()
    return PspSimulatorService(
        db, BankAccountRepository(db), BankTransactionRepository(db),
        ChargeRepository(db), payment_confirmation_service(),
    )
