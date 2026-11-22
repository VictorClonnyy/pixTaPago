"""Camada de integração com serviços externos (API Pix v2 do Banco do Brasil)."""

from .bb_pix_client import BancoDoBrasilPixClient, PixIntegrationError

__all__ = ["BancoDoBrasilPixClient", "PixIntegrationError"]
