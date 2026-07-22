import { Mail } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CONTACT_EMAIL } from "@/lib/constants";

export function ContactPage() {
  return (
    <div className="mx-auto max-w-2xl px-4 py-16 sm:px-8">
      <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-full bg-primary/15 text-primary">
        <Mail className="h-6 w-6" />
      </div>
      <h1 className="font-display text-3xl font-semibold text-foreground sm:text-4xl">
        Fale com a gente
      </h1>
      <p className="mt-4 text-muted-foreground">
        O XHub não tem cadastro público — cada conta é criada por nós, depois de entender o
        tamanho da sua operação (quantas contas do X você precisa conectar, volume de publicações)
        para indicar o plano certo. Escreva para o e-mail abaixo contando um pouco sobre o seu
        caso.
      </p>

      <Card className="mt-8">
        <CardHeader>
          <CardTitle className="text-base">E-mail para contato comercial e suporte</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="font-display text-xl font-semibold text-primary">{CONTACT_EMAIL}</p>
          <Button asChild size="lg">
            <a href={`mailto:${CONTACT_EMAIL}`}>
              <Mail className="h-4 w-4" />
              Enviar e-mail
            </a>
          </Button>
          <p className="text-xs text-subtle-foreground">
            Costumamos responder em até 1 dia útil. Se você já é cliente e precisa de suporte
            técnico, use o mesmo e-mail.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
