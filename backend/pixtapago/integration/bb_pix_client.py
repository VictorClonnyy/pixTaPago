from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests


class PixIntegrationError(RuntimeError):
    pass


class BancoDoBrasilPixClient:
    """Cliente HTTP da API Pix v2 oficial do Banco do Brasil."""

    _token: str | None = None
    _token_expires_at: float = 0

    def __init__(self) -> None:
        self.mode = "bb"
        self.client_id = os.getenv("BB_CLIENT_ID", "")
        self.client_secret = os.getenv("BB_CLIENT_SECRET", "")
        self.app_key = os.getenv("BB_GW_DEV_APP_KEY", "")
        self.pix_key = os.getenv("BB_PIX_KEY", "hmtestes2@bb.com.br")
        self.oauth_url = os.getenv("BB_OAUTH_URL", "https://oauth.hm.bb.com.br/oauth/token")
        self.base_url = os.getenv("BB_PIX_BASE_URL", "https://api.hm.bb.com.br/pix/v2").rstrip("/")
        self.mtls_cert_path = os.getenv("BB_MTLS_CERT_PATH", "")
        self.mtls_key_path = os.getenv("BB_MTLS_KEY_PATH", "")

    def create_immediate_charge(self, txid: str, amount: float, description: str) -> dict:
        payload = {
            "calendario": {"expiracao": 3600},
            "valor": {"original": f"{amount:.2f}"},
            "chave": self.pix_key,
            "solicitacaoPagador": description or "Pagamento PixTaPago",
        }
        data = self._request("PUT", f"/cob/{txid}", json=payload)
        copy_paste = data.get("pixCopiaECola") or data.get("pix_copy_paste")
        if not copy_paste:
            raise PixIntegrationError("A API criou a cobrança, mas não retornou o Pix Copia e Cola esperado.")
        return {"pixCopyPaste": copy_paste, "location": (data.get("loc") or {}).get("location")}

    def get_charge(self, txid: str, fallback_status: str = "ACTIVE") -> dict:
        data = self._request("GET", f"/cob/{txid}")
        status_map = {"ATIVA": "ACTIVE", "CONCLUIDA": "PAID", "REMOVIDA_PELO_USUARIO_RECEBEDOR": "CANCELED", "REMOVIDA_PELO_PSP": "EXPIRED"}
        return {
            "status": status_map.get(data.get("status"), fallback_status),
            "payments": data.get("pix") if isinstance(data.get("pix"), list) else [],
            "raw": data,
        }

    def list_received_pix(self, lookback_hours: int = 24) -> list[dict]:
        """Consulta Pix recebidos na chave pela API oficial GET /pix."""
        end = datetime.now(timezone.utc)
        start = end - timedelta(hours=lookback_hours)
        data = self._request(
            "GET",
            "/pix",
            params={
                "inicio": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "fim": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "paginaAtual": 0,
                "itensPorPagina": 100,
            },
        )
        return data.get("pix") if isinstance(data.get("pix"), list) else []

    def _access_token(self) -> str:
        client_type = type(self)
        if client_type._token and time.time() < client_type._token_expires_at:
            return client_type._token
        if not all([self.client_id, self.client_secret, self.base_url]):
            raise PixIntegrationError("Configure BB_CLIENT_ID, BB_CLIENT_SECRET e BB_PIX_BASE_URL para usar a API real.")
        try:
            response = requests.post(
                self.oauth_url,
                auth=(self.client_id, self.client_secret),
                data={"grant_type": "client_credentials", "scope": "cob.write cob.read pix.read webhook.read webhook.write"},
                timeout=15,
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as error:
            response = getattr(error, "response", None)
            if response is not None and response.status_code in {400, 401, 403}:
                raise PixIntegrationError(
                    f"O Banco do Brasil recusou as credenciais OAuth (HTTP {response.status_code})."
                ) from error
            raise PixIntegrationError(
                "Não foi possível conectar ao OAuth do Banco do Brasil. Verifique a rede e tente novamente."
            ) from error
        except ValueError as error:
            raise PixIntegrationError("O OAuth do Banco do Brasil retornou uma resposta inválida.") from error

        token = data.get("access_token")
        if not token:
            raise PixIntegrationError("O OAuth do Banco do Brasil não retornou o token de acesso.")
        client_type._token = token
        client_type._token_expires_at = time.time() + int(data.get("expires_in", 300)) - 30
        return client_type._token

    def _request(self, method: str, path: str, **kwargs) -> dict:
        try:
            params = {"gw-dev-app-key": self.app_key}
            params.update(kwargs.pop("params", {}) or {})
            response = requests.request(
                method,
                f"{self.base_url}{path}",
                headers={"Authorization": f"Bearer {self._access_token()}", "Accept": "application/json"},
                params=params,
                cert=self._client_certificate(),
                timeout=20,
                **kwargs,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.SSLError as error:
            raise PixIntegrationError(
                "O Banco do Brasil recusou o certificado mTLS. Configure "
                "BB_MTLS_CERT_PATH e BB_MTLS_KEY_PATH com o certificado e a chave privada "
                "correspondente ao certificado cadastrado no Portal Developers BB."
            ) from error
        except (requests.RequestException, ValueError) as error:
            detail = getattr(getattr(error, "response", None), "text", "")
            raise PixIntegrationError(f"Falha na API Pix do BB. {detail[:180]}") from error

    def _client_certificate(self) -> tuple[str, str] | None:
        if not self.mtls_cert_path and not self.mtls_key_path:
            return None
        if not self.mtls_cert_path or not self.mtls_key_path:
            raise PixIntegrationError(
                "Informe BB_MTLS_CERT_PATH e BB_MTLS_KEY_PATH em conjunto."
            )
        cert_path = Path(self.mtls_cert_path).expanduser().resolve()
        key_path = Path(self.mtls_key_path).expanduser().resolve()
        if not cert_path.is_file() or not key_path.is_file():
            raise PixIntegrationError(
                "O certificado ou a chave mTLS não foi encontrado no caminho configurado."
            )
        return str(cert_path), str(key_path)
