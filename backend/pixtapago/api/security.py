"""Controle de sessão (RNF001): exige autenticação nas rotas que expõem dados."""

from __future__ import annotations

import hmac
from functools import wraps

from flask import jsonify, session


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"message": "Autenticação necessária."}), 401
        return view(*args, **kwargs)
    return wrapped


def secrets_match(expected: str, received: str | None) -> bool:
    """Comparação em tempo constante, para não vazar o segredo por tempo de resposta."""
    return bool(expected) and received is not None and hmac.compare_digest(expected, received)
