"""Excecoes reutilizaveis da aplicacao, independentes de framework web."""

from collections.abc import Mapping
from typing import Any


class BaseAppException(Exception):
    """Excecao base para erros esperados da aplicacao."""

    default_message = "Erro na aplicacao."
    default_code = "app_error"

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        self.message = message or self.default_message
        self.code = code or self.default_code
        self.details = dict(details or {})
        super().__init__(self.message)

    def __str__(self) -> str:
        return self.message


class ValidationException(BaseAppException):
    default_message = "Dados invalidos."
    default_code = "validation_error"


class NotFoundException(BaseAppException):
    default_message = "Recurso nao encontrado."
    default_code = "not_found"


class ConflictException(BaseAppException):
    default_message = "Conflito com o estado atual do recurso."
    default_code = "conflict"


class UnauthorizedException(BaseAppException):
    default_message = "Credenciais invalidas ou ausentes."
    default_code = "unauthorized"


class ForbiddenException(BaseAppException):
    default_message = "Acesso negado."
    default_code = "forbidden"


class BadRequestException(BaseAppException):
    default_message = "Requisicao invalida."
    default_code = "bad_request"


class ServiceUnavailableException(BaseAppException):
    """Falha temporaria de um servico externo (ex.: Groq indisponivel,
    limite de requisicoes atingido). Usada quando a aplicacao precisa
    distinguir "servico externo fora do ar agora" de um erro de
    requisicao do proprio cliente (`BadRequestException`), para que a
    camada de service possa decidir corretamente (ex.: interromper a
    publicacao em vez de prosseguir com um fallback indevido)."""

    default_message = "Servico externo temporariamente indisponivel."
    default_code = "service_unavailable"


class NotImplementedException(BaseAppException):
    """Erro para fluxos ja modelados (rota/service) mas cuja implementacao
    ainda nao foi feita nesta etapa do roadmap."""

    default_message = "Funcionalidade ainda nao implementada."
    default_code = "not_implemented"
