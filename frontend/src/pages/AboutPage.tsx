import { Link } from "react-router-dom";
import { Building2, ShieldCheck, Sparkles, Users } from "lucide-react";

const VALUES = [
  {
    icon: Sparkles,
    title: "Escala sem parecer automatizado",
    description:
      "Publicar o mesmo texto, ao mesmo tempo, em várias contas é o padrão mais fácil de identificar como automação. Por isso investimos em variação de texto por IA e em atraso natural entre publicações, desde o primeiro dia.",
  },
  {
    icon: ShieldCheck,
    title: "Segurança em primeiro lugar",
    description:
      "Nunca pedimos a senha da sua conta do X — a conexão é sempre feita pelo fluxo oficial de autorização (OAuth2). Tokens de acesso são armazenados de forma criptografada, nunca em texto puro.",
  },
  {
    icon: Users,
    title: "Feito para operações reais",
    description:
      "Agências, criadores e negócios que gerenciam múltiplas contas do X têm necessidades diferentes de um usuário publicando na própria conta pessoal — o XHub é desenhado para esse cenário desde a arquitetura.",
  },
];

export function AboutPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-16 sm:px-8">
      <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-full bg-primary/15 text-primary">
        <Building2 className="h-6 w-6" />
      </div>
      <h1 className="font-display text-3xl font-semibold text-foreground sm:text-4xl">
        Sobre o XHub
      </h1>
      <p className="mt-4 text-muted-foreground">
        O XHub nasceu para resolver um problema específico: gerenciar dezenas de contas do X ao
        mesmo tempo, publicando o mesmo conteúdo, sem que isso pareça (ou seja tratado pela
        plataforma como) um comportamento automatizado suspeito. Escrever o mesmo post uma vez e
        publicá-lo manualmente em cada conta não escala — e publicar tudo de forma idêntica e
        simultânea é o padrão mais fácil de detectar.
      </p>
      <p className="mt-4 text-muted-foreground">
        Por isso o XHub combina três coisas em um só lugar: um compositor único para escrever e
        anexar mídia, variação automática de texto por IA quando o número de contas selecionadas
        justifica, e um atraso natural e aleatório entre cada publicação — tudo enquanto você
        acompanha o resultado real de cada conta em um painel dedicado.
      </p>

      <div className="mt-10 space-y-6">
        {VALUES.map((value) => (
          <div key={value.title} className="flex gap-4">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/15 text-primary">
              <value.icon className="h-5 w-5" />
            </div>
            <div>
              <p className="font-medium text-foreground">{value.title}</p>
              <p className="mt-1 text-sm text-muted-foreground">{value.description}</p>
            </div>
          </div>
        ))}
      </div>

      <p className="mt-10 text-sm text-muted-foreground">
        Não temos autoatendimento — cada conta é configurada por nós, para garantir o plano certo
        desde o primeiro dia.{" "}
        <Link to="/contato" className="font-medium text-primary hover:underline">
          Fale com a gente
        </Link>{" "}
        para conhecer o XHub.
      </p>
    </div>
  );
}
