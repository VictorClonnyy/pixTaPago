"""Configuração da aplicação, lida das variáveis de ambiente e do arquivo .env."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIST = BACKEND_DIR.parent / "frontend" / "dist"

# Valores já definidos no ambiente têm precedência sobre o .env.
load_dotenv(BACKEND_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    secret_key: str
    database_path: str
    pix_key: str
    webhook_secret: str
    allowed_origins: tuple[str, ...]

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            secret_key=os.getenv("SECRET_KEY", "dev-only-change-me"),
            database_path=str(BACKEND_DIR / os.getenv("DATABASE_PATH", "instance/pixtapago.db")),
            pix_key=os.getenv("BB_PIX_KEY", "hmtestes2@bb.com.br"),
            webhook_secret=os.getenv("BB_WEBHOOK_SECRET", ""),
            allowed_origins=("http://localhost:5173",),
        )
