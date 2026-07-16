import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Loader2, UserPlus } from "lucide-react";
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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { DateTimePicker } from "@/components/common/DateTimePicker";
import { useCreateUser } from "@/hooks/useAdminUsers";
import { usePlans } from "@/hooks/useAdminPlans";

const createUserSchema = z.object({
  name: z.string().min(1, "Informe o nome."),
  email: z.string().min(1, "Informe o e-mail.").email("E-mail inválido."),
  password: z.string().min(8, "A senha deve ter ao menos 8 caracteres."),
  role: z.enum(["client", "admin"]),
  plan_id: z.string().min(1, "Selecione um plano."),
  subscription_expires_at: z.string().min(1, "Defina a validade da assinatura."),
});

type CreateUserFormValues = z.infer<typeof createUserSchema>;

function defaultExpiryLocal(): string {
  const date = new Date();
  date.setDate(date.getDate() + 30);
  const offset = date.getTimezoneOffset();
  const local = new Date(date.getTime() - offset * 60 * 1000);
  return local.toISOString().slice(0, 16);
}

export function CreateUserDialog() {
  const [open, setOpen] = useState(false);
  const { data: plans } = usePlans();
  const createUser = useCreateUser();

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    reset,
    formState: { errors },
  } = useForm<CreateUserFormValues>({
    resolver: zodResolver(createUserSchema),
    defaultValues: {
      role: "client",
      subscription_expires_at: defaultExpiryLocal(),
    },
  });

  const role = watch("role");
  const planId = watch("plan_id");

  const onSubmit = (values: CreateUserFormValues) => {
    createUser.mutate(
      {
        ...values,
        subscription_expires_at: new Date(values.subscription_expires_at).toISOString(),
      },
      {
        onSuccess: () => {
          setOpen(false);
          reset({ role: "client", subscription_expires_at: defaultExpiryLocal() });
        },
      },
    );
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <UserPlus className="h-4 w-4" />
          Novo usuário
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Criar usuário</DialogTitle>
          <DialogDescription>
            O plano escolhido cria a assinatura do usuário automaticamente.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
          <div className="space-y-2">
            <Label htmlFor="name">Nome</Label>
            <Input id="name" {...register("name")} />
            {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
          </div>

          <div className="space-y-2">
            <Label htmlFor="email">E-mail</Label>
            <Input id="email" type="email" {...register("email")} />
            {errors.email && <p className="text-xs text-destructive">{errors.email.message}</p>}
          </div>

          <div className="space-y-2">
            <Label htmlFor="password">Senha temporária</Label>
            <Input id="password" type="password" {...register("password")} />
            <p className="text-xs text-muted-foreground">
              No primeiro login, o usuário será obrigado a trocá-la por uma senha definitiva.
            </p>
            {errors.password && (
              <p className="text-xs text-destructive">{errors.password.message}</p>
            )}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label>Papel</Label>
              <Select value={role} onValueChange={(value) => setValue("role", value as "client" | "admin")}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="client">Cliente</SelectItem>
                  <SelectItem value="admin">Administrador</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Plano</Label>
              <Select value={planId} onValueChange={(value) => setValue("plan_id", value)}>
                <SelectTrigger>
                  <SelectValue placeholder="Selecione" />
                </SelectTrigger>
                <SelectContent>
                  {plans?.map((plan) => (
                    <SelectItem key={plan.id} value={plan.id}>
                      {plan.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {errors.plan_id && (
                <p className="text-xs text-destructive">{errors.plan_id.message}</p>
              )}
            </div>
          </div>

          <div className="space-y-2">
            <Label>Assinatura válida até</Label>
            <DateTimePicker
              value={watch("subscription_expires_at")}
              onChange={(value) => setValue("subscription_expires_at", value)}
            />
            {errors.subscription_expires_at && (
              <p className="text-xs text-destructive">{errors.subscription_expires_at.message}</p>
            )}
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>
              Cancelar
            </Button>
            <Button type="submit" disabled={createUser.isPending}>
              {createUser.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              Criar usuário
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
