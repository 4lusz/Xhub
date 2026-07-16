"""Elementos imutaveis de um texto de post, e validacao de preservacao.

Parte da funcionalidade Publicacao Inteligente (ver
`docs/ROADMAP_PUBLICACAO_INTELIGENTE.md`). Usado tanto por
`AIContentVariationService` (para validar variacoes geradas pela Groq)
quanto por `PostService` (para validar edicoes manuais enviadas pelo
usuario) -- funcoes puras, sem I/O, sem dependencia de models
SQLAlchemy, seguindo o mesmo padrao de `app.domain.policies`.

Regra oficial do roadmap: URLs sao constantes imutaveis (nunca expandir,
resumir, reescrever, trocar parametros, alterar dominio ou modificar
encurtadores como `bit.ly`); hashtags, @mencoes e emojis tambem devem
ser preservados. A comparacao e feita por multiset (mesmos elementos e
quantidades), sem exigir a mesma ordem -- reescrever a posicao de uma
hashtag dentro do texto e uma variacao estilistica aceitavel, alterar
seu conteudo nao e.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

# URL "generosa": cobre esquemas explicitos (http/https) e dominios
# encurtados comuns sem esquema (ex.: "bit.ly/abc", "shopee.com.br/x").
# Deliberadamente ampla -- e preferivel tratar algo como URL a mais (e
# exigir preservacao exata) do que deixar um encurtador escapar da
# validacao.
_URL_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.)?"
    r"[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)+"
    r"(?:/[^\s]*)?",
)
_HASHTAG_PATTERN = re.compile(r"#\w+")
_MENTION_PATTERN = re.compile(r"@\w+")
_EMOJI_PATTERN = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U0001F1E6-\U0001F1FF"
    "\U00002700-\U000027BF"
    "]",
    flags=re.UNICODE,
)

# Dominios que, por si so, nao devem ser tratados como URL "candidata a
# ser preservada" quando aparecem soltos em texto comum (evita falso
# positivo grosseiro em palavras com ponto, ex.: "v.s." nao e URL).
_MIN_URL_LENGTH = 4

# Pontuacao de encerramento de frase que o regex de URL captura por
# engano quando a URL fica colada nela (ex.: "confira em bit.ly/x."),
# porque `[^\s]*` no path nao sabe distinguir "faz parte da URL" de
# "e o ponto final da frase". Removida do final de cada match antes de
# comparar -- sem isso, duas ocorrencias da MESMA URL, cercadas de
# pontuacao diferente por causa da reescrita natural da frase ao redor
# (nao da URL em si), eram tratadas como URLs diferentes e a variacao
# era descartada indevidamente por `preserves_invariants`, mesmo tendo
# preservado o link exatamente como exigido pelo roadmap.
_URL_TRAILING_PUNCTUATION = ".,;:!?)]}'\""


@dataclass(frozen=True)
class ContentInvariants:
    """Elementos que uma variacao/edicao NUNCA pode alterar."""

    urls: tuple[str, ...]
    hashtags: tuple[str, ...]
    mentions: tuple[str, ...]
    emojis: tuple[str, ...]


def _strip_trailing_url_punctuation(url: str) -> str:
    return url.rstrip(_URL_TRAILING_PUNCTUATION)


def extract_invariants(text: str) -> ContentInvariants:
    urls = tuple(
        stripped
        for match in _URL_PATTERN.finditer(text)
        if len(stripped := _strip_trailing_url_punctuation(match.group(0))) >= _MIN_URL_LENGTH
        and "." in stripped
    )
    hashtags = tuple(_HASHTAG_PATTERN.findall(text))
    mentions = tuple(_MENTION_PATTERN.findall(text))
    emojis = tuple(_EMOJI_PATTERN.findall(text))

    return ContentInvariants(
        urls=urls,
        hashtags=hashtags,
        mentions=mentions,
        emojis=emojis,
    )


def preserves_invariants(original_text: str, candidate_text: str) -> bool:
    """`True` somente se `candidate_text` preserva exatamente (mesmo
    conteudo, mesma quantidade -- ordem livre) todas as URLs, hashtags,
    @mencoes e emojis presentes em `original_text`."""
    if not candidate_text.strip():
        return False

    original = extract_invariants(original_text)
    candidate = extract_invariants(candidate_text)

    return (
        Counter(original.urls) == Counter(candidate.urls)
        and Counter(original.hashtags) == Counter(candidate.hashtags)
        and Counter(original.mentions) == Counter(candidate.mentions)
        and Counter(original.emojis) == Counter(candidate.emojis)
    )


def normalize_for_comparison(text: str) -> str:
    return " ".join(text.strip().split()).casefold()


def is_duplicate_text(text_a: str, text_b: str) -> bool:
    return normalize_for_comparison(text_a) == normalize_for_comparison(text_b)


def has_duplicates(texts: list[str]) -> bool:
    """`True` se houver qualquer par de textos equivalentes (apos
    normalizacao de espacos/maiusculas) na lista."""
    normalized = [normalize_for_comparison(text) for text in texts]
    return len(set(normalized)) != len(normalized)
