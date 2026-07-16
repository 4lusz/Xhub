import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Sparkles } from "lucide-react";

import { AccountSelector } from "@/components/posts/AccountSelector";
import { CharacterCounter } from "@/components/common/CharacterCounter";
import { MediaComposer } from "@/components/posts/MediaComposer";
import { PageHeader } from "@/components/common/PageHeader";
import { IntelligentPublicationPreviewModal } from "@/components/intelligent-publication/IntelligentPublicationPreviewModal";
import { PublishOrScheduleDialog } from "@/components/posts/PublishOrScheduleDialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { useIntelligentPublicationPreview } from "@/hooks/useIntelligentPublication";
import { useMediaComposer } from "@/hooks/useMediaComposer";
import { useCreatePost, usePublishPost, useSchedulePost } from "@/hooks/usePosts";
import { useToast } from "@/hooks/use-toast";
import type { ApiError } from "@/types/api";

const MANDATORY_VARIATION_THRESHOLD = 5;
const OPTIONAL_VARIATION_MAX = 4;

export function NewPostPage() {
  const navigate = useNavigate();
  const { toast } = useToast();

  const [text, setText] = useState("");
  const [selectedAccountIds, setSelectedAccountIds] = useState<string[]>([]);
  const [applyVariation, setApplyVariation] = useState(true);
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const [createdPostId, setCreatedPostId] = useState<string | null>(null);

  const preview = useIntelligentPublicationPreview();
  const createPost = useCreatePost();
  const publishPost = usePublishPost();
  const schedulePost = useSchedulePost();
  const media = useMediaComposer();

  const accountCount = selectedAccountIds.length;
  const isMandatory = accountCount >= MANDATORY_VARIATION_THRESHOLD;
  const isOptionalRange = accountCount >= 2 && accountCount <= OPTIONAL_VARIATION_MAX;
  const canGeneratePreview =
    text.trim().length > 0 &&
    text.length <= 280 &&
    accountCount > 0 &&
    !media.isUploading &&
    !media.hasErrors;

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

  const resetComposer = () => {
    setText("");
    setSelectedAccountIds([]);
    setApplyVariation(true);
    setCreatedPostId(null);
    media.reset();
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
        description="Escreva uma vez, publique em várias contas — com variações naturais geradas por IA quando fizer sentido."
      />

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

            {isOptionalRange && (
              <div className="flex items-center justify-between rounded-lg border border-border bg-surface px-4 py-3">
                <div className="flex items-start gap-3">
                  <Sparkles className="mt-0.5 h-4 w-4 text-primary" />
                  <div>
                    <p className="text-sm font-medium text-foreground">Publicação Inteligente</p>
                    <p className="text-xs text-muted-foreground">
                      Gera uma variação natural do texto para cada conta, reduzindo o risco de
                      bloqueio por conteúdo repetitivo.
                    </p>
                  </div>
                </div>
                <Switch checked={applyVariation} onCheckedChange={setApplyVariation} />
              </div>
            )}

            {isMandatory && (
              <div className="flex items-start gap-3 rounded-lg border border-warning/30 bg-warning/10 px-4 py-3">
                <Sparkles className="mt-0.5 h-4 w-4 text-warning" />
                <p className="text-xs text-warning">
                  Você selecionou {accountCount} contas. A partir de 5 contas, a Publicação
                  Inteligente é obrigatória — o mesmo texto não pode ser publicado em todas elas.
                </p>
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
