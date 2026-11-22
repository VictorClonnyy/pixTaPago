"""Exceções de domínio. Herdam de ValueError para preservar o contrato da API."""


class DomainError(ValueError):
    """Erro de regra de negócio, apresentado ao usuário com status 400."""


class ValidationError(DomainError):
    """Dado informado pelo usuário não atende às regras de validação."""


class NotFoundError(DomainError):
    """Registro solicitado não existe."""


class AuthenticationError(DomainError):
    """Credenciais não conferem com as armazenadas (UC001 - A1)."""


class InactiveUserError(DomainError):
    """Cadastro do usuário está inativo (UC001 - A2)."""


class PixAlreadyPaidError(DomainError):
    """A cobrança indicada já possui pagamento liquidado."""
