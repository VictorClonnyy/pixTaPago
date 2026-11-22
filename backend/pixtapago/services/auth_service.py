"""UC001 - Autenticar usuário (incluído por UC007 - Realizar login)."""

from __future__ import annotations

import logging

from werkzeug.security import check_password_hash

from ..domain.errors import AuthenticationError, InactiveUserError
from ..domain.models import User
from ..persistence.repositories import UserRepository

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, users: UserRepository) -> None:
        self.users = users

    def authenticate(self, email: str, password: str) -> User:
        """Compara as credenciais com as armazenadas e verifica se o cadastro está ativo."""
        user = self.users.find_by_email(email or "")
        if not user or not check_password_hash(user.password_hash, password or ""):
            logger.info("Acesso recusado: credenciais inválidas.")
            raise AuthenticationError("E-mail ou senha não conferem.")
        if not user.active:
            logger.info("Acesso recusado: cadastro inativo (usuário %s).", user.id)
            raise InactiveUserError("Acesso suspenso. Procure o responsável pelo estabelecimento.")
        logger.info("Usuário %s autenticado.", user.id)
        return user

    def current_user(self, user_id: int) -> User | None:
        return self.users.find_by_id(user_id)
