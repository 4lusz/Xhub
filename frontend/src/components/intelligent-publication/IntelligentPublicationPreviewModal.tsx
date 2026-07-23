import { useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, Image as ImageIcon, Info, RefreshCw, Sparkles } from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { VariationAccountCard } from "@/components/intelligent-publication/VariationAccountCard";
import { VariationLoadingState } from "@/components/intelligent-publication/VariationLoadingState";
import type { IntelligentPublicationPreview } from "@/types/intelligentPublication";

interface IntelligentPublicationPreviewModalProps {
  isOpen: boolean;
  preview: IntelligentPublicationPreview | null;
  isLoading: boolean;
  errorMessage?: string | null;
  accountCount: number;
  /** Há mídia (imagem/gif/vídeo) anexada a este post -- ver `components/posts/MediaComposer`. */
  hasMedia?: boolean;
  onClose: () => void;
  onRetry: () => void;
  onConfirm: (renderedTexts: Record<string, string>) => void;
  isConfirming?: boolean;
}

const STRATEGY_LABEL: Record<string, string> = {
  original: "Texto original",
  optional_variation: "Variação opcional",
  mandatory_variation: "Variação obrigatória",
};

/**
 * Explica, em uma frase, o que a Publicação Inteligente decidiu fazer
 * nesta publicação específica -- complementa a explicação geral fixa
 * (ver `DialogDescription` abaixo), que descreve o que a funcionalidade
 * faz. As quatro situações reais são espelhadas de
 * `app/services/ai_content_variation_service.py` (1 conta / variação
 * opcional aplicada / variação opcional não aplicada / variação
 * obrigatória) -- nenhum estado novo foi inventado aqui.
 */
function getSituationSummary(
  preview: IntelligentPublicationPreview,
  accountCount: number,
): string {
  if (preview.strategy === "original") {
    return "Você selecionou apenas 1 conta, então o texto original será publicado sem alterações — a Publicação Inteligente não entra em ação aqui.";
  }

  if (preview.strategy === "mandatory_variation") {
    return `Você selecionou ${accountCount} contas. A partir de 5 contas, gerar uma variação por conta é obrigatório: nenhum texto pode se repetir entre elas.`;
  }

  // optional_variation
  if (preview.is_variation_applied) {
    return `Você selecionou ${accountCount} contas e a Publicação Inteligente está ativada: geramos uma variação diferente para cada uma. Revise o resultado antes de confirmar.`;
  }

  return `Você selecionou ${accountCount} contas, mas a Publicação Inteligente está desativada nesta publicação — o mesmo texto original será usado em todas elas.`;
}

