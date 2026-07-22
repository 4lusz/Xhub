import { Link } from "react-router-dom";
import {
  AtSign,
  BarChart3,
  CalendarClock,
  Image as ImageIcon,
  Mail,
  Shield,
  Shuffle,
  Sparkles,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const FEATURES = [
  {
    icon: AtSign,
    title: "Múltiplas contas, um clique",
    description:
      "Conecte quantas contas do X sua operação precisar e publique em todas de uma vez, sem repetir o trabalho manualmente em cada uma.",
  },
  {
    icon: Sparkles,
    title: "Publicação Inteligente",
    description:
      "Variações naturais do mesmo texto, geradas por IA, reduzindo o risco de bloqueio por conteúdo repetitivo — links, hashtags e menções nunca são alterados.",
  },
  {
    icon: Shuffle,
    title: "Jitter entre publicações",
    description:
      "Um atraso natural e aleatório entre as publicações em contas diferentes, para que a sequência nunca pareça automatizada.",
  },
  {
    icon: ImageIcon,
    title: "Imagens, GIFs e vídeos",
    description:
      "Anexe mídia com preview, corte e ajuste direto no navegador antes de publicar — a mesma mídia em todas as contas selecionadas.",
  },
  {
    icon: CalendarClock,
    title: "Agendamento",
    description:
      "Programe uma publicação para o horário certo e deixe o XHub cuidar do resto, com novas tentativas automáticas em caso de falha.",
  },
  {
    icon: BarChart3,
    title: "Resultados por conta",
    description:
      "Acompanhe impressões, curtidas e seguidores de cada conta conectada, com alerta automático quando o alcance cai.",
  },
];

const STEPS = [
  {
    title: "1. Fale com a gente",
    description: "Conte o tamanho da sua operação e escolhemos o plano certo para você.",
  },
  {
    title: "2. Conecte suas contas",
    description: "Autorize suas contas do X pelo fluxo oficial — nunca pedimos sua senha do X.",
  },
  {
    title: "3. Escreva uma vez, publique em todas",
    description: "Um texto, várias contas, com variação automática quando fizer sentido.",
  },
];

export function LandingPage() {
  return (
    <div>
      <section className="relative overflow-hidden">
        <div className="pointer-events-none absolute inset-0 bg-grid-fade" />
        <div
          className="pointer-events-none absolute left-1/2 top-0 h-[560px] w-[560px] -translate-x-1/2 -translate-y-1/3 rounded-full bg-primary/10 blur-[120px]"
          aria-hidden="true"
        />

        <div className="relative mx-auto max-w-4xl px-4 py-24 text-center sm:px-8">
          <h1 className="font-display text-4xl font-semibold tracking-tight text-foreground sm:text-5xl">
            Publique no X em várias contas, de uma vez só.
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-lg text-muted-foreground">
            O XHub gerencia múltiplas contas do X para agências e operações que precisam publicar
            o mesmo conteúdo em escala — com variação de texto por IA, atraso natural entre
            publicações e resultados por conta, tudo em um só lugar.
          </p>
          <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Button asChild size="lg">
              <Link to="/contato">
                <Mail className="h-4 w-4" />
                Falar com a gente
              </Link>
            </Button>
            <Button asChild size="lg" variant="outline">
              <Link to="/login">Já sou cliente — Entrar</Link>
            </Button>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-16 sm:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="font-display text-2xl font-semibold text-foreground sm:text-3xl">
            Feito para quem gerencia muitas contas
          </h2>
          <p className="mt-3 text-muted-foreground">
            Cada funcionalidade existe para resolver um problema real de quem publica o mesmo
            conteúdo em múltiplas contas do X.
          </p>
        </div>

        <div className="mt-10 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((feature) => (
            <Card key={feature.title} className="transition-colors hover:border-border-strong">
              <CardHeader>
                <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-lg bg-primary/15 text-primary">
                  <feature.icon className="h-5 w-5" />
                </div>
                <CardTitle className="text-base">{feature.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">{feature.description}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      <section className="border-y border-border bg-surface/40">
        <div className="mx-auto max-w-5xl px-4 py-16 sm:px-8">
          <h2 className="text-center font-display text-2xl font-semibold text-foreground sm:text-3xl">
            Como funciona
          </h2>

          <div className="mt-10 grid grid-cols-1 gap-8 sm:grid-cols-3">
            {STEPS.map((step) => (
              <div key={step.title} className="text-center sm:text-left">
                <p className="font-display text-lg font-semibold text-primary">{step.title}</p>
                <p className="mt-2 text-sm text-muted-foreground">{step.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-3xl px-4 py-20 text-center sm:px-8">
        <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-full bg-primary/15 text-primary">
          <Shield className="h-6 w-6" />
        </div>
        <h2 className="font-display text-2xl font-semibold text-foreground sm:text-3xl">
          Não existe autoatendimento — de propósito
        </h2>
        <p className="mx-auto mt-3 max-w-xl text-muted-foreground">
          Toda conta do XHub é configurada por nós, para garantir o plano certo desde o primeiro
          dia. Escreva para a gente e explicamos as opções.
        </p>
        <Button asChild size="lg" className="mt-6">
          <Link to="/contato">
            <Mail className="h-4 w-4" />
            Falar com a gente
          </Link>
        </Button>
      </section>
    </div>
  );
}
