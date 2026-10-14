"""Página inicial e política de privacidade públicas, exigidas pela tela de
consentimento OAuth do Google e pela auditoria da API do YouTube."""
from __future__ import annotations

import html
import os

APP_NAME = os.environ.get("APP_PUBLIC_NAME", "Fábrica de Vídeos")
CONTACT = os.environ.get("CONTACT_EMAIL", "")
UPDATED = "14 de outubro de 2026"

_STYLE = """
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;max-width:760px;margin:40px auto;padding:0 16px;
line-height:1.6;color:#1f2328;background:#fff}
h1{font-size:1.6rem}h2{font-size:1.15rem;margin-top:1.8rem}a{color:#0969da}
footer{margin-top:3rem;font-size:.9rem;color:#57606a}
@media (prefers-color-scheme:dark){body{background:#0d1117;color:#e6edf3}a{color:#4493f8}footer{color:#8d96a0}}
"""


def _page(title: str, body: str) -> str:
    contact = (f'<a href="mailto:{html.escape(CONTACT)}">{html.escape(CONTACT)}</a>'
               if CONTACT else "o e-mail de suporte informado na tela de autorização do Google")
    return (f"<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'>"
            f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{html.escape(title)} · {html.escape(APP_NAME)}</title><style>{_STYLE}</style></head>"
            f"<body>{body.replace('{{contact}}', contact)}"
            f"<footer><a href='/'>Início</a> · <a href='/privacidade'>Política de Privacidade</a> · "
            f"<a href='/termos'>Termos de Uso</a></footer></body></html>")


def home() -> str:
    return _page("Início", f"""
<h1>{html.escape(APP_NAME)}</h1>
<p>{html.escape(APP_NAME)} é uma ferramenta interna e privada usada pelo seu proprietário para produzir
vídeos animados e enviá-los aos <strong>seus próprios canais</strong> do YouTube.</p>
<p>O que ela faz:</p>
<ul>
<li>gera roteiro, narração, imagens e a montagem de vídeos;</li>
<li>envia cada vídeo ao YouTube como privado, com data de publicação agendada, somente depois de uma
aprovação humana;</li>
<li>lê estatísticas de audiência dos próprios canais para melhorar os próximos vídeos.</li>
</ul>
<p>A ferramenta não é oferecida ao público e não acessa contas ou canais de terceiros.</p>
<p>Contato: {{{{contact}}}}.</p>
""")


def privacy() -> str:
    return _page("Política de Privacidade", f"""
<h1>Política de Privacidade</h1>
<p>Última atualização: {UPDATED}.</p>

<h2>Quem somos</h2>
<p>{html.escape(APP_NAME)} é uma ferramenta privada operada pelo seu proprietário para publicar vídeos nos
seus próprios canais do YouTube. Ela usa os Serviços de API do YouTube.</p>

<h2>Serviços de API do YouTube</h2>
<p>Ao autorizar esta ferramenta, você concorda com os
<a href="https://www.youtube.com/t/terms">Termos de Serviço do YouTube</a>. Os dados acessados pelo Google
seguem a <a href="https://policies.google.com/privacy">Política de Privacidade do Google</a>.</p>

<h2>Dados que acessamos</h2>
<ul>
<li><strong>Autorização OAuth</strong> da conta Google dona do canal (tokens de acesso), usada apenas para
enviar vídeos, definir thumbnails e agendar publicações nesse canal.</li>
<li><strong>Estatísticas de audiência</strong> dos vídeos do próprio canal (visualizações e retenção), usadas
apenas para planejar os próximos vídeos.</li>
</ul>
<p>Não coletamos dados de espectadores, comentaristas ou de quaisquer outros usuários do YouTube.</p>

<h2>Como usamos e guardamos</h2>
<ul>
<li>Os tokens ficam armazenados de forma criptografada no servidor de automação do proprietário e nunca são
compartilhados.</li>
<li>Os arquivos de vídeo e as estatísticas ficam em servidor privado do proprietário.</li>
<li>Estatísticas obtidas da API são atualizadas ou apagadas em até 30 dias, conforme as políticas dos
Serviços de API do YouTube.</li>
</ul>

<h2>Compartilhamento</h2>
<p>Não vendemos, alugamos nem compartilhamos dados com terceiros. Os dados não são usados para publicidade.</p>

<h2>Como revogar o acesso</h2>
<p>Você pode revogar o acesso a qualquer momento na página de
<a href="https://myaccount.google.com/permissions">permissões de segurança da sua Conta Google</a>.
Após a revogação, os tokens deixam de funcionar e os dados armazenados relacionados são apagados em até 7 dias,
ou antes, mediante pedido.</p>

<h2>Contato</h2>
<p>Dúvidas ou pedidos de exclusão de dados: {{{{contact}}}}.</p>
""")


def terms() -> str:
    return _page("Termos de Uso", f"""
<h1>Termos de Uso</h1>
<p>Última atualização: {UPDATED}.</p>
<p>{html.escape(APP_NAME)} é uma ferramenta de uso exclusivo do seu proprietário, para publicação de conteúdo
nos seus próprios canais. Não há usuários externos nem oferta comercial da ferramenta.</p>
<p>O uso dos Serviços de API do YouTube está sujeito aos
<a href="https://www.youtube.com/t/terms">Termos de Serviço do YouTube</a>.</p>
<p>Contato: {{{{contact}}}}.</p>
""")
