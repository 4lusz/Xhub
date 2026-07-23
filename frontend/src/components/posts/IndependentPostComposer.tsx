import { forwardRef, useEffect, useImperativeHandle, useState } from "react";
import { AlertTriangle } from "lucide-react";

import { type AccountMediaState, AccountMediaEditor } from "@/components/posts/AccountMediaEditor";
import { MediaComposer } from "@/components/posts/MediaComposer";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { CharacterCounter } from "@/components/common/CharacterCounter";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { useMediaComposer } from "@/hooks/useMediaComposer";
import { cn } from "@/lib/utils";
import { initialsFromName } from "@/lib/format";

interface TwitterAccountLite {
  id: string;
  username: string;
  display_name: string;
  profile_image_url: string | null;
}

export interface IndependentPostPayload {
  rendered_texts: Record<string, string>;
  media_ids: string[] | null;
  account_media_ids: Record<string, string[]> | null;
}

export interface IndependentPostComposerHandle {
  getPayload: () => IndependentPostPayload;
  reset: () => void;
}

interface IndependentPostComposerProps {
  accounts: TwitterAccountLite[];
  onReadyChange: (ready: boolean) => void;
}

/**
 * Fluxo 2 (conteúdo diferente para cada conta -- ver CLAUDE.md): sem
 * texto principal, sem Publicação Inteligente. Cada conta selecionada
 * ganha seu próprio editor desde o início; mídia pode ser compartilhada
 * (padrão, uma única `MediaComposer`) ou individualizada por conta
 * (uma `AccountMediaEditor` -- mesma instância de `useMediaComposer`,
 * mesmas regras de validação -- por conta).
 */
export const IndependentPostComposer = forwardRef<
  IndependentPostComposerHandle,
  IndependentPostComposerProps
