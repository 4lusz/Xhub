"""Calculo de custo de publicacoes do XHub.

Nota (auditoria item 13): este modulo pondera custos diferentes por
tipo de conteudo (ex.: LINK custando 15x mais que TEXT), mas o fluxo
real de publicacao (`PostService.publish_post`) sempre consome
exatamente 1 posto do saldo do plano por conta publicada, e
`CreatePostRequest` (`app.routes.post`) so aceita `text` -- nao ha
suporte real a imagem/video/link ainda. Este modulo NAO e importado
fora de si mesmo e NAO esta em uso no fluxo de publicacao atual; ele
existe como modelagem preparatoria para quando o produto suportar
outros tipos de conteudo. Antes de conecta-lo ao fluxo real, revisar
se os pesos abaixo ainda refletem a politica de negocio desejada.
"""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from app.core.exceptions import ValidationException
from app.domain.enums import PublicationContentType


@dataclass(frozen=True)
class PublicationCostPolicy:
    weights: Mapping[PublicationContentType, int]

    def get_weight(self, content_type: PublicationContentType) -> int:
        try:
            return self.weights[content_type]
        except KeyError as exc:
            raise ValidationException("Tipo de publicacao invalido.") from exc


DEFAULT_PUBLICATION_COST_POLICY = PublicationCostPolicy(
    weights=MappingProxyType(
        {
            PublicationContentType.TEXT: 1,
            PublicationContentType.IMAGE: 1,
            PublicationContentType.VIDEO: 1,
            PublicationContentType.LINK: 15,
        }
    )
)


def calculate_publication_cost(
    *,
    content_type: PublicationContentType,
    selected_accounts_count: int,
    policy: PublicationCostPolicy = DEFAULT_PUBLICATION_COST_POLICY,
) -> int:
    if selected_accounts_count <= 0:
        raise ValidationException("Selecione pelo menos uma conta para publicar.")

    return policy.get_weight(content_type) * selected_accounts_count