export function IntelligentPublicationPreviewModal({
  isOpen,
  preview,
  isLoading,
  errorMessage,
  accountCount,
  hasMedia,
  onClose,
  onRetry,
  onConfirm,
  isConfirming,
}: IntelligentPublicationPreviewModalProps) {
  const [editedTexts, setEditedTexts] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!preview) return;
    const initial: Record<string, string> = {};
    for (const account of preview.accounts) {
      initial[account.twitter_account_id] = account.text;
    }
    setEditedTexts(initial);
  }, [preview]);

  const texts = useMemo(() => Object.values(editedTexts), [editedTexts]);
  const normalizedTexts = useMemo(
    () => texts.map((text) => text.trim().toLowerCase()),
    [texts],
  );

  const hasEmptyText = texts.some((text) => !text.trim());
  const hasTextOverLimit = texts.some((text) => text.length > 280);
  const hasAnyDuplicate =
    texts.length >= 2 && new Set(normalizedTexts).size !== normalizedTexts.length;
  const hasDuplicateText = !!preview?.is_variation_required && hasAnyDuplicate;
  // Mesmo texto em 2+ contas fora do caso obrigatório (5+ contas, ja
  // bloqueado acima) -- risco de deteccao de conteudo repetitivo pelo X
  // (ver docs/AUDITORIA_SEGURANCA.md), mas nunca bloqueia: publicar o
  // mesmo conteudo em poucas contas e um uso legitimo e comum (a
  // variacao e OPCIONAL de proposito nessa faixa).
  const hasDuplicateWarning = hasAnyDuplicate && !hasDuplicateText;

  const canConfirm =
    !isLoading && !!preview && !hasEmptyText && !hasTextOverLimit && !hasDuplicateText;

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary/15 text-primary">
              <Sparkles className="h-4 w-4" />
            </div>
            <DialogTitle>Publicação Inteligente</DialogTitle>
            {preview && (
              <Badge variant={preview.is_variation_required ? "warning" : "secondary"}>
                {STRATEGY_LABEL[preview.strategy] ?? preview.strategy}
              </Badge>
            )}
          </div>
          <DialogDescription>
            Nossa IA reescreve seu texto em variações naturais, preservando o significado, links,
            hashtags e menções — o objetivo é reduzir padrões repetitivos entre contas e diminuir
            o risco de bloqueio pela política do X.
          </DialogDescription>
        </DialogHeader>

        <AnimatePresence mode="wait">
          {isLoading && (
            <motion.div key="loading" exit={{ opacity: 0 }}>
              <VariationLoadingState accountCount={accountCount} />
            </motion.div>
          )}

          {!isLoading && errorMessage && (
            <motion.div key="error" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              <Alert variant="destructive">
                <AlertTriangle />
                <AlertDescription className="space-y-3">
                  <p>{errorMessage}</p>
                  <div className="flex gap-2">
                    <Button size="sm" variant="outline" onClick={onRetry}>
                      <RefreshCw className="h-3.5 w-3.5" />
                      Tentar novamente
                    </Button>
                    <Button size="sm" variant="ghost" onClick={onClose}>
                      Salvar como rascunho
                    </Button>
                  </div>
                </AlertDescription>
              </Alert>
            </motion.div>
          )}

          {!isLoading && !errorMessage && preview && (
            <motion.div
              key="content"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="space-y-4"
            >
              <div className="flex items-start gap-2 rounded-lg border border-primary/20 bg-primary/5 px-3 py-2.5 text-sm text-foreground">
                <Info className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                <p>{getSituationSummary(preview, accountCount)}</p>
              </div>

              {hasMedia && (
                <div className="flex items-start gap-2 rounded-lg border border-border bg-surface px-3 py-2.5 text-xs text-muted-foreground">
                  <ImageIcon className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                  <p>
                    A mídia anexada (imagem, gif ou vídeo) será publicada exatamente igual em todas as
                    contas — a Publicação Inteligente varia apenas o texto.
                  </p>
                </div>
              )}

              <div className="space-y-1.5">
                <p className="text-xs font-medium uppercase tracking-wide text-subtle-foreground">
                  Texto original
                </p>
                <p className="rounded-md border border-border bg-background p-3 text-sm text-muted-foreground">
                  {preview.original_text}
                </p>
              </div>

              {preview.warning && (
                <Alert variant="warning">
                  <AlertTriangle />
                  <AlertDescription>{preview.warning}</AlertDescription>
                </Alert>
              )}

              {hasDuplicateWarning && (
                <Alert variant="warning">
                  <AlertTriangle />
                  <AlertDescription>
                    O mesmo texto está sendo publicado em mais de uma conta. Isso aumenta o risco de
                    a plataforma X identificar um padrão repetitivo entre elas — considere variar o
                    texto de cada conta. Você ainda pode confirmar assim mesmo.
                  </AlertDescription>
                </Alert>
              )}

              <div className="max-h-[22rem] space-y-2.5 overflow-y-auto pr-1 scrollbar-thin">
                {preview.accounts.map((account) => {
                  const currentValue =
                    editedTexts[account.twitter_account_id] ?? account.text;
                  const isEmpty = !currentValue.trim();
                  const normalizedValue = currentValue.trim().toLowerCase();
                  const isRepeatedAcrossAccounts =
                    normalizedTexts.filter((text) => text === normalizedValue).length > 1;
                  const isDuplicate = !!preview.is_variation_required && isRepeatedAcrossAccounts;
                  const isDuplicateWarning = !preview.is_variation_required && isRepeatedAcrossAccounts;

                  return (
                    <VariationAccountCard
                      key={account.twitter_account_id}
                      account={account}
                      value={currentValue}
                      isEmpty={isEmpty}
                      isDuplicate={isDuplicate}
                      isDuplicateWarning={isDuplicateWarning}
                      onChange={(value) =>
                        setEditedTexts((current) => ({
                          ...current,
                          [account.twitter_account_id]: value,
                        }))
                      }
                    />
                  );
                })}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancelar
          </Button>
          <Button
            disabled={!canConfirm || isConfirming}
            onClick={() => onConfirm(editedTexts)}
          >
            {isConfirming ? "Confirmando…" : "Confirmar publicação"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
