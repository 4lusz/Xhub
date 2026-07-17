/**
 * Espelha `backend/app/domain/publication_cost.py` para dar feedback
 * instantâneo no navegador (quantos créditos este post vai consumir por
 * conta) antes de publicar. O backend é sempre a fonte da verdade --
 * esta detecção é só UX, nunca a única linha de defesa.
 */

const URL_PATTERN = /(?:https?:\/\/)?(?:www\.)?[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)+(?:\/[^\s]*)?/g;
const TRAILING_PUNCTUATION = /[.,;:!?)\]}'"]+$/;

export const DEFAULT_CREDITS_PER_ACCOUNT = 1;
export const LINK_CREDITS_PER_ACCOUNT = 15;

export function containsLink(text: string): boolean {
  const matches = text.match(URL_PATTERN) ?? [];
  return matches.some((match) => {
    const stripped = match.replace(TRAILING_PUNCTUATION, "");
    return stripped.length >= 4 && stripped.includes(".");
  });
}

export function creditsPerAccountFor(text: string): number {
  return containsLink(text) ? LINK_CREDITS_PER_ACCOUNT : DEFAULT_CREDITS_PER_ACCOUNT;
}
