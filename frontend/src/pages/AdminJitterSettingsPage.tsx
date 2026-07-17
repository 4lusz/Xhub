import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { Loader2, Save, Shuffle } from "lucide-react";
import { z } from "zod";

import { PageHeader } from "@/components/common/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { useJitterSettings, useUpdateJitterSettings } from "@/hooks/useAdminJitterSettings";

// Espelha `settings.JITTER_MAX_ALLOWED_SECONDS` (ver
// app/config/settings.py) -- só um limite de UX para feedback
// imediato; o backend é quem de fato aplica e valida este teto.
const JITTER_MAX_ALLOWED_SECONDS = 120;

const jitterSettingsSchema = z
  .object({
    min_seconds: z.coerce.number().min(0, "O tempo mínimo não pode ser negativo."),
    max_seconds: z.coerce
      .number()
      .min(0, "O tempo máximo não pode ser negativo.")
      .max(
        JITTER_MAX_ALLOWED_SECONDS,
        `O tempo máximo não pode exceder ${JITTER_MAX_ALLOWED_SECONDS} segundos.`,
      ),
  })
  .refine((data) => data.max_seconds >= data.min_seconds, {
    message: "O tempo máximo não pode ser menor que o tempo mínimo.",
    path: ["max_seconds"],
  });

type JitterSettingsFormValues = z.infer<typeof jitterSettingsSchema>;

/**
 * Configuração administrativa do Jitter (ver docs/ROADMAP_JITTER.md):
 * atraso aleatório aplicado entre publicações em contas diferentes do
 * mesmo post, para tornar a sequência de chamadas à API do X menos
 * automatizada. Puramente operacional -- não há nada para o cliente
 * final ver ou configurar; esta tela é exclusiva do administrador.
 */
export function AdminJitterSettingsPage() {
  const jitterQuery = useJitterSettings();
  const updateJitter = useUpdateJitterSettings();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<JitterSettingsFormValues>({
    resolver: zodResolver(jitterSettingsSchema),
  });

  useEffect(() => {
    if (jitterQuery.data) {
      reset({
        min_seconds: jitterQuery.data.min_seconds,
        max_seconds: jitterQuery.data.max_seconds,
      });
    }
  }, [jitterQuery.data, reset]);

  const onSubmit = (values: JitterSettingsFormValues) => {
    updateJitter.mutate(values);
  };

  return (
    <div className="space-y-8">
      <PageHeader
        title="Jitter"
        description="Atraso aleatório entre publicações em contas diferentes do mesmo post, para reduzir padrões automatizados. Não afeta a experiência do cliente -- apenas o ritmo interno de publicação."
      />

      <Card className="max-w-md">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Shuffle className="h-4 w-4 text-primary" />
            Intervalo do atraso
          </CardTitle>
          <CardDescription>
            Quando um post tem mais de uma conta, cada publicação (a partir da segunda) espera um
            tempo aleatório dentro deste intervalo antes de ocorrer. Um novo valor é sorteado a
            cada publicação -- nunca é reutilizado.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {jitterQuery.isLoading ? (
            <div className="space-y-4">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : (
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
              <div className="space-y-2">
                <Label htmlFor="min_seconds">Tempo mínimo (segundos)</Label>
                <Input id="min_seconds" type="number" step="0.1" min={0} {...register("min_seconds")} />
                {errors.min_seconds && (
                  <p className="text-xs text-destructive">{errors.min_seconds.message}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="max_seconds">Tempo máximo (segundos)</Label>
                <Input
                  id="max_seconds"
                  type="number"
                  step="0.1"
                  min={0}
                  max={JITTER_MAX_ALLOWED_SECONDS}
                  {...register("max_seconds")}
                />
                {errors.max_seconds && (
                  <p className="text-xs text-destructive">{errors.max_seconds.message}</p>
                )}
              </div>

              <Button type="submit" disabled={updateJitter.isPending}>
                {updateJitter.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Save className="h-4 w-4" />
                )}
                Salvar
              </Button>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
