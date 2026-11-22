"""Rotas de recebimentos (UC005), notificações (UC006) e confirmação (UC004)."""

import logging

from flask import Blueprint, current_app, jsonify, request

from ..domain.errors import NotFoundError, ValidationError
from . import dependencies
from .security import login_required, secrets_match

logger = logging.getLogger(__name__)
bp = Blueprint("receipts", __name__, url_prefix="/api")


@bp.get("/receipts")
@login_required
def list_receipts():
    try:
        receipts = dependencies.receipt_history_service().search(
            request.args.get("q", ""), request.args.get("inicio"), request.args.get("fim"),
        )
    except ValidationError as error:
        return jsonify({"message": str(error)}), 400
    return jsonify([receipt.to_dict() for receipt in receipts])


@bp.get("/notifications")
@login_required
def list_notifications():
    only_unread = request.args.get("unread") in {"1", "true"}
    notifications = dependencies.notification_service().list(only_unread=only_unread)
    return jsonify([item.to_dict() for item in notifications])


@bp.post("/notifications/<int:notification_id>/read")
@login_required
def read_notification(notification_id: int):
    try:
        dependencies.notification_service().mark_read(notification_id)
    except NotFoundError as error:
        return jsonify({"message": str(error)}), 404
    return "", 204


@bp.post("/notifications/read-all")
@login_required
def read_all_notifications():
    return jsonify({"updated": dependencies.notification_service().mark_all_read()})


@bp.post("/pix/sync")
@login_required
def sync_pix():
    """Contingência: consulta o BB quando o webhook não alcança o ambiente local."""
    return jsonify(dependencies.payment_confirmation_service().synchronize())


@bp.post("/webhooks/bb/pix")
def bb_pix_webhook():
    """UC004: a API Pix do BB comunica os valores creditados na chave acompanhada."""
    expected = current_app.config["WEBHOOK_SECRET"]
    received = request.headers.get("X-Webhook-Secret") or request.args.get("token")
    if not secrets_match(expected, received):
        # UC004 - A2: origem não confiável; nenhuma alteração é feita.
        logger.warning(
            "Webhook recusado: %s.",
            "BB_WEBHOOK_SECRET não configurado" if not expected else "segredo ausente ou inválido",
        )
        return jsonify({"message": "Origem não autorizada."}), 401
    payload = request.get_json(silent=True) or {}
    events = payload.get("pix", []) if isinstance(payload, dict) else payload
    if not isinstance(events, list):
        return jsonify({"message": "Payload inválido."}), 400
    processed = dependencies.payment_confirmation_service().process_webhook(events)
    return jsonify({"processed": processed}), 200
