"""Rotas do simulador de PSP pagador (telas /cliente e /dono)."""

from uuid import uuid4

from flask import Blueprint, jsonify, request

from ..api import dependencies
from ..domain.errors import NotFoundError, PixAlreadyPaidError

bp = Blueprint("psp_simulator", __name__, url_prefix="/api/bank")


def _idempotency_key(payload: dict) -> str:
    return str(payload.get("idempotencyKey", "")).strip() or uuid4().hex


@bp.get("/accounts/<actor>")
def get_account(actor: str):
    try:
        return jsonify(dependencies.psp_simulator_service().account_statement(actor))
    except NotFoundError as error:
        return jsonify({"message": str(error)}), 404


@bp.get("/pix/resolve")
def resolve_key():
    try:
        return jsonify(dependencies.psp_simulator_service().resolve_key(request.args.get("key", "")))
    except NotFoundError as error:
        return jsonify({"message": str(error)}), 404


@bp.post("/pix/preview")
def preview_code():
    payload = request.get_json(silent=True) or {}
    try:
        return jsonify(dependencies.psp_simulator_service().preview_code(str(payload.get("pix", ""))))
    except NotFoundError as error:
        return jsonify({"message": str(error)}), 404
    except ValueError as error:
        return jsonify({"message": str(error)}), 400


@bp.post("/accounts/<actor>/pix/transfer")
def transfer(actor: str):
    payload = request.get_json(silent=True) or {}
    try:
        transaction = dependencies.psp_simulator_service().transfer_to_key(
            actor, str(payload.get("pixKey", "")).strip(), float(payload.get("amount", 0)),
            str(payload.get("description", "")), _idempotency_key(payload),
        )
    except (TypeError, ValueError) as error:
        return jsonify({"message": str(error)}), 400
    return jsonify(transaction), 201


@bp.post("/accounts/<actor>/pix/pay")
def pay_code(actor: str):
    payload = request.get_json(silent=True) or {}
    try:
        transaction = dependencies.psp_simulator_service().pay_code(
            actor, str(payload.get("pix", "")), float(payload.get("amount", 0)),
            str(payload.get("description", "")), _idempotency_key(payload),
        )
    except PixAlreadyPaidError as error:
        return jsonify({"message": str(error)}), 409
    except (TypeError, ValueError) as error:
        return jsonify({"message": str(error)}), 400
    return jsonify(transaction), 201
