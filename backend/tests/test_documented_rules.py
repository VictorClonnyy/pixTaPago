"""Regras do relatório de requisitos verificadas sobre a API (UC001, UC004 a UC006, T03)."""

import os
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

os.environ.setdefault("DATABASE_PATH", tempfile.mktemp(suffix=".db"))

from werkzeug.security import generate_password_hash  # noqa: E402

from pixtapago import create_app  # noqa: E402
from pixtapago.persistence.database import get_db  # noqa: E402

BB_CLIENT = "pixtapago.integration.bb_pix_client.BancoDoBrasilPixClient"
app = create_app()


class DocumentedRulesTest(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True, WEBHOOK_SECRET="segredo-de-teste")
        self.client = app.test_client()
        self.assertEqual(
            self.client.post("/api/auth/login", json={"email": "demo@pixtapago.com.br", "password": "pix123"}).status_code,
            200,
        )

    def sync_with(self, payments):
        with patch(f"{BB_CLIENT}.list_received_pix", return_value=payments), \
             patch(f"{BB_CLIENT}.get_charge", return_value={"status": "ACTIVE", "payments": [], "raw": {}}):
            return self.client.post("/api/pix/sync")

    def test_uc001_inactive_user_is_informed_access_is_suspended(self):
        email = f"inativo-{uuid4().hex[:6]}@pixtapago.com.br"
        with app.app_context():
            get_db().execute(
                "INSERT INTO users (name, email, password_hash, role, active) VALUES (?, ?, ?, ?, 0)",
                ("Funcionário Inativo", email, generate_password_hash("senha123"), "Funcionário"),
            )
            get_db().commit()
        anonymous = app.test_client()
        response = anonymous.post("/api/auth/login", json={"email": email, "password": "senha123"})
        self.assertEqual(response.status_code, 403)
        self.assertIn("suspenso", response.get_json()["message"])
        wrong = anonymous.post("/api/auth/login", json={"email": email, "password": "errada"})
        self.assertEqual(wrong.status_code, 401)
        self.assertEqual(anonymous.get("/api/dashboard").status_code, 401)

    def test_uc006_notification_is_persisted_until_read(self):
        e2eid = f"E{uuid4().hex}"
        self.sync_with([{"endToEndId": e2eid, "valor": "15.00", "pagador": {"nome": "Ana"}}])
        unread = self.client.get("/api/notifications?unread=1").get_json()
        notification = next(item for item in unread if item["receipt_e2eid"] == e2eid)
        self.assertEqual(notification["payer_name"], "Ana")
        self.assertEqual(notification["amount"], 15.0)
        self.assertIn("Pix recebido de Ana", notification["message"])

        self.assertEqual(self.client.post(f"/api/notifications/{notification['id']}/read").status_code, 204)
        unread = self.client.get("/api/notifications?unread=1").get_json()
        self.assertFalse(any(item["receipt_e2eid"] == e2eid for item in unread))
        self.assertEqual(self.client.post("/api/notifications/999999/read").status_code, 404)

    def test_uc004_duplicate_transaction_does_not_create_second_notification(self):
        payment = {"endToEndId": f"E{uuid4().hex}", "valor": "3.10"}
        self.sync_with([payment])
        self.sync_with([payment])
        notifications = self.client.get("/api/notifications").get_json()
        self.assertEqual(sum(1 for item in notifications if item["receipt_e2eid"] == payment["endToEndId"]), 1)

    def test_uc004_webhook_rejects_untrusted_origin_and_accepts_valid_secret(self):
        event = {"pix": [{"endToEndId": f"E{uuid4().hex}", "valor": "20.00", "horario": "2026-10-01T12:00:00Z"}]}
        anonymous = app.test_client()
        self.assertEqual(anonymous.post("/api/webhooks/bb/pix", json=event).status_code, 401)
        self.assertEqual(
            anonymous.post("/api/webhooks/bb/pix", json=event, headers={"X-Webhook-Secret": "outro"}).status_code, 401,
        )
        accepted = anonymous.post("/api/webhooks/bb/pix?token=segredo-de-teste", json=event)
        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(accepted.get_json()["processed"], 1)

        app.config.update(WEBHOOK_SECRET="")
        self.assertEqual(anonymous.post("/api/webhooks/bb/pix", json=event).status_code, 401)

    def test_uc005_history_filters_by_period_and_rejects_invalid_criteria(self):
        e2eid = f"E{uuid4().hex}"
        self.sync_with([{"endToEndId": e2eid, "valor": "8.00", "horario": "2026-03-15T09:00:00Z"}])
        inside = self.client.get("/api/receipts?inicio=2026-03-01&fim=2026-03-31").get_json()
        self.assertTrue(any(item["e2eid"] == e2eid for item in inside))
        outside = self.client.get("/api/receipts?inicio=2026-04-01").get_json()
        self.assertFalse(any(item["e2eid"] == e2eid for item in outside))
        self.assertEqual(self.client.get("/api/receipts?inicio=15/03/2026").status_code, 400)
        inverted = self.client.get("/api/receipts?inicio=2026-03-31&fim=2026-03-01")
        self.assertEqual(inverted.status_code, 400)
        self.assertIn("Critério de busca inválido", inverted.get_json()["message"])

    def test_uc008_invalid_amount_and_t03_description_limit(self):
        self.assertEqual(self.client.post("/api/charges", json={"amount": "abc"}).status_code, 400)
        self.assertEqual(self.client.post("/api/charges", json={"amount": -5}).status_code, 400)
        with patch(f"{BB_CLIENT}.create_immediate_charge", return_value={"pixCopyPaste": "payload", "location": None}) as bb:
            charge = self.client.post("/api/charges", json={"amount": 10, "description": "x" * 150}).get_json()
        self.assertEqual(len(charge["description"]), 100)
        self.assertEqual(bb.call_args.kwargs["description"], "x" * 100)

    def test_uc002_integration_failure_does_not_register_charge(self):
        from pixtapago.integration.bb_pix_client import PixIntegrationError
        before = len(self.client.get("/api/charges").get_json())
        with patch(f"{BB_CLIENT}.create_immediate_charge", side_effect=PixIntegrationError("BB indisponível")):
            response = self.client.post("/api/charges", json={"amount": 10})
        self.assertEqual(response.status_code, 502)
        self.assertEqual(len(self.client.get("/api/charges").get_json()), before)

    def test_uc003_integration_failure_keeps_last_known_status(self):
        from pixtapago.integration.bb_pix_client import PixIntegrationError
        with patch(f"{BB_CLIENT}.create_immediate_charge", return_value={"pixCopyPaste": "p-uc003", "location": None}):
            charge = self.client.post("/api/charges", json={"amount": 5}).get_json()
        with patch(f"{BB_CLIENT}.get_charge", side_effect=PixIntegrationError("timeout")):
            response = self.client.get(f"/api/charges/{charge['txid']}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ACTIVE")
        self.assertEqual(self.client.get("/api/charges/inexistente").status_code, 404)


if __name__ == "__main__":
    unittest.main()
