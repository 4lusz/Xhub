import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Link as LinkIcon, Sparkles } from "lucide-react";

import { AccountSelector } from "@/components/posts/AccountSelector";
import { CharacterCounter } from "@/components/common/CharacterCounter";
import {
  IndependentPostComposer,
  type IndependentPostComposerHandle,
} from "@/components/posts/IndependentPostComposer";
import { MediaComposer } from "@/components/posts/MediaComposer";
import { PageHeader } from "@/components/common/PageHeader";
import { IntelligentPublicationPreviewModal } from "@/components/intelligent-publication/IntelligentPublicationPreviewModal";
import { PublishOrScheduleDialog } from "@/components/posts/PublishOrScheduleDialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { useIntelligentPublicationPreview } from "@/hooks/useIntelligentPublication";
import { useMediaComposer } from "@/hooks/useMediaComposer";
import { useCreatePost, usePublishPost, useSchedulePost } from "@/hooks/usePosts";
import { useTwitterAccounts } from "@/hooks/useTwitterAccounts";
import { useToast } from "@/hooks/use-toast";
import { containsLink, LINK_CREDITS_PER_ACCOUNT } from "@/lib/publicationCost";
import type { ApiError } from "@/types/api";
import type { PostCompositionMode } from "@/types/post";

const MANDATORY_VARIATION_THRESHOLD = 5;
const OPTIONAL_VARIATION_MAX = 4;

