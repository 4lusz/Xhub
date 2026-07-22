import { CONTACT_EMAIL } from "@/lib/constants";

export function TermsOfUsePage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-16 sm:px-8">
      <h1 className="font-display text-3xl font-semibold text-foreground sm:text-4xl">
        Termos de Uso
      </h1>
      <p className="mt-2 text-sm text-subtle-foreground">Última atualização: julho de 2026.</p>

      <div className="mt-8 space-y-8 text-sm leading-relaxed text-muted-foreground">
        <section>
          <h2 className="text-base font-semibold text-foreground">1. Aceitação dos termos</h2>
          <p className="mt-2">
            Ao usar o XHub, você concorda com estes termos. Se você estiver usando a plataforma em
            nome de uma empresa ou agência, você declara ter autoridade para aceitar estes termos
            em nome dela.
          </p>
        </section>

        <section>
          <h2 className="text-base font-semibold text-foreground">2. Contas e acesso</h2>
          <p className="mt-2">
            O XHub não oferece cadastro público — toda conta é criada por nós, após contato prévio
            (ver página de Contato), e vinculada a um plano específico. Você é responsável por
            manter suas credenciais de acesso em sigilo e por toda atividade realizada com sua
            conta. Toda conta nova recebe uma senha temporária e é obrigada a defini-la novamente
            no primeiro acesso.
          </p>
        </section>

        <section>
          <h2 className="text-base font-semibold text-foreground">3. Uso permitido</h2>
          <p className="mt-2">
            Você concorda em usar o XHub apenas para publicar conteúdo em contas do X que você tem
            autorização legítima para gerenciar, e em cumprir os Termos de Serviço e a Política de
            Uso do X (Twitter) em toda publicação feita através da plataforma. O XHub pode
            suspender ou encerrar contas que violem estes termos ou as regras da plataforma do X.
          </p>
        </section>

        <section>
          <h2 className="text-base font-semibold text-foreground">4. Conteúdo publicado</h2>
          <p className="mt-2">
            Você é o único responsável pelo conteúdo que escreve e publica através do XHub,
            incluindo texto, imagens, gifs e vídeos. O XHub nunca publica conteúdo em seu nome sem
            uma ação explícita sua (publicar ou agendar). Recursos como a Publicação Inteligente
            geram variações de texto, mas sempre a partir do que você escreveu, e o preview final é
            sempre revisável antes da publicação.
          </p>
        </section>

        <section>
          <h2 className="text-base font-semibold text-foreground">5. Conexão de contas do X</h2>
          <p className="mt-2">
            A conexão de contas do X é feita exclusivamente pelo fluxo oficial de autorização
            (OAuth2) do próprio X — o XHub nunca solicita nem armazena sua senha do X. Você pode
            revogar esse acesso a qualquer momento, desconectando a conta na plataforma ou
            diretamente nas configurações de aplicativos autorizados do X.
          </p>
        </section>

        <section>
          <h2 className="text-base font-semibold text-foreground">6. Planos e cobrança</h2>
          <p className="mt-2">
            Planos, limites (número de contas conectadas, volume mensal de publicações) e valores
            são definidos previamente, por escrito, no momento da configuração da sua conta.
            Alterações de plano são feitas mediante solicitação para {CONTACT_EMAIL}.
          </p>
        </section>

        <section>
          <h2 className="text-base font-semibold text-foreground">7. Disponibilidade do serviço</h2>
          <p className="mt-2">
            Fazemos o possível para manter o XHub disponível de forma contínua, mas não garantimos
            disponibilidade ininterrupta. Funcionalidades que dependem de serviços de terceiros
            (API do X, geração de variações por IA) podem ser afetadas por instabilidades desses
            provedores, fora do nosso controle.
          </p>
        </section>

        <section>
          <h2 className="text-base font-semibold text-foreground">8. Limitação de responsabilidade</h2>
          <p className="mt-2">
            O XHub é uma ferramenta de gestão e publicação — não somos responsáveis por decisões de
            moderação, suspensão ou banimento tomadas pelo X (Twitter) sobre contas conectadas à
            plataforma, nem pelo conteúdo publicado pelos usuários.
          </p>
        </section>

        <section>
          <h2 className="text-base font-semibold text-foreground">9. Encerramento</h2>
          <p className="mt-2">
            Você pode solicitar o encerramento da sua conta a qualquer momento, escrevendo para{" "}
            {CONTACT_EMAIL}. Podemos suspender ou encerrar contas que violem estes termos, com
            aviso prévio sempre que possível.
          </p>
        </section>

        <section>
          <h2 className="text-base font-semibold text-foreground">10. Alterações nestes termos</h2>
          <p className="mt-2">
            Podemos atualizar estes termos periodicamente. Mudanças relevantes serão comunicadas
            aos clientes ativos por e-mail. Dúvidas: {CONTACT_EMAIL}.
          </p>
        </section>
      </div>
    </div>
  );
}