>(function IndependentPostComposer({ accounts, onReadyChange }, ref) {
  const [texts, setTexts] = useState<Record<string, string>>({});
  const [shareMedia, setShareMedia] = useState(true);
  const [pendingShareMedia, setPendingShareMedia] = useState<boolean | null>(null);
  const [accountMedia, setAccountMedia] = useState<Record<string, AccountMediaState>>({});

  const sharedMedia = useMediaComposer();

  const handleAccountMediaChange = (accountId: string, state: AccountMediaState) => {
    setAccountMedia((current) => ({ ...current, [accountId]: state }));
  };

  const hasAnyMediaAttached =
    sharedMedia.items.length > 0 ||
    Object.values(accountMedia).some((state) => state.mediaIds.length > 0 || state.isUploading);

  const requestShareMediaChange = (nextValue: boolean) => {
    if (hasAnyMediaAttached) {
      setPendingShareMedia(nextValue);
    } else {
      setShareMedia(nextValue);
    }
  };

  const confirmShareMediaChange = () => {
    if (pendingShareMedia === null) return;
    sharedMedia.reset();
    setAccountMedia({});
    setShareMedia(pendingShareMedia);
    setPendingShareMedia(null);
  };

  const allTextsFilled =
    accounts.length > 0 && accounts.every((account) => (texts[account.id] ?? "").trim().length > 0);
  const allTextsWithinLimit = accounts.every((account) => (texts[account.id] ?? "").length <= 280);

  // Aviso (nunca bloqueia -- ver docs/AUDITORIA_SEGURANCA.md): no
  // Fluxo 2 o usuário escreve cada tweet manualmente, então repetir
  // texto entre contas é uma decisão dele, mas ainda assim aumenta o
  // risco de a plataforma X identificar um padrão repetitivo.
  const normalizedFilledTexts = accounts
    .map((account) => (texts[account.id] ?? "").trim().toLowerCase())
    .filter((text) => text.length > 0);
  const duplicatedNormalizedTexts = new Set(
    normalizedFilledTexts.filter(
      (text, index) => normalizedFilledTexts.indexOf(text) !== index,
    ),
  );
  const hasDuplicateWarning = duplicatedNormalizedTexts.size > 0;
  const mediaIsUploading = shareMedia
    ? sharedMedia.isUploading
    : Object.values(accountMedia).some((state) => state.isUploading);
  const mediaHasErrors = shareMedia
    ? sharedMedia.hasErrors
    : Object.values(accountMedia).some((state) => state.hasErrors);

  const ready = allTextsFilled && allTextsWithinLimit && !mediaIsUploading && !mediaHasErrors;

  useEffect(() => {
    onReadyChange(ready);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready]);

  useImperativeHandle(
    ref,
    () => ({
      getPayload: () => ({
        rendered_texts: Object.fromEntries(
          accounts.map((account) => [account.id, (texts[account.id] ?? "").trim()]),
        ),
        media_ids: shareMedia && sharedMedia.mediaIds.length > 0 ? sharedMedia.mediaIds : null,
        account_media_ids:
          !shareMedia && accounts.some((account) => (accountMedia[account.id]?.mediaIds.length ?? 0) > 0)
            ? Object.fromEntries(
                accounts.map((account) => [account.id, accountMedia[account.id]?.mediaIds ?? []]),
              )
            : null,
      }),
      reset: () => {
        setTexts({});
        sharedMedia.reset();
        setAccountMedia({});
        setShareMedia(true);
      },
    }),
    [accounts, texts, shareMedia, sharedMedia, accountMedia],
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between rounded-lg border border-border bg-surface px-4 py-3">
        <div>
          <p className="text-sm font-medium text-foreground">Usar a mesma mídia em todos os tweets</p>
          <p className="text-xs text-muted-foreground">
            Desative para anexar uma mídia diferente para cada conta.
          </p>
        </div>
        <Switch checked={shareMedia} onCheckedChange={requestShareMediaChange} />
      </div>

      {shareMedia && (
        <MediaComposer
          items={sharedMedia.items}
          canAddMore={sharedMedia.canAddMore}
          onAddFiles={sharedMedia.addFiles}
          onRemoveItem={sharedMedia.removeItem}
          onEditItem={sharedMedia.editItem}
        />
      )}

      {hasDuplicateWarning && (
        <Alert variant="warning">
          <AlertTriangle />
          <AlertDescription>
            O mesmo texto está sendo usado em mais de uma conta. Isso aumenta o risco de a
            plataforma X identificar um padrão repetitivo entre elas — considere escrever um tweet
            diferente para cada uma. Você ainda pode criar o post assim mesmo.
          </AlertDescription>
        </Alert>
      )}

      {accounts.length === 0 ? (
        <p className="rounded-lg border border-dashed border-border px-4 py-6 text-center text-sm text-muted-foreground">
          Selecione as contas de destino para escrever o tweet de cada uma.
        </p>
      ) : (
        accounts.map((account) => {
          const text = texts[account.id] ?? "";
          const isDuplicate = duplicatedNormalizedTexts.has(text.trim().toLowerCase());
          return (
            <Card key={account.id} className={cn(isDuplicate && "border-warning/50")}>
              <CardHeader className="pb-2">
                <div className="flex items-center gap-2">
                  <Avatar className="h-7 w-7 border border-border">
                    <AvatarImage src={account.profile_image_url ?? undefined} alt={account.display_name} />
                    <AvatarFallback>{initialsFromName(account.display_name)}</AvatarFallback>
                  </Avatar>
                  <CardTitle className="text-sm">@{account.username}</CardTitle>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label htmlFor={`independent-text-${account.id}`}>Texto</Label>
                    <CharacterCounter length={text.length} />
                  </div>
                  <Textarea
                    id={`independent-text-${account.id}`}
                    value={text}
                    onChange={(event) =>
                      setTexts((current) => ({ ...current, [account.id]: event.target.value }))
                    }
                    rows={4}
                    maxLength={280}
                    placeholder={`O que você quer publicar em @${account.username}?`}
                    className={cn(isDuplicate && "border-warning/60 focus-visible:ring-warning/40")}
                  />
                  {isDuplicate && (
                    <span className="inline-flex items-center gap-1 text-xs text-warning">
                      <AlertTriangle className="h-3 w-3" />
                      Igual a outra conta
                    </span>
                  )}
                </div>

                {!shareMedia && (
                  <AccountMediaEditor accountId={account.id} onChange={handleAccountMediaChange} />
                )}
              </CardContent>
            </Card>
          );
        })
      )}

      <ConfirmDialog
        open={pendingShareMedia !== null}
        onOpenChange={(open) => !open && setPendingShareMedia(null)}
        title="Trocar o modo de mídia?"
        description="Isso vai remover toda a mídia já anexada nos tweets deste post. O texto de cada conta não é afetado."
        confirmLabel="Trocar e remover mídia"
        destructive
        onConfirm={confirmShareMediaChange}
      />
    </div>
  );
});