export function NewPostPage() {
  const navigate = useNavigate();
  const { toast } = useToast();

  const [mode, setMode] = useState<PostCompositionMode>("shared");
  const [text, setText] = useState("");
  const [selectedAccountIds, setSelectedAccountIds] = useState<string[]>([]);
  const [applyVariation, setApplyVariation] = useState(true);
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const [createdPostId, setCreatedPostId] = useState<string | null>(null);
  const [independentReady, setIndependentReady] = useState(false);

  const preview = useIntelligentPublicationPreview();
  const createPost = useCreatePost();
  const publishPost = usePublishPost();
  const schedulePost = useSchedulePost();
  const media = useMediaComposer();
  const { data: accounts } = useTwitterAccounts();
  const independentComposerRef = useRef<IndependentPostComposerHandle>(null);

  const accountCount = selectedAccountIds.length;
  const isMandatory = accountCount >= MANDATORY_VARIATION_THRESHOLD;
  const isOptionalRange = accountCount >= 2 && accountCount <= OPTIONAL_VARIATION_MAX;
  const hasLink = containsLink(text);
  const canGeneratePreview =
    mode === "shared" &&
    text.trim().length > 0 &&
    text.length <= 280 &&
    accountCount > 0 &&
    !media.isUploading &&
    !media.hasErrors;

  const selectedAccounts = (accounts ?? []).filter((account) => selectedAccountIds.includes(account.id));
  const canCreateIndependentPost =
    mode === "independent" && accountCount > 0 && independentReady && !createPost.isPending;

  const handleGeneratePreview = () => {
    setIsPreviewOpen(true);
    preview.mutate({
      text,
      twitter_account_ids: selectedAccountIds,
      apply_variation: isMandatory ? true : applyVariation,
    });
  };

  const handleClosePreview = () => {
    setIsPreviewOpen(false);
    preview.reset();
  };

  const handleConfirmPreview = (renderedTexts: Record<string, string>) => {
    createPost.mutate(
      {
        composition_mode: "shared",
        text,
        twitter_account_ids: selectedAccountIds,
        rendered_texts: renderedTexts,
        media_ids: media.mediaIds,
      },
      {
        onSuccess: (post) => {
          setIsPreviewOpen(false);
          preview.reset();
          setCreatedPostId(post.id);
        },
      },
    );
  };

  const handleCreateIndependentPost = () => {
    const payload = independentComposerRef.current?.getPayload();
    if (!payload) return;

    createPost.mutate(
      {
        composition_mode: "independent",
        twitter_account_ids: selectedAccountIds,
        rendered_texts: payload.rendered_texts,
        media_ids: payload.media_ids,
        account_media_ids: payload.account_media_ids,
      },
      {
        onSuccess: (post) => {
          setCreatedPostId(post.id);
        },
      },
    );
  };

  const resetComposer = () => {
    setMode("shared");
    setText("");
    setSelectedAccountIds([]);
    setApplyVariation(true);
    setCreatedPostId(null);
    media.reset();
    independentComposerRef.current?.reset();
  };

  const handlePublishNow = () => {
    if (!createdPostId) return;
    publishPost.mutate(createdPostId, {
      onSuccess: () => {
        resetComposer();
        navigate("/posts");
      },
    });
  };

  const handleSchedule = (isoDateTime: string) => {
    if (!createdPostId) return;
    schedulePost.mutate(
      { postId: createdPostId, payload: { scheduled_for: isoDateTime } },
      {
        onSuccess: () => {
          resetComposer();
          navigate("/scheduled");
        },
      },
    );
  };

  const previewError = preview.isError ? (preview.error as ApiError).message : null;

  return (
    <div className="space-y-8">
      <PageHeader
        title="Novo post"
        description="Escreva uma vez e publique em várias contas, ou escreva um tweet diferente para cada uma."
      />

      <Tabs value={mode} onValueChange={(value) => setMode(value as PostCompositionMode)}>
        <TabsList>
          <TabsTrigger value="shared">Mesmo conteúdo para todas as contas</TabsTrigger>
          <TabsTrigger value="independent">Conteúdo diferente para cada conta</TabsTrigger>
        </TabsList>
      </Tabs>

      {mode === "shared" ? (
        <>
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle>Conteúdo</CardTitle>
                <CardDescription>O texto original nunca é publicado sem revisão quando há variação.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label htmlFor="post-text">Texto do post</Label>
                    <CharacterCounter length={text.length} />
                  </div>
                  <Textarea
                    id="post-text"
                    value={text}
                    onChange={(event) => setText(event.target.value)}
                    rows={5}
                    placeholder="O que você quer compartilhar?"
                    maxLength={280}
                  />
                </div>

                <MediaComposer
                  items={media.items}
                  canAddMore={media.canAddMore}
                  onAddFiles={media.addFiles}
                  onRemoveItem={media.removeItem}
                  onEditItem={media.editItem}
                />

                {hasLink && (
                  <div className="flex items-start gap-3 rounded-lg border border-warning/30 bg-warning/10 px-4 py-3">
                    <LinkIcon className="mt-0.5 h-4 w-4 text-warning" />
                    <p className="text-xs text-warning">
                      Este texto contém um link: cada conta publicada consumirá{" "}
                      {LINK_CREDITS_PER_ACCOUNT} créditos em vez de 1
                      {accountCount > 0
                        ? ` (${LINK_CREDITS_PER_ACCOUNT * accountCount} créditos no total para as ${accountCount} contas selecionadas).`
                        : "."}
                    </p>
                  </div>
                )}

                {accountCount === 0 && (
                  <div className="flex items-start gap-3 rounded-lg border border-dashed border-border px-4 py-3">
                    <Sparkles className="mt-0.5 h-4 w-4 text-muted-foreground" />
                    <div>
                      <p className="text-sm font-medium text-foreground">Publicação Inteligente</p>
                      <p className="text-xs text-muted-foreground">
                        Selecione as contas de destino ao lado para saber se a variação automática de
                        texto será usada — depende de quantas contas você escolher.
                      </p>
                    </div>
                  </div>
                )}

                {accountCount === 1 && (
                  <div className="flex items-start gap-3 rounded-lg border border-dashed border-border px-4 py-3">
                    <Sparkles className="mt-0.5 h-4 w-4 text-muted-foreground" />
                    <div>
                      <p className="text-sm font-medium text-foreground">Publicação Inteligente</p>
                      <p className="text-xs text-muted-foreground">
                        Com 1 conta selecionada, o texto original é publicado como está — não há
                        necessidade de variação e a IA não é usada.
                      </p>
                    </div>
                  </div>
                )}

                {isOptionalRange && (
                  <div className="flex items-center justify-between rounded-lg border border-border bg-surface px-4 py-3">
                    <div className="flex items-start gap-3">
                      <Sparkles className="mt-0.5 h-4 w-4 text-primary" />
                      <div>
                        <p className="text-sm font-medium text-foreground">
                          Publicação Inteligente — opcional (2 a 4 contas)
                        </p>
                        <p className="text-xs text-muted-foreground">
                          Gera uma variação natural do texto para cada conta, reduzindo o risco de
                          bloqueio por conteúdo repetitivo. Você pode desativar e publicar o texto
                          original em todas as contas.
                        </p>
                      </div>
                    </div>
                    <Switch checked={applyVariation} onCheckedChange={setApplyVariation} />
                  </div>
                )}

                {isMandatory && (
                  <div className="flex items-start gap-3 rounded-lg border border-warning/30 bg-warning/10 px-4 py-3">
                    <Sparkles className="mt-0.5 h-4 w-4 text-warning" />
                    <div>
                      <p className="text-sm font-medium text-warning">
                        Publicação Inteligente — obrigatória (5 ou mais contas)
                      </p>
                      <p className="text-xs text-warning">
                        Você selecionou {accountCount} contas. A partir de 5, uma variação diferente é
                        gerada para cada conta automaticamente — o mesmo texto não pode ser publicado
                        em todas elas.
                      </p>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Contas</CardTitle>
                <CardDescription>Selecione onde publicar.</CardDescription>
              </CardHeader>
              <CardContent>
                <AccountSelector selectedIds={selectedAccountIds} onChange={setSelectedAccountIds} />
              </CardContent>
            </Card>
          </div>

          <div className="flex justify-end">
            <Button size="lg" disabled={!canGeneratePreview} onClick={handleGeneratePreview}>
              <Sparkles className="h-4 w-4" />
              Gerar Publicação Inteligente
            </Button>
          </div>
        </>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            <div className="space-y-4 lg:col-span-2">
              <IndependentPostComposer
                ref={independentComposerRef}
                accounts={selectedAccounts}
                onReadyChange={setIndependentReady}
              />
            </div>

            <Card>
              <CardHeader>
                <CardTitle>Contas</CardTitle>
                <CardDescription>Selecione onde publicar — cada uma com seu próprio tweet.</CardDescription>
              </CardHeader>
              <CardContent>
                <AccountSelector selectedIds={selectedAccountIds} onChange={setSelectedAccountIds} />
              </CardContent>
            </Card>
          </div>

          <div className="flex justify-end">
            <Button size="lg" disabled={!canCreateIndependentPost} onClick={handleCreateIndependentPost}>
              Criar post
            </Button>
          </div>
        </>
      )}

      <IntelligentPublicationPreviewModal
        isOpen={isPreviewOpen}
        preview={preview.data ?? null}
        isLoading={preview.isPending}
        errorMessage={previewError}
        accountCount={accountCount}
        hasMedia={media.items.length > 0}
        onClose={handleClosePreview}
        onRetry={handleGeneratePreview}
        onConfirm={handleConfirmPreview}
        isConfirming={createPost.isPending}
      />

      <PublishOrScheduleDialog
        isOpen={createdPostId !== null}
        onClose={() => {
          toast({ title: "Post salvo como rascunho" });
          resetComposer();
          navigate("/posts");
        }}
        onPublishNow={handlePublishNow}
        onSchedule={handleSchedule}
        isPublishing={publishPost.isPending}
        isScheduling={schedulePost.isPending}
      />
    </div>
  );
}
