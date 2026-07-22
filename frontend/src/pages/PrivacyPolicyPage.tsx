import { CONTACT_EMAIL } from "@/lib/constants";

export function PrivacyPolicyPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-16 sm:px-8">
      <h1 className="font-display text-3xl font-semibold text-foreground sm:text-4xl">
        Política de Privacidade
      </h1>
      <p className="mt-2 text-sm text-subtle-foreground">Última atualização: julho de 2026.</p>

      <div className="prose-invert mt-8 space-y-8 text-sm leading-relaxed text-muted-foreground">
        <section>
          <h2 className="text-base font-semibold text-foreground">1. Quem somos</h2>
          <p className="mt-2">
            O XHub é uma plataforma para gerenciar múltiplas contas do X (Twitter) e publicar
            conteúdo nelas. Esta política explica quais dados coletamos, por que coletamos e como
            você pode entrar em contato sobre eles. Dúvidas: {CONTACT_EMAIL}.
          </p>
        </section>

        <section>
          <h2 className="text-base font-semibold text-foreground">2. Dados que coletamos</h2>
          <p className="mt-2">
            <strong className="text-foreground">Da sua conta no XHub:</strong> nome, e-mail e senha
            (armazenada apenas como hash criptográfico — nunca em texto puro).
          </p>
          <p className="mt-2">
            <strong className="text-foreground">Das contas do X que você conecta:</strong> nome de
            usuário, nome de exibição, identificador da conta e foto de perfil pública, além dos
            tokens de acesso emitidos pelo X (armazenados de forma criptografada, nunca em texto
            puro). Nunca temos acesso à sua senha do X — a conexão é sempre feita pelo fluxo
            oficial de autorização (OAuth2).
          </p>
          <p className="mt-2">
            <strong className="text-foreground">Conteúdo que você cria:</strong> o texto e a mídia
            (imagem, gif ou vídeo) dos posts que você escreve para publicar através da plataforma.
          </p>
          <p className="mt-2">
            <strong className="text-foreground">Dados técnicos:</strong> endereço IP e metadados de
            requisição, usados para segurança (ex.: limitar tentativas de login) e para
            diagnosticar problemas — nunca para fins de publicidade.
          </p>
        </section>

        <section>
          <h2 className="text-base font-semibold text-foreground">3. Para que usamos esses dados</h2>
          <ul className="mt-2 list-disc space-y-1 pl-5">
            <li>Autenticar você e manter sua sessão.</li>
            <li>Publicar o conteúdo que você escreve nas contas do X que você conectou.</li>
            <li>
              Quando você ativa a Publicação Inteligente, o texto do seu post é enviado à Groq
              (fornecedora de IA usada para gerar variações naturais de texto) — apenas o texto do
              post em si, nunca seus dados de conta ou tokens.
            </li>
            <li>Mostrar o desempenho (impressões, curtidas, seguidores) das suas contas conectadas.</li>
            <li>Segurança da plataforma (prevenção de abuso, limite de tentativas de login).</li>
          </ul>
        </section>

        <section>
          <h2 className="text-base font-semibold text-foreground">4. Com quem compartilhamos</h2>
          <p className="mt-2">
            Não vendemos nem compartilhamos seus dados com terceiros para fins de publicidade.
            Usamos dois serviços de terceiros estritamente necessários ao funcionamento da
            plataforma: a <strong className="text-foreground">API do X (Twitter)</strong>, para
            conectar contas e publicar conteúdo, e a{" "}
            <strong className="text-foreground">Groq</strong>, para gerar variações de texto
            quando a Publicação Inteligente está ativa.
          </p>
        </section>

        <section>
          <h2 className="text-base font-semibold text-foreground">5. Como protegemos seus dados</h2>
          <p className="mt-2">
            Senhas são armazenadas apenas como hash (bcrypt), nunca em texto puro. Os tokens de
            acesso das suas contas do X são cifrados em repouso (criptografia autenticada) antes de
            serem gravados no banco de dados. O acesso à plataforma é protegido por limite de
            tentativas de login e headers de segurança contra ataques comuns de navegador.
          </p>
        </section>

        <section>
          <h2 className="text-base font-semibold text-foreground">6. Armazenamento no navegador</h2>
          <p className="mt-2">
            Para manter sua sessão ativa, o XHub guarda o token de acesso no armazenamento local do
            seu navegador (não usamos cookies de rastreamento nem de terceiros). Esse dado some ao
            limpar os dados do site ou ao encerrar a sessão.
          </p>
        </section>

        <section>
          <h2 className="text-base font-semibold text-foreground">7. Quanto tempo guardamos seus dados</h2>
          <p className="mt-2">
            Enquanto sua conta estiver ativa. Ao encerrar sua conta, você pode solicitar a remoção
            dos seus dados pessoais escrevendo para {CONTACT_EMAIL} — mantemos apenas o que a lei
            exigir ou o necessário para registros administrativos internos.
          </p>
        </section>

        <section>
          <h2 className="text-base font-semibold text-foreground">8. Seus direitos</h2>
          <p className="mt-2">
            Você pode solicitar, a qualquer momento, acesso, correção ou exclusão dos seus dados
            pessoais, ou revogar o acesso do XHub às suas contas do X (desconectando a conta
            diretamente na plataforma ou nas configurações de aplicativos autorizados do próprio
            X). Para qualquer solicitação, escreva para {CONTACT_EMAIL}.
          </p>
        </section>

        <section>
          <h2 className="text-base font-semibold text-foreground">9. Alterações nesta política</h2>
          <p className="mt-2">
            Podemos atualizar esta política periodicamente. Mudanças relevantes serão comunicadas
            aos clientes ativos por e-mail.
          </p>
        </section>
      </div>
    </div>
  );
}
