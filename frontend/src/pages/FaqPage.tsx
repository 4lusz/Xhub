import { ChevronDown, HelpCircle } from "lucide-react";

import { CONTACT_EMAIL } from "@/lib/constants";

const FAQ_ITEMS = [
  {
    question: "Preciso dar minha senha do X para o XHub?",
    answer:
      "Não, nunca. A conexão é sempre feita pelo fluxo oficial de autorização do X (OAuth2) — você autoriza o acesso diretamente no site do X, e o XHub nunca vê nem armazena sua senha.",
  },
  {
    question: "Como faço para criar uma conta?",
    answer: `O XHub não tem cadastro público. Escreva para ${CONTACT_EMAIL} contando o tamanho da sua operação (quantas contas do X, volume de publicações) e configuramos o plano certo para você.`,
  },
  {
    question: "O que acontece se eu publicar o mesmo texto em várias contas ao mesmo tempo?",
    answer:
      "É exatamente o padrão que tentamos evitar: publicar de forma idêntica e simultânea aumenta o risco de a plataforma tratar isso como comportamento automatizado. Por isso o XHub oferece variação de texto por IA (a partir de 2 contas selecionadas, obrigatória a partir de 5) e um atraso natural entre cada publicação.",
  },
  {
    question: "A variação de texto por IA pode mudar links, hashtags ou menções do meu post?",
    answer:
      "Não. É uma regra rígida do sistema: qualquer variação que altere um link, hashtag, @menção ou emoji do texto original é descartada automaticamente, nunca publicada — mesmo que a IA tente gerar algo assim.",
  },
  {
    question: "Quais tipos de mídia posso publicar?",
    answer:
      "Imagens (JPEG, PNG, WEBP), GIF e vídeo (MP4), com corte e ajuste direto no navegador antes de publicar. A mesma mídia é publicada em todas as contas selecionadas.",
  },
  {
    question: "Consigo agendar uma publicação?",
    answer:
      "Sim. Escolha a data e o horário, e o XHub publica automaticamente quando chegar a hora, com nova tentativa automática em caso de falha temporária.",
  },
  {
    question: "Meus dados e os tokens das minhas contas do X ficam seguros?",
    answer:
      "Os tokens de acesso das suas contas do X são armazenados de forma criptografada, nunca em texto puro. Veja mais detalhes na nossa Política de Privacidade.",
  },
  {
    question: "Como funciona o suporte?",
    answer: `Pelo mesmo e-mail do contato comercial: ${CONTACT_EMAIL}. Costumamos responder em até 1 dia útil.`,
  },
];

export function FaqPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-16 sm:px-8">
      <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-full bg-primary/15 text-primary">
        <HelpCircle className="h-6 w-6" />
      </div>
      <h1 className="font-display text-3xl font-semibold text-foreground sm:text-4xl">
        Perguntas frequentes
      </h1>
      <p className="mt-4 text-muted-foreground">
        Não achou o que procurava?{" "}
        <a href={`mailto:${CONTACT_EMAIL}`} className="font-medium text-primary hover:underline">
          Fale com a gente
        </a>
        .
      </p>

      <div className="mt-8 divide-y divide-border rounded-lg border border-border">
        {FAQ_ITEMS.map((item) => (
          <details key={item.question} className="group px-5 py-4">
            <summary className="flex cursor-pointer list-none items-center justify-between gap-4 text-sm font-medium text-foreground marker:content-none">
              {item.question}
              <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground transition-transform group-open:rotate-180" />
            </summary>
            <p className="mt-3 text-sm text-muted-foreground">{item.answer}</p>
          </details>
        ))}
      </div>
    </div>
  );
}
