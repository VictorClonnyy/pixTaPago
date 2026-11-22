"""UC007 - Realizar login (inclui UC001) e encerramento de sessão (RF003)."""

from flask import Blueprint, jsonify, request, session

from ..domain.errors import AuthenticationError, InactiveUserError
from . import dependencies
from .security import login_required

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@bp.post("/login")
def login():
    payload = request.get_json(silent=True) or {}
    try:
        user = dependencies.auth_service().authenticate(payload.get("email", ""), payload.get("password", ""))
    except AuthenticationError as error:
        return jsonify({"message": str(error)}), 401
    except InactiveUserError as error:
        return jsonify({"message": str(error)}), 403
    session.clear()
    session["user_id"] = user.id
    return jsonify(user.to_public_dict())


@bp.post("/logout")
def logout():
    session.clear()
    return "", 204


@bp.get("/me")
@login_required
def me():
    user = dependencies.auth_service().current_user(session["user_id"])
    if not user:
        session.clear()
        return jsonify({"message": "Autenticação necessária."}), 401
    return jsonify(user.to_public_dict())
