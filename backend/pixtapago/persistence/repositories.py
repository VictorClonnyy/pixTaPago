"""Repositórios: único ponto do sistema que contém instruções SQL.

Cada repositório recebe a conexão da requisição e converte as linhas do banco
em entidades do domínio. O controle de transação (commit/rollback) pertence à
camada de serviços.
"""

from __future__ import annotations

import sqlite3

from ..domain.models import Charge, ChargeStatus, Notification, Receipt, User


class UserRepository:
    def __init__(self, db: sqlite3.Connection) -> None:
        self.db = db

    def find_by_email(self, email: str) -> User | None:
        row = self.db.execute("SELECT * FROM users WHERE lower(email) = lower(?)", (email,)).fetchone()
        return User.from_row(row) if row else None

    def find_by_id(self, user_id: int) -> User | None:
        row = self.db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return User.from_row(row) if row else None


class ChargeRepository:
    def __init__(self, db: sqlite3.Connection) -> None:
        self.db = db

    def add(self, txid: str, payer_name: str, amount: float, description: str,
            pix_copy_paste: str, location: str | None, created_at: str) -> None:
        self.db.execute(
            """INSERT INTO charges
               (txid, payer_name, amount, description, status, pix_copy_paste, location, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (txid, payer_name, amount, description, ChargeStatus.ACTIVE.value,
             pix_copy_paste, location, created_at, created_at),
        )

    def find_by_txid(self, txid: str) -> Charge | None:
        row = self.db.execute("SELECT * FROM charges WHERE txid = ?", (txid,)).fetchone()
        return Charge.from_row(row) if row else None

    def find_by_copy_paste(self, payload: str) -> Charge | None:
        row = self.db.execute("SELECT * FROM charges WHERE pix_copy_paste = ?", (payload,)).fetchone()
        return Charge.from_row(row) if row else None

    def list_all(self) -> list[Charge]:
        rows = self.db.execute("SELECT * FROM charges ORDER BY created_at DESC").fetchall()
        return [Charge.from_row(row) for row in rows]

    def list_recent(self, limit: int = 5) -> list[Charge]:
        rows = self.db.execute("SELECT * FROM charges ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [Charge.from_row(row) for row in rows]

    def list_awaiting_confirmation(self, limit: int = 30) -> list[Charge]:
        """Cobranças pendentes ou pagas cujo recebimento ainda não foi registrado."""
        rows = self.db.execute(
            """SELECT * FROM charges
               WHERE status = 'ACTIVE'
                  OR (status = 'PAID' AND NOT EXISTS (
                        SELECT 1 FROM receipts WHERE receipts.txid = charges.txid
                     ))
               ORDER BY created_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        return [Charge.from_row(row) for row in rows]

    def update_status(self, txid: str, status: str, updated_at: str) -> None:
        self.db.execute(
            "UPDATE charges SET status = ?, updated_at = ? WHERE txid = ?",
            (status, updated_at, txid),
        )

    def count_by_status(self, status: ChargeStatus) -> int:
        return self.db.execute(
            "SELECT COUNT(*) value FROM charges WHERE status = ?", (status.value,)
        ).fetchone()["value"]


class ReceiptRepository:
    def __init__(self, db: sqlite3.Connection) -> None:
        self.db = db

    def add_if_absent(self, e2eid: str, txid: str | None, payer_name: str, amount: float,
                      origin: str, description: str, received_at: str) -> bool:
        """Grava o recebimento uma única vez por EndToEndId. Retorna True se gravou."""
        cursor = self.db.execute(
            """INSERT OR IGNORE INTO receipts
               (e2eid, txid, payer_name, amount, origin, description, received_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (e2eid, txid, payer_name, amount, origin, description, received_at),
        )
        return cursor.rowcount == 1

    def exists_for_txid(self, txid: str) -> bool:
        return self.db.execute("SELECT 1 FROM receipts WHERE txid = ? LIMIT 1", (txid,)).fetchone() is not None

    def search(self, text: str = "", start_date: str | None = None, end_date: str | None = None) -> list[Receipt]:
        clauses: list[str] = []
        params: list[str] = []
        if text:
            clauses.append("(payer_name LIKE ? OR txid LIKE ? OR e2eid LIKE ?)")
            params.extend([f"%{text}%"] * 3)
        if start_date:
            clauses.append("substr(received_at, 1, 10) >= ?")
            params.append(start_date)
        if end_date:
            clauses.append("substr(received_at, 1, 10) <= ?")
            params.append(end_date)
        sql = "SELECT * FROM receipts"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY received_at DESC"
        return [Receipt.from_row(row) for row in self.db.execute(sql, params).fetchall()]

    def total_by_period(self, prefix: str) -> float:
        """Soma os recebimentos cuja data começa com o prefixo (AAAA-MM-DD ou AAAA-MM)."""
        value = self.db.execute(
            "SELECT COALESCE(SUM(amount), 0) value FROM receipts WHERE substr(received_at, 1, ?) = ?",
            (len(prefix), prefix),
        ).fetchone()["value"]
        return float(value)


class NotificationRepository:
    _SELECT = """SELECT n.id, n.receipt_e2eid, n.message, n.created_at, n.read_at,
                        r.payer_name, r.amount, r.txid, r.received_at
                 FROM notifications n
                 JOIN receipts r ON r.e2eid = n.receipt_e2eid"""

    def __init__(self, db: sqlite3.Connection) -> None:
        self.db = db

    def add_if_absent(self, receipt_e2eid: str, message: str, created_at: str) -> bool:
        cursor = self.db.execute(
            "INSERT OR IGNORE INTO notifications (receipt_e2eid, message, created_at) VALUES (?, ?, ?)",
            (receipt_e2eid, message, created_at),
        )
        return cursor.rowcount == 1

    def list(self, only_unread: bool = False, limit: int = 20) -> list[Notification]:
        sql = self._SELECT + (" WHERE n.read_at IS NULL" if only_unread else "")
        sql += " ORDER BY n.id DESC LIMIT ?"
        return [Notification.from_row(row) for row in self.db.execute(sql, (limit,)).fetchall()]

    def mark_read(self, notification_id: int, read_at: str) -> bool:
        cursor = self.db.execute(
            "UPDATE notifications SET read_at = COALESCE(read_at, ?) WHERE id = ?",
            (read_at, notification_id),
        )
        return cursor.rowcount == 1

    def mark_all_read(self, read_at: str) -> int:
        return self.db.execute(
            "UPDATE notifications SET read_at = ? WHERE read_at IS NULL", (read_at,)
        ).rowcount


class BankAccountRepository:
    """Contas fictícias do simulador de PSP pagador."""

    def __init__(self, db: sqlite3.Connection) -> None:
        self.db = db

    def find_by_actor(self, actor: str) -> sqlite3.Row | None:
        return self.db.execute("SELECT * FROM bank_accounts WHERE actor = ?", (actor,)).fetchone()

    def find_by_pix_key(self, pix_key: str) -> sqlite3.Row | None:
        return self.db.execute(
            "SELECT * FROM bank_accounts WHERE lower(pix_key) = lower(?)", (pix_key,)
        ).fetchone()

    def balance_cents(self, account_id: int) -> int:
        return self.db.execute(
            "SELECT balance_cents FROM bank_accounts WHERE id = ?", (account_id,)
        ).fetchone()["balance_cents"]

    def move_balance(self, sender_id: int, receiver_id: int, amount_cents: int) -> None:
        self.db.execute("UPDATE bank_accounts SET balance_cents = balance_cents - ? WHERE id = ?", (amount_cents, sender_id))
        self.db.execute("UPDATE bank_accounts SET balance_cents = balance_cents + ? WHERE id = ?", (amount_cents, receiver_id))


class BankTransactionRepository:
    def __init__(self, db: sqlite3.Connection) -> None:
        self.db = db

    def find_by_idempotency_key(self, key: str) -> sqlite3.Row | None:
        return self.db.execute("SELECT * FROM bank_transactions WHERE idempotency_key = ?", (key,)).fetchone()

    def exists_for_txid(self, txid: str) -> bool:
        return self.db.execute(
            "SELECT 1 FROM bank_transactions WHERE txid = ? LIMIT 1", (txid,)
        ).fetchone() is not None

    def add(self, e2eid: str, idempotency_key: str, sender_id: int, receiver_id: int,
            amount_cents: int, description: str, method: str, txid: str, created_at: str) -> None:
        self.db.execute(
            """INSERT INTO bank_transactions
               (e2eid, idempotency_key, sender_id, receiver_id, amount_cents, description, payment_method, txid, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (e2eid, idempotency_key, sender_id, receiver_id, amount_cents, description, method, txid, created_at),
        )

    def list_for_account(self, account_id: int, limit: int = 30) -> list[sqlite3.Row]:
        return self.db.execute(
            """SELECT t.*, sender.name sender_name, sender.pix_key sender_key,
                             receiver.name receiver_name, receiver.pix_key receiver_key
               FROM bank_transactions t
               JOIN bank_accounts sender ON sender.id = t.sender_id
               JOIN bank_accounts receiver ON receiver.id = t.receiver_id
               WHERE t.sender_id = ? OR t.receiver_id = ?
               ORDER BY t.created_at DESC, t.id DESC LIMIT ?""",
            (account_id, account_id, limit),
        ).fetchall()
