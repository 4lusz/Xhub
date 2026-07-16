import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Loader2, Pencil } from "lucide-react";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useUpdatePlan } from "@/hooks/useAdminPlans";
import type { Plan } from "@/types/plan";

// `min(0.01, ...)` espelha a validação do backend (`UpdatePlanRequest.price:
// float = Field(gt=0)`, ver app/routes/admin.py) -- preço precisa ser
// maior que zero, nunca apenas não-negativo. Sem isso, o formulário
// aceitava 0 e só falhava depois, no servidor, com um 422.
const editPlanSchema = z.object({
  price: z.coerce.number().min(0.01, "O preço deve ser maior que zero."),
  max_accounts: z.coerce.number().int().min(1, "Mínimo de 1 conta."),
  max_posts_month: z.coerce.number().int().min(1, "Mínimo de 1 post por mês."),
});

type EditPlanFormValues = z.infer<typeof editPlanSchema>;

export function EditPlanDialog({ plan }: { plan: Plan }) {
  const [open, setOpen] = useState(false);
  const updatePlan = useUpdatePlan();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<EditPlanFormValues>({
    resolver: zodResolver(editPlanSchema),
    defaultValues: {
      price: plan.price,
      max_accounts: plan.max_accounts,
      max_posts_month: plan.max_posts_month,
    },
  });

  const onSubmit = (values: EditPlanFormValues) => {
    updatePlan.mutate(
      { planId: plan.id, payload: values },
      { onSuccess: () => setOpen(false) },
    );
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm">
          <Pencil className="h-3.5 w-3.5" />
          Editar
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>Editar {plan.name}</DialogTitle>
          <DialogDescription>
            Limites e características vêm do catálogo oficial — o preço é definido manualmente.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
          <div className="space-y-2">
            <Label htmlFor="price">Preço (R$)</Label>
            <Input id="price" type="number" step="0.01" min={0.01} {...register("price")} />
            {errors.price && <p className="text-xs text-destructive">{errors.price.message}</p>}
          </div>

          <div className="space-y-2">
            <Label htmlFor="max_accounts">Máximo de contas do X</Label>
            <Input id="max_accounts" type="number" min={1} {...register("max_accounts")} />
            {errors.max_accounts && (
              <p className="text-xs text-destructive">{errors.max_accounts.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="max_posts_month">Posts por mês</Label>
            <Input id="max_posts_month" type="number" min={1} {...register("max_posts_month")} />
            {errors.max_posts_month && (
              <p className="text-xs text-destructive">{errors.max_posts_month.message}</p>
            )}
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>
              Cancelar
            </Button>
            <Button type="submit" disabled={updatePlan.isPending}>
              {updatePlan.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              Salvar
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
