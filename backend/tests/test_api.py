import os
import tempfile
import unittest
from uuid import uuid4
from unittest.mock import patch

os.environ["DATABASE_PATH"] = tempfile.mktemp(suffix=".db")

from pixtapago import create_app  # noqa: E402
from pixtapago.domain.pix_payload import create_static_pix_payload, crc16_ccitt, emv_field  # noqa: E402


app = create_app()


class PixTaPagoApiTest(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def login(self):
        return self.client.post("/api/auth/login", json={"email": "demo@pixtapago.com.br", "password": "pix123"})

    def test_login_and_charge_flow(self):
        self.assertEqual(self.login().status_code, 200)
        with patch("pixtapago.integration.bb_pix_client.BancoDoBrasilPixClient.create_immediate_charge", return_value={"pixCopyPaste": "payload-bb", "location": "https://bb.test/location"}):
            created = self.client.post("/api/charges", json={"amount": 42.90, "description": "Teste"})
        self.assertEqual(created.status_code, 201)
        charge = created.get_json()
        self.assertEqual(charge["status"], "ACTIVE")
        self.assertEqual(charge["pix_copy_paste"], "payload-bb")

    def test_local_payment_simulation_does_not_exist(self):
        self.assertEqual(self.login().status_code, 200)
        response = self.client.post("/api/charges/qualquer/simulate-payment")
        self.assertEqual(response.status_code, 404)

    def test_protected_route(self):
        self.assertEqual(self.client.get("/api/dashboard").status_code, 401)

    def test_official_sync_records_receipt_only_once(self):
        self.assertEqual(self.login().status_code, 200)
        with patch("pixtapago.integration.bb_pix_client.BancoDoBrasilPixClient.create_immediate_charge", return_value={"pixCopyPaste": "payload-sync", "location": "https://bb.test/sync"}):
            charge = self.client.post("/api/charges", json={"amount": 17.35, "payerName": "Maria"}).get_json()
        payment = {
            "endToEndId": f"E{uuid4().hex}", "txid": charge["txid"],
            "valor": "17.35", "horario": "2026-09-13T10:30:00Z",
            "infoPagador": "Pedido pago",
        }
        remote = {"status": "PAID", "payments": [payment], "raw": {"status": "CONCLUIDA"}}
        with patch("pixtapago.integration.bb_pix_client.BancoDoBrasilPixClient.list_received_pix", return_value=[payment]), \
             patch("pixtapago.integration.bb_pix_client.BancoDoBrasilPixClient.get_charge", return_value=remote):
            first = self.client.post("/api/pix/sync")
            second = self.client.post("/api/pix/sync")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.get_json()["newReceipts"], 1)
        self.assertEqual(second.get_json()["newReceipts"], 0)
        updated = self.client.get(f"/api/charges/{charge['txid']}").get_json()
        self.assertEqual(updated["status"], "PAID")
        receipts = self.client.get("/api/receipts").get_json()
        saved = next(item for item in receipts if item["e2eid"] == payment["endToEndId"])
        self.assertEqual(saved["payer_name"], "Maria")
        self.assertEqual(saved["amount"], 17.35)

    def test_standalone_pix_is_recorded_without_local_charge(self):
        self.assertEqual(self.login().status_code, 200)
        payment = {
            "endToEndId": f"E{uuid4().hex}",
            "txid": f"BANK{uuid4().hex[:20]}",
            "valor": "9.75",
            "horario": "2026-09-13T11:00:00Z",
            "pagador": {"nome": "Cliente externo"},
        }
        with patch("pixtapago.integration.bb_pix_client.BancoDoBrasilPixClient.list_received_pix", return_value=[payment]), \
             patch("pixtapago.integration.bb_pix_client.BancoDoBrasilPixClient.get_charge", return_value={"status": "ACTIVE", "payments": [], "raw": {}}):
            response = self.client.post("/api/pix/sync")
        self.assertEqual(response.status_code, 200)
        receipts = self.client.get("/api/receipts").get_json()
        saved = next(item for item in receipts if item["e2eid"] == payment["endToEndId"])
        self.assertEqual(saved["origin"], "Pix chave")
        self.assertEqual(saved["payer_name"], "Cliente externo")

    def test_bank_pix_by_key_updates_both_accounts(self):
        before_pedro = self.client.get("/api/bank/accounts/cliente").get_json()
        before_joao = self.client.get("/api/bank/accounts/dono").get_json()
        response = self.client.post("/api/bank/accounts/cliente/pix/transfer", json={
            "pixKey": before_joao["pixKey"], "amount": 25.50,
            "description": "Almoço", "idempotencyKey": uuid4().hex,
        })
        self.assertEqual(response.status_code, 201)
        transaction = response.get_json()
        self.assertEqual(transaction["direction"], "OUT")
        self.assertEqual(transaction["counterparty"], "João")
        after_pedro = self.client.get("/api/bank/accounts/cliente").get_json()
        after_joao = self.client.get("/api/bank/accounts/dono").get_json()
        self.assertAlmostEqual(after_pedro["balance"], before_pedro["balance"] - 25.50)
        self.assertAlmostEqual(after_joao["balance"], before_joao["balance"] + 25.50)
        self.assertEqual(after_joao["transactions"][0]["counterparty"], "Pedro")
        self.assertEqual(after_joao["transactions"][0]["direction"], "IN")
        self.assertEqual(self.login().status_code, 200)
        receipts = self.client.get("/api/receipts").get_json()
        receipt = next(item for item in receipts if item["e2eid"] == transaction["e2eid"])
        self.assertEqual(receipt["origin"], "Pix chave")
        self.assertEqual(receipt["payer_name"], "Pedro")
        self.assertIsNone(receipt["txid"])

    def test_bank_pix_copy_and_paste_flow(self):
        joao = self.client.get("/api/bank/accounts/dono").get_json()
        pix_code = create_static_pix_payload(joao["pixKey"], joao["name"])
        preview = self.client.post("/api/bank/pix/preview", json={"pix": pix_code})
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview.get_json()["name"], "João")
        payment = self.client.post("/api/bank/accounts/cliente/pix/pay", json={
            "pix": pix_code, "amount": 12.75,
            "description": "Pagamento por QR", "idempotencyKey": uuid4().hex,
        })
        self.assertEqual(payment.status_code, 201)
        self.assertEqual(payment.get_json()["paymentMethod"], "PIX_QR")

    def test_bank_reads_dynamic_copy_and_paste_returned_by_bb(self):
        self.assertEqual(self.login().status_code, 200)
        location = "qrcodepix-h.bb.com.br/pix/v2/12345678-1234-1234-1234-123456789012"
        merchant = emv_field("00", "BR.GOV.BCB.PIX") + emv_field("25", location)
        code_without_crc = (
            emv_field("00", "01") + emv_field("01", "12") + emv_field("26", merchant)
            + emv_field("52", "0000") + emv_field("53", "986") + emv_field("58", "BR")
            + emv_field("59", "JOAO") + emv_field("60", "SAO PAULO")
            + emv_field("62", emv_field("05", "***")) + "6304"
        )
        pix_code = code_without_crc + crc16_ccitt(code_without_crc)

        with patch("pixtapago.integration.bb_pix_client.BancoDoBrasilPixClient.create_immediate_charge", return_value={"pixCopyPaste": pix_code, "location": f"https://{location}"}):
            charge = self.client.post("/api/charges", json={"amount": 31.20, "description": "Pedido"}).get_json()

        preview = self.client.post("/api/bank/pix/preview", json={"pix": pix_code})
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview.get_json()["name"], "João")
        self.assertEqual(preview.get_json()["amount"], 31.20)
        self.assertEqual(preview.get_json()["pixKey"], os.environ.get("BB_PIX_KEY", "hmtestes2@bb.com.br"))

        payment_payload = {
            "pix": pix_code, "amount": 0,
            "description": "Pagamento da cobrança", "idempotencyKey": uuid4().hex,
        }
        payment = self.client.post("/api/bank/accounts/cliente/pix/pay", json=payment_payload)
        self.assertEqual(payment.status_code, 201)
        self.assertEqual(payment.get_json()["txid"], charge["txid"])

        charges = self.client.get("/api/charges").get_json()
        paid_charge = next(item for item in charges if item["txid"] == charge["txid"])
        self.assertEqual(paid_charge["status"], "PAID")
        receipts = self.client.get("/api/receipts").get_json()
        receipt = next(item for item in receipts if item["txid"] == charge["txid"])
        self.assertEqual(receipt["payer_name"], "Pedro")

        payment_payload["idempotencyKey"] = uuid4().hex
        duplicate = self.client.post("/api/bank/accounts/cliente/pix/pay", json=payment_payload)
        self.assertEqual(duplicate.status_code, 409)
        self.assertEqual(duplicate.get_json()["message"], "Esta cobrança Pix já foi paga.")

    def test_bank_pix_is_idempotent(self):
        joao = self.client.get("/api/bank/accounts/dono").get_json()
        key = uuid4().hex
        payload = {
            "pixKey": joao["pixKey"], "amount": 8.40,
            "description": "Pedido idempotente", "idempotencyKey": key,
        }
        first = self.client.post("/api/bank/accounts/cliente/pix/transfer", json=payload)
        second = self.client.post("/api/bank/accounts/cliente/pix/transfer", json=payload)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(first.get_json()["e2eid"], second.get_json()["e2eid"])

    def test_bank_pix_rejects_insufficient_balance(self):
        joao = self.client.get("/api/bank/accounts/dono").get_json()
        pedro_before = self.client.get("/api/bank/accounts/cliente").get_json()
        response = self.client.post("/api/bank/accounts/cliente/pix/transfer", json={
            "pixKey": joao["pixKey"], "amount": pedro_before["balance"] + 1,
            "description": "", "idempotencyKey": uuid4().hex,
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["message"], "Saldo insuficiente para concluir o Pix.")
        pedro_after = self.client.get("/api/bank/accounts/cliente").get_json()
        self.assertEqual(pedro_after["balance"], pedro_before["balance"])


if __name__ == "__main__":
    unittest.main()
