"""Normalizacao da resposta da pergunta de seguranca (2o fator simples
de login, hoje restrito a administradores -- ver
docs/AUDITORIA_SEGURANCA.md).

Funcao pura, sem I/O -- mesmo padrao do restante de `app.domain`. A
normalizacao (espacos nas pontas removidos, minusculas) existe para que
a resposta funcione mesmo se o usuario digitar com capitalizacao ou
espacamento diferente da vez em que configurou -- comparado sempre
pelo hash da forma NORMALIZADA (nunca da forma literal digitada).
"""

from __future__ import annotations


def normalize_security_answer(answer: str) -> str:
    return " ".join(answer.strip().split()).casefold()
