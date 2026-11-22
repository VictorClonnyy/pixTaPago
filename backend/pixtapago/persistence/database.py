"""Conexão SQLite por requisição, criação do esquema e dados iniciais."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from flask import Flask, current_app, g
from werkzeug.security import generate_password_hash

from ..domain.models import ReceiptOrigin, now_iso

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def get_db() -> sqlite3.Connection:
    """Retorna a conexão da requisição atual, abrindo-a sob demanda."""
    if "db" not in g:
        Path(current_app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(_error=None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_app(app: Flask) -> None:
    app.teardown_appcontext(close_db)
    init_db(app)


def init_db(app: Flask) -> None:
    """Cria as tabelas, garante os dados de demonstração e aplica ajustes de dados."""
    with app.app_context(), closing(get_db()) as db:
        db.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        _seed_demo_data(db, app.config["PIX_KEY"])
        _remove_legacy_mock_data(db)
        _reconcile_bank_payments(db)
        _reclassify_standalone_pix(db)
        db.commit()


def _seed_demo_data(db: sqlite3.Connection, owner_pix_key: str) -> None:
    if not db.execute("SELECT 1 FROM users LIMIT 1").fetchone():
        db.execute(
            "INSERT INTO users (name, email, password_hash, role, active) VALUES (?, ?, ?, ?, 1)",
            ("Usuário Demonstração", "demo@pixtapago.com.br", generate_password_hash("pix123"), "Administrador"),
        )
    created = now_iso()
    # Contas do simulador de PSP: João recebe na chave configurada do BB, Pedro paga.
    db.execute(
        """INSERT INTO bank_accounts
           (actor, name, document, pix_key, balance_cents, created_at)
           VALUES ('dono', 'João', '***.482.910-**', ?, 850000, ?)
           ON CONFLICT(actor) DO UPDATE SET pix_key = excluded.pix_key""",
        (owner_pix_key, created),
    )
    db.execute(
        """INSERT OR IGNORE INTO bank_accounts
           (actor, name, document, pix_key, balance_cents, created_at)
           VALUES ('cliente', 'Pedro', '***.715.306-**', 'pedro@bancoaurora.com.br', 325000, ?)""",
        (created,),
    )


def _remove_legacy_mock_data(db: sqlite3.Connection) -> None:
    """Remove somente registros reconhecidamente gerados pelo simulador antigo."""
    db.execute(
        """DELETE FROM receipts WHERE txid IN (
               SELECT txid FROM charges
               WHERE location LIKE 'mock://%' OR pix_copy_paste LIKE '%PIXTA-PAGO-SANDBOX%'
           )"""
    )
    db.execute(
        """DELETE FROM charges
           WHERE location LIKE 'mock://%' OR pix_copy_paste LIKE '%PIXTA-PAGO-SANDBOX%'"""
    )


def _reconcile_bank_payments(db: sqlite3.Connection) -> None:
    """Recupera pagamentos do simulador concluídos antes da vinculação automática da cobrança."""
    rows = db.execute(
        """SELECT t.e2eid, t.txid, t.amount_cents, t.description, t.created_at,
                  sender.name AS payer_name
           FROM bank_transactions t
           JOIN bank_accounts sender ON sender.id = t.sender_id
           JOIN charges charge ON charge.txid = t.txid
           WHERE t.txid <> '***'"""
    ).fetchall()
    for row in rows:
        db.execute(
            "UPDATE charges SET status = 'PAID', updated_at = ? WHERE txid = ?",
            (row["created_at"], row["txid"]),
        )
        db.execute(
            """INSERT OR IGNORE INTO receipts
               (e2eid, txid, payer_name, amount, origin, description, received_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                row["e2eid"], row["txid"], row["payer_name"], row["amount_cents"] / 100,
                ReceiptOrigin.CHARGE.value, row["description"], row["created_at"],
            ),
        )


def _reclassify_standalone_pix(db: sqlite3.Connection) -> None:
    """Distingue Pix por chave de cobranças criadas por este sistema."""
    db.execute(
        """UPDATE receipts SET origin = 'Pix chave'
           WHERE origin = 'Pix avulso'
              OR (origin = 'Cobrança Pix' AND NOT EXISTS (
                    SELECT 1 FROM charges WHERE charges.txid = receipts.txid
                 ))"""
    )
