"""Rotas do proprio usuario autenticado (`/me`).

Complementa `GET /auth/me` (identidade) com dados que um cliente comum
precisa ver sobre a propria conta -- hoje, a assinatura vigente (plano,
limites e consumo). Diferente das rotas de `app.routes.admin`, que
exigem `get_current_admin` e operam sobre QUALQUER usuario, aqui a
autorizacao e `get_current_user`: cada usuario le apenas a propria
assinatura, descoberta a partir do token, sem receber nenhum id por
parametro. Reaproveita os mesmos models/services/repositories de
Subscription ja usados no fluxo administrativo.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth.dependencies import get_current_user, get_subscription_service
from app.core.exceptions import BaseAppException, NotFoundException
from app.models.enums import SubscriptionStatus
from app.models.subscription import Subscription
from app.models.user import User
from app.services.subscription_service import SubscriptionService

router = APIRouter(prefix="/me", tags=["me"])


class MyPlanInfo(BaseModel):
    id: str
    name: str
    price: float
    max_accounts: int
    max_posts_month: int


class MySubscriptionResponse(BaseModel):
    id: str
    status: SubscriptionStatus
    expires_at: datetime
    renewed_at: datetime | None
    used_posts: int
    extra_posts: int
    # Posts ainda disponiveis no ciclo (limite do plano + extras - usados),
    # calculado pela mesma politica de dominio usada na publicacao.
    available_posts: int
    # Contas do X ja conectadas x limite do plano.
    used_accounts: int
    plan: MyPlanInfo


def _raise_http_error(exc: BaseAppException) -> None:
    status_code = status.HTTP_400_BAD_REQUEST
    if isinstance(exc, NotFoundException):
        status_code = status.HTTP_404_NOT_FOUND

    raise HTTPException(status_code=status_code, detail=exc.message) from exc


def _to_response(
    subscription: Subscription, subscription_service: SubscriptionService
) -> MySubscriptionResponse:
    context = subscription_service.to_domain_context(subscription)
    plan = subscription.plan

    return MySubscriptionResponse(
        id=str(subscription.id),
        status=subscription.status,
        expires_at=subscription.expires_at,
        renewed_at=subscription.renewed_at,
        used_posts=subscription.used_posts,
        extra_posts=subscription.extra_posts,
        available_posts=subscription_service.get_available_posts(subscription),
        used_accounts=context.usage.connected_accounts,
        plan=MyPlanInfo(
            id=str(plan.id),
            name=plan.name,
            price=float(plan.price),
            max_accounts=plan.max_accounts,
            max_posts_month=plan.max_posts_month,
        ),
    )


@router.get("/subscription", response_model=MySubscriptionResponse)
def get_my_subscription(
    current_user: User = Depends(get_current_user),
    subscription_service: SubscriptionService = Depends(get_subscription_service),
) -> MySubscriptionResponse:
    """Assinatura vigente do usuario autenticado (plano, limites e
    consumo). Retorna 404 quando o usuario nao possui assinatura -- caso
    tipico de contas administrativas, que sao criadas sem assinatura."""
    try:
        subscription = subscription_service.get_current_subscription(current_user.id)
        if subscription is None:
            raise NotFoundException("Usuario nao possui assinatura.")
    except BaseAppException as exc:
        _raise_http_error(exc)

    return _to_response(subscription, subscription_service)
