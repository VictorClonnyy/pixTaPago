"""PixTáPago: confirmação e acompanhamento de recebimentos Pix.

Arquitetura em camadas:

* ``api``          - apresentação REST (blueprints Flask, sessão, validação de origem);
* ``services``     - aplicação: um serviço por grupo de casos de uso;
* ``domain``       - entidades, objetos de valor, regras e leitura do payload EMV;
* ``persistence``  - conexão SQLite, esquema e repositórios;
* ``integration``  - cliente da API Pix v2 do Banco do Brasil;
* ``simulator``    - simulador do PSP pagador, fora do escopo do produto.
"""

from __future__ import annotations

import logging

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from .config import FRONTEND_DIST, Settings


def create_app(settings: Settings | None = None) -> Flask:
    settings = settings or Settings.from_env()
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=settings.secret_key,
        DATABASE=settings.database_path,
        PIX_KEY=settings.pix_key,
        WEBHOOK_SECRET=settings.webhook_secret,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )
    CORS(app, supports_credentials=True, origins=list(settings.allowed_origins))
    _configure_logging()

    from .api import auth_routes, charge_routes, receipt_routes
    from .persistence import database
    from .simulator import routes as simulator_routes

    database.init_app(app)
    for blueprint in (auth_routes.bp, charge_routes.bp, receipt_routes.bp, simulator_routes.bp):
        app.register_blueprint(blueprint)

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "pixMode": "bb", "environment": "homologacao"})

    @app.errorhandler(404)
    def frontend(error):
        """Entrega a SPA compilada (frontend/dist) quando ela existir."""
        path = request.path.lstrip("/")
        if request.method != "GET" or path.startswith("api/") or not FRONTEND_DIST.is_dir():
            return error
        if path and (FRONTEND_DIST / path).is_file():
            return send_from_directory(FRONTEND_DIST, path)
        return send_from_directory(FRONTEND_DIST, "index.html")

    return app


def _configure_logging() -> None:
    """Registro de eventos técnicos (RNF012), sem gravar segredos ou credenciais."""
    logger = logging.getLogger("pixtapago")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
