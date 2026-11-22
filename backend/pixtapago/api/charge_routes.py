"""Rotas de cobranças (UC002, UC003, UC008) e do painel inicial (T02)."""

from flask import Blueprint, jsonify, request

from ..domain.errors import NotFoundError, ValidationError
from ..integration.bb_pix_client import PixIntegrationError
from . import dependencies
from .security import login_required

bp = Blueprint("charges", __name__, url_prefix="/api")


@bp.get("/dashboard")
@login_required
def dashboard():
    return jsonify(dependencies.dashboard_service().summary())


@bp.get("/charges")
@login_required
def list_charges():
    return jsonify([charge.to_dict() for charge in dependencies.charge_service().list()])


@bp.post("/charges")
@login_required
def create_charge():
    payload = request.get_json(silent=True) or {}
    try:
        charge = dependencies.charge_service().create(
            payload.get("amount", 0), payload.get("description", ""), payload.get("payerName"),
        )
    except ValidationError as error:
        return jsonify({"message": str(error)}), 400
    except PixIntegrationError as error:
        return jsonify({"message": str(error)}), 502
    return jsonify(charge.to_dict()), 201


@bp.get("/charges/<txid>")
@login_required
def get_charge(txid: str):
    try:
        charge = dependencies.charge_service().get_status(txid)
    except NotFoundError as error:
        return jsonify({"message": str(error)}), 404
    return jsonify(charge.to_dict())
