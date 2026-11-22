import unittest
from unittest.mock import patch

import requests

from pixtapago.integration.bb_pix_client import BancoDoBrasilPixClient, PixIntegrationError


class BancoDoBrasilPixClientTest(unittest.TestCase):
    def test_charge_uses_official_cob_endpoint_and_returned_copy_paste(self):
        client = BancoDoBrasilPixClient()
        bb_response = {
            "pixCopiaECola": "000201-codigo-retornado-pelo-bb",
            "loc": {"location": "https://qrcodepix-h.bb.com.br/pix/v2/charge-id"},
        }

        with patch.object(client, "_request", return_value=bb_response) as request:
            result = client.create_immediate_charge("txid123", 19.90, "Pedido 123")

        request.assert_called_once_with(
            "PUT",
            "/cob/txid123",
            json={
                "calendario": {"expiracao": 3600},
                "valor": {"original": "19.90"},
                "chave": client.pix_key,
                "solicitacaoPagador": "Pedido 123",
            },
        )
        self.assertEqual(result["pixCopyPaste"], bb_response["pixCopiaECola"])
        self.assertEqual(result["location"], bb_response["loc"]["location"])

    def test_completed_charge_exposes_official_pix_events(self):
        client = BancoDoBrasilPixClient()
        payment = {
            "endToEndId": "E123",
            "txid": "txid123",
            "valor": "19.90",
            "horario": "2026-09-13T10:00:00Z",
        }
        with patch.object(client, "_request", return_value={"status": "CONCLUIDA", "pix": [payment]}):
            result = client.get_charge("txid123")
        self.assertEqual(result["status"], "PAID")
        self.assertEqual(result["payments"], [payment])

    def test_received_pix_uses_official_pix_endpoint(self):
        client = BancoDoBrasilPixClient()
        with patch.object(client, "_request", return_value={"pix": [{"endToEndId": "E123"}]}) as request:
            result = client.list_received_pix()
        self.assertEqual(result, [{"endToEndId": "E123"}])
        args, kwargs = request.call_args
        self.assertEqual(args[:2], ("GET", "/pix"))
        self.assertIn("inicio", kwargs["params"])
        self.assertIn("fim", kwargs["params"])

    def test_oauth_connection_error_has_a_clear_message(self):
        client = BancoDoBrasilPixClient()
        type(client)._token = None
        with patch("pixtapago.integration.bb_pix_client.requests.post", side_effect=requests.ConnectionError):
            with self.assertRaisesRegex(PixIntegrationError, "conectar ao OAuth"):
                client._access_token()


if __name__ == "__main__":
    unittest.main()
