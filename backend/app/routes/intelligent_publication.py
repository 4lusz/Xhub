"""Rotas da Publicacao Inteligente.

Ver `docs/ROADMAP_PUBLICACAO_INTELIGENTE.md`. Expoe apenas o preview de
variacoes -- a confirmacao/criacao do post reutiliza o endpoint ja
existente `POST /posts` (ver `app.routes.post` e
`PostService.create_post`), que agora aceita `rendered_texts` opcional
por conta (texto final aprovado/editado pelo usuario apos o preview).
Reaproveitar o endpoint existente evita duplicar a logica de criacao de
`Post`/`PostAccount` ja implementada e testada.

Sem regra de negocio aqui -- apenas validacao de autenticacao e
delegacao para `AIContentVariationService` (ver
"Responsabilidades do AIContentVariationService" no roadmap: "Nao deve
conter regra de negocio de geracao" na rota).
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import get_ai_content_variation_service, get_current_user
from app.core.exceptions import (
    BaseAppException,
    ConflictException,
    NotFoundException,
    ServiceUnavailableException,
    UnauthorizedException,
    ValidationException,
)
from app.domain.content_invariants import is_duplicate_text
from app.models.user import User
from app.schemas.intelligent_publication import (
    AccountPreviewResponse,
    IntelligentPublicationPreviewRequest,
    IntelligentPublicationPreviewResponse,
)
from app.services.ai_content_variation_service import (
    AIContentVariationService,
    IntelligentPublicationPreview,
)

router = APIRouter(
    prefix="/intelligent-publication",
    tags=["intelligent-publication"],
)


def _raise_http_error(exc: BaseAppException) -> None:
    status_code = status.HTTP_400_BAD_REQUEST

    if isinstance(exc, ConflictException):
        status_code = status.HTTP_409_CONFLICT
    elif isinstance(exc, UnauthorizedException):
        status_code = status.HTTP_401_UNAUTHORIZED
    elif isinstance(exc, ValidationException):
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    elif isinstance(exc, NotFoundException):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, ServiceUnavailableException):
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    headers = {"WWW-Authenticate": "Bearer"} if status_code == 401 else None

    raise HTTPException(
        status_code=status_code,
        detail=exc.message,
        headers=headers,
    ) from exc


def _to_preview_response(
    preview: IntelligentPublicationPreview,
) -> IntelligentPublicationPreviewResponse:
    texts = [account.text for account in preview.accounts]

    accounts = []
    for account in preview.accounts:
        occurrences = sum(
            1 for text in texts if is_duplicate_text(text, account.text)
        )
        accounts.append(
            AccountPreviewResponse(
                twitter_account_id=str(account.twitter_account_id),
                username=account.username,
                display_name=account.display_name,
                text=account.text,
                is_variation=account.is_variation,
                char_count=account.char_count,
                is_duplicate=occurrences > 1,
                is_valid=bool(account.text.strip()) and account.char_count <= 280,
            )
        )

    return IntelligentPublicationPreviewResponse(
        original_text=preview.original_text,
        strategy=preview.strategy,
        is_variation_required=preview.is_variation_required,
        is_variation_applied=preview.is_variation_applied,
        cache_hit=preview.cache_hit,
        warning=preview.warning,
        model=preview.model,
        prompt_version=preview.prompt_version,
        accounts=accounts,
    )


@router.post(
    "/preview",
    response_model=IntelligentPublicationPreviewResponse,
)
def preview(
    request: IntelligentPublicationPreviewRequest,
    current_user: User = Depends(get_current_user),
    ai_content_variation_service: AIContentVariationService = Depends(
        get_ai_content_variation_service
    ),
) -> IntelligentPublicationPreviewResponse:
    try:
        preview_result = ai_content_variation_service.generate_preview(
            user_id=current_user.id,
            original_text=request.text,
            twitter_account_ids=request.twitter_account_ids,
            apply_variation=request.apply_variation,
        )

        return _to_preview_response(preview_result)

    except BaseAppException as exc:
        _raise_http_error(exc)
