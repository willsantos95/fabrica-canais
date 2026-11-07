"""Roteiro e shotlist (formato stickman) escritos pelo Claude para o canal "Um Ano Preso".
História original e fictícia (empresa, pessoas e casos inventados). Regras de teleatendimento
(NR-17 Anexo II), fim do prefixo 0303 e Não Me Perturbe vêm das fontes.
Plano = (narração, cenário ou cena, selo, actors | None, fx | None)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _compact import save  # noqa: E402

CHANNEL = "um-ano-preso"
TITLE = "Fiquei Preso 1 Ano Como Operador de Telemarketing"
PRIORITY = 10

SOURCES = [
    {"id": "src1", "title": "NR-17 Anexo II — Trabalho em teleatendimento/telemarketing (Ministério do Trabalho e Emprego)",
     "url": "https://www.gov.br/trabalho-e-emprego/pt-br/acesso-a-informacao/participacao-social/conselhos-e-orgaos-colegiados/comissao-tripartite-partitaria-permanente/arquivos/normas-regulamentadoras/nr-17-anexo-ii-teleatendimento-atualizado-2021.pdf",
     "claim": "Tempo efetivo de no máximo 6 horas por dia, com as pausas incluídas; duas pausas de 10 minutos e intervalo de 20 minutos para refeição; ir ao banheiro a qualquer momento sem prejuízo na avaliação; pausa imediata depois de ameaça ou abuso verbal; é vedado exigir seguir o script ao pé da letra; monitoramento não pode ser usado para acelerar o trabalho."},
    {"id": "src2", "title": "Prefixo 0303 não é mais obrigatório para telemarketing — Baguete (agosto de 2025)",
     "url": "https://www.baguete.com.br/noticias/prefixo-0303-nao-e-mais-obrigatorio-para-telemarketing",
     "claim": "A Anatel revogou a obrigatoriedade do prefixo 0303, criada em 2022, porque o código passou a ser associado a ligações indesejadas e rejeitado; no lugar, exigiu a origem verificada, que mostra quem liga e o motivo."},
    {"id": "src3", "title": "Anatel dá prazo para bancos e operadoras entrarem no Não Me Perturbe — meutudo (setembro de 2025)",
     "url": "https://meutudo.com.br/blog/noticias/2025/09/05/anatel-da-prazo-para-bancos-e-operadoras-entrarem-no-nao-me-perturbe/",
     "claim": "O Não Me Perturbe é uma plataforma gratuita, de 2019, para bloquear telemarketing de bancos e operadoras; em 2025 a Anatel tornou a adesão obrigatória para essas empresas; o bloqueio vale em até 30 dias após o pedido; a Anatel fiscaliza pelas denúncias."},
]

FLOOR = "a huge crowded call center floor with long rows of small cubicles, headsets on every desk, monitors and fluorescent ceiling lights"
BAIA = "a tiny call center cubicle with a headset, a monitor full of script text and a sticky note with a sales goal number"
SUP = "a call center floor in front of a big wall screen showing a ranking of operators with green and red bars"
BREAK = "a small call center break room with a vending machine, a bench and a big wall clock"
HOME = "a simple old living room with a landline phone on a small wooden table, an old radio and a window with afternoon light"
STREET = "an empty city bus stop at night under a street lamp"

YOU, SANDRO, NEIDE, JOAQUIM = "you", "extra", "nina", "tomas"


def A(who, action="idle", x=0.5, **kw):
    return {"who": who, "action": action, "x": x, **kw}


PLANS = [
    ("b01", "A baia quarenta e sete", [], [
        ("O aluguel venceu, a geladeira está vazia, e o único lugar que te chamou para entrevista foi uma central de telemarketing. Você começa na segunda.",
         "a cartoon fridge with its door open and completely empty, an overdue rent bill stuck with a magnet", "DIA 0", None, None),
        ("A Central Fala Já ocupa três andares. Seiscentas baias iguais, seiscentos fones de ouvido, e um barulho de fundo que nunca para.",
         FLOOR, "DIA 1", [A(YOU, "walk", 0.12, to=0.48)], None),
        ("Você recebe um crachá, um fone e um número: baia quarenta e sete. A partir de hoje, você é a P A quarenta e sete.",
         "a call center ID badge with the number 47 next to a headset on a desk, cartoon style", "DIA 1", None, None),
        ("O seu supervisor é o Sandro. Gravata torta, prancheta na mão, e uma frase que ele repete o dia inteiro: meta é meta.",
         FLOOR, "DIA 1", [A(SANDRO, "talk", 0.62, facing=-1), A(YOU, "idle", 0.36, facing=1)], None),
        ("A meta: vender trinta planos de internet por mês. Quem bater ganha bônus. Quem não bater, o Sandro chama para conversar.",
         BAIA + ", a sticky note on the monitor with the number 30 circled in red", "DIA 1", [A(YOU, "sit", 0.45)], None),
        ("Na baia do lado, a Dona Neide, vinte anos de casa, te olha por cima dos óculos de leitura e diz: respira, menino. O primeiro mês é o pior.",
         BAIA, "DIA 1", [A(NEIDE, "talk", 0.64, facing=-1), A(YOU, "sit", 0.36, facing=1)], None),
        ("Você coloca o fone. O discador liga sozinho, sem você apertar nada. Alguém atende. Você abre a boca para ler o script.",
         BAIA + ", a computer screen showing an automatic dialer connecting a call", "DIA 1", [A(YOU, "talk", 0.45)], None),
        ("O script tem três páginas. Bom dia, meu nome é tal, estou ligando da operadora tal, com uma oferta exclusiva para o seu endereço. Você leu tantas vezes no treinamento que sonhou com ele.",
         BAIA + ", a long printed script taped to the cubicle wall", "DIA 1", [A(YOU, "sit", 0.45)], None),
        ("A pessoa desliga antes do bom dia. A segunda também. A terceira te xinga de um jeito que você nem sabia que existia.",
         BAIA, "DIA 1", [A(YOU, "scared", 0.45)], None),
    ]),
    ("b02", "As regras", ["src1"], [
        ("Na primeira semana, você aprende que existe uma regra só para o seu trabalho. Uma norma do Ministério do Trabalho, com um anexo inteiro sobre teleatendimento.",
         "a cartoon government rule book titled 'NR-17 ANEXO II' on a desk next to a headset", "DIA 5", None, None),
        ("Ela diz que o tempo de trabalho é de no máximo seis horas por dia, já contando as pausas. Duas pausas de dez minutos. E vinte minutos para comer.",
         "a cartoon clock divided into a 6-hour shift with two small 10-minute breaks and one 20-minute meal break marked", "DIA 5", None, None),
        ("Ela diz também que você pode ir ao banheiro quando precisar, sem que isso conte contra você. E que ninguém pode exigir que você siga o script palavra por palavra.",
         "a cartoon checklist with icons: a toilet sign with a green check, a script paper with a crossed out exact-words rule", "DIA 5", None, None),
        ("Na Central Fala Já, o Sandro tem outra versão das regras. Ele cronometra o banheiro. Na tela dele, toda ida aparece em vermelho.",
         SUP + ", one operator line marked in red with a toilet icon", "DIA 9", [A(SANDRO, "point", 0.4, facing=1), A(YOU, "sad", 0.66, facing=-1)], None),
        ("E o script é sagrado. Se você trocar bom dia por olá, o Sandro escuta a gravação e te dá zero na monitoria.",
         BAIA + ", a monitor showing a call quality score of zero in red", "DIA 12", [A(SANDRO, "talk", 0.65, facing=-1), A(YOU, "sit", 0.38, facing=1)], None),
        ("Até a pausa tem roteiro. O sistema avisa quando você pode sair, e conta cada segundo que você passa fora. Dez minutos e um segundo já aparecem na tela do Sandro.",
         BREAK + ", the wall clock showing seconds ticking", "DIA 20", [A(YOU, "sit", 0.45)], None),
        ("Você vende quatro planos no primeiro mês. Quatro de trinta. O Sandro te chama para conversar na frente de todo mundo.",
         SUP, "DIA 30", [A(SANDRO, "talk", 0.6, facing=-1), A(YOU, "sad", 0.36, facing=1)], None),
        ("No ônibus de volta, às onze da noite, você faz as contas. Sem esse salário, não tem aluguel. Você está preso na baia quarenta e sete.",
         STREET, "DIA 30", [A(YOU, "sit", 0.45)], None),
    ]),
    ("b03", "Os gritos", ["src1"], [
        ("Com o tempo, você aprende a reconhecer a ligação ruim pelo primeiro segundo. A respiração antes do grito.",
         BAIA, "DIA 48", [A(YOU, "scared", 0.45)], None),
        ("Num dia de chuva, um homem passa quatro minutos te ameaçando. Diz que sabe onde fica a central. Que vai te esperar na porta.",
         BAIA + ", rain on a small window behind", "DIA 55", [A(YOU, "shiver", 0.45)], None),
        ("A norma garante uma pausa imediata depois de ameaça ou agressão verbal. Você levanta a mão e pede.",
         FLOOR, "DIA 55", [A(YOU, "point_up", 0.4), A(SANDRO, "walk", 0.85, to=0.66, beats=[["walk", 1.6, 0.66], ["idle", 99]])], None),
        ("O Sandro olha a fila de espera na tela e responde: pausa agora não dá. Tem quarenta clientes esperando.",
         SUP, "DIA 55", [A(SANDRO, "talk", 0.62, facing=-1), A(YOU, "sad", 0.36, facing=1)], None),
        ("A Dona Neide tira o fone, pega você pelo braço e te leva para a copa. Se ele reclamar, diz que eu passei mal, ela fala.",
         BREAK, "DIA 55", [A(NEIDE, "walk", 0.2, to=0.45), A(YOU, "walk", 0.1, to=0.62, delay=0.3)], None),
        ("Na copa, ela te ensina o que nenhum treinamento ensina. Tem gente que grita porque está com raiva de você. Tem gente que grita porque ninguém mais escuta. Você precisa aprender a separar.",
         BREAK, "DIA 55", [A(NEIDE, "talk", 0.38, facing=1), A(YOU, "sit", 0.62, facing=-1)], None),
        ("Ela também te conta da filha que se formou em enfermagem com o salário dessa mesma baia. Vinte anos de fone no ouvido, ela diz, e nenhum dia igual ao outro.",
         BREAK, "DIA 55", [A(NEIDE, "cheer", 0.38, facing=1), A(YOU, "sit", 0.62, facing=-1)], None),
        ("Você volta para a baia. Mas alguma coisa mudou no jeito como você escuta.",
         BAIA, "DIA 56", [A(YOU, "sit", 0.45)], None),
    ]),
    ("b04", "Ninguém atende", ["src2"], [
        ("O maior inimigo do telemarketing não é o cliente bravo. É o cliente que nem atende.",
         "a phone screen showing an incoming call being declined with a red button, cartoon style", "DIA 80", None, None),
        ("Durante anos, as ligações de telemarketing tiveram que vir de um número começado em zero três zero três. A ideia era o consumidor saber quem estava ligando.",
         "a cartoon phone screen showing an incoming number starting with 0303", "DIA 80", None, None),
        ("Funcionou bem demais. O zero três zero três virou sinônimo de não atende. Em 2025, a Anatel acabou com a obrigação.",
         "a cartoon of many phones rejecting calls from 0303 numbers, crossed out 0303 sign", "DIA 80", None, None),
        ("No lugar, veio a origem verificada: a tela do celular mostra o nome da empresa e o motivo da ligação. Mais transparente. E, para a Central Fala Já, ainda mais fácil de recusar.",
         "a cartoon phone screen showing a verified caller with a company name and the reason for the call, and a thumb pressing decline", "DIA 82", None, None),
        ("O Sandro tem uma solução para isso: mais ligações. O discador agora liga para três números ao mesmo tempo. Quem atender primeiro, cai com você.",
         SUP + ", the wall screen showing a dialer calling three numbers at once", "DIA 90", [A(SANDRO, "cheer", 0.45), A(YOU, "sad", 0.7, facing=-1)], None),
        ("Você tenta explicar para o Sandro que isso irrita as pessoas e queima o nome da empresa. Ele responde que o nome da empresa não paga o seu salário. A meta paga.",
         SUP, "DIA 90", [A(YOU, "talk", 0.36, facing=1), A(SANDRO, "idle", 0.62, facing=-1)], None),
        ("Os outros dois atendem e escutam silêncio. E ligam de volta, irritados, perguntando quem está ligando e desligando na cara deles.",
         BAIA, "DIA 91", [A(YOU, "scared", 0.45)], None),
    ]),
    ("b05", "Seu Joaquim", ["src3"], [
        ("Numa terça qualquer, o discador cai num número fixo. Atende um senhor de voz baixa. Você começa o script, e ele te interrompe com educação.",
         HOME, "DIA 120", [A(JOAQUIM, "talk", 0.5)], None),
        ("Meu filho, eu me cadastrei naquele site, o Não Me Perturbe. Faz meses. Por que vocês continuam ligando?",
         HOME + ", an old landline phone on the table", "DIA 120", [A(JOAQUIM, "sad", 0.45)], None),
        ("Você pesquisa no intervalo. O Não Me Perturbe é um cadastro gratuito, criado em 2019, para bloquear ligações de telemarketing de bancos e operadoras.",
         "a cartoon laptop screen showing a simple website with a big 'NÃO ME PERTURBE' title and a phone with a block sign", "DIA 120", None, None),
        ("Em 2025, a Anatel tornou a participação obrigatória para essas empresas. Depois do pedido, o bloqueio tem que valer em até trinta dias. E quem desrespeita pode ser denunciado.",
         "a cartoon calendar with 30 days circled next to a phone with a block sign and a small official stamp", "DIA 121", None, None),
        ("Você abre a lista do discador. Ela foi comprada há dois anos e nunca foi cruzada com o cadastro. O Seu Joaquim é só um entre milhares.",
         BAIA + ", a monitor showing a very long list of phone numbers with some highlighted in red", "DIA 121", [A(YOU, "scared", 0.45)], None),
        ("Antes de desligar, ele fala uma coisa que fica na sua cabeça: tudo bem, filho. Pelo menos hoje alguém conversou comigo.",
         HOME + ", late afternoon light through the window", "DIA 120", [A(JOAQUIM, "idle", 0.5)], None),
        ("Você mostra a lista para o Sandro. Ele dá de ombros: quem cuida de cadastro é o pessoal da tecnologia. Você cuida de vender.",
         SUP, "DIA 122", [A(YOU, "point", 0.4, facing=1), A(SANDRO, "idle", 0.64, facing=-1)], None),
        ("Daquele dia em diante, uma vez por semana, no seu intervalo, você liga para o Seu Joaquim. Do seu próprio celular. Não para vender nada.",
         BREAK, "DIA 130", [A(YOU, "talk", 0.45)], None),
    ]),
    ("b06", "O jeito errado", ["src1"], [
        ("Conversando com o Seu Joaquim, você percebe uma coisa. Ninguém compra de quem lê um texto. As pessoas compram de quem escuta.",
         BREAK, "DIA 150", [A(YOU, "look_up", 0.45, facing=1)], None),
        ("Então você para de ler o script palavra por palavra. Pergunta da internet que a pessoa tem, de quem usa, do que trava. E só oferece o plano que resolve o problema dela.",
         BAIA, "DIA 155", [A(YOU, "talk", 0.45)], None),
        ("A norma já dizia que ninguém pode exigir o script ao pé da letra. Mas na monitoria do Sandro, você tira zero toda semana.",
         BAIA + ", a monitor showing a row of zero scores", "DIA 160", [A(SANDRO, "point", 0.66, facing=-1), A(YOU, "sit", 0.38, facing=1)], None),
        ("E, ao mesmo tempo, as suas vendas sobem. Doze. Dezenove. Vinte e seis. No quarto mês desse jeito, trinta e quatro.",
         SUP + ", one operator's green bar climbing to the top of the ranking", "DIA 240", [A(YOU, "cheer", 0.45), A(NEIDE, "cheer", 0.7)], None),
        ("O Sandro não sabe se te dá bronca ou bônus. Ele escolhe a bronca. O bônus vem da folha de pagamento, sem ele conseguir impedir.",
         SUP, "DIA 241", [A(SANDRO, "talk", 0.6, facing=-1), A(YOU, "idle", 0.36, facing=1)], None),
        ("A Dona Neide ri baixinho na baia ao lado: vinte anos aqui, e é a primeira vez que eu vejo ele sem palavras.",
         BAIA, "DIA 241", [A(NEIDE, "cheer", 0.62, facing=-1), A(YOU, "sit", 0.38, facing=1)], None),
    ]),
    ("b07", "A auditoria", ["src3"], [
        ("Em outubro, a operadora que contrata a Central Fala Já manda uma auditoria. As denúncias no Não Me Perturbe se acumularam, e alguém precisa explicar.",
         FLOOR + ", two auditors with laptops walking between the rows", "DIA 290", [A("extra", "walk", 0.1, to=0.4, scale=0.95), A(YOU, "sit", 0.7, facing=-1)], None),
        ("Os auditores escutam gravações, cruzam listas, olham a tela do Sandro. E encontram o banheiro em vermelho.",
         SUP + ", the wall screen showing many red toilet icons", "DIA 291", [A(SANDRO, "scared", 0.5)], None),
        ("Eles chamam alguns operadores para conversar, um por um. A Dona Neide entra primeiro. Fica quarenta minutos. Sai com os olhos vermelhos e um sorriso.",
         "a closed meeting room door with a small sign 'AUDITORIA'", "DIA 291", [A(NEIDE, "walk", 0.62, to=0.3)], None),
        ("Depois é a sua vez. Você conta das pausas negadas, da lista nunca cruzada, do discador que liga para três pessoas. E do Seu Joaquim.",
         "a small meeting room with a table and two chairs, a laptop and a coffee cup", "DIA 291", [A(YOU, "talk", 0.36, facing=1), A("extra", "idle", 0.64, facing=-1)], None),
        ("O auditor anota tudo sem levantar os olhos. No fim, ele só pergunta uma coisa: por que você não pediu demissão? Você responde a verdade. Porque eu precisava do salário.",
         "a small meeting room with a table and two chairs, a laptop and a coffee cup", "DIA 291", [A("extra", "talk", 0.64, facing=-1), A(YOU, "sad", 0.36, facing=1)], None),
        ("Na semana seguinte, o discador volta a ligar para um número por vez. A lista passa a ser cruzada com o cadastro. E o Sandro é transferido para outro andar.",
         FLOOR + ", calmer atmosphere, afternoon", "DIA 300", [A(YOU, "sit", 0.36), A(NEIDE, "sit", 0.62)], None),
    ]),
    ("b08", "A última ligação", [], [
        ("Dia trezentos e sessenta e cinco. Você chega na Central Fala Já sabendo que tem uma decisão para tomar.",
         FLOOR + ", early morning, empty cubicles", "DIA 365", [A(YOU, "walk", 0.15, to=0.45)], None),
        ("A coordenação te ofereceu a vaga do Sandro. Supervisor. Salário melhor, mesa própria, e o poder de mudar o andar inteiro.",
         SUP + ", an empty supervisor desk with a small plant", "DIA 365", [A(YOU, "look_up", 0.45, facing=1)], None),
        ("E, no mesmo e-mail, chegou uma resposta de outra empresa, de fora do telemarketing. Horário normal. Sem fone. Sem meta de trinta.",
         "a phone screen showing a job offer email with a calm office picture", "DIA 365", None, None),
        ("A Dona Neide, que se aposenta no mês que vem, só te diz: eu fiquei vinte anos porque precisava. Você pode ficar porque quer, ou ir porque quer. Só não fica por medo.",
         BAIA, "DIA 365", [A(NEIDE, "talk", 0.62, facing=-1), A(YOU, "sit", 0.38, facing=1)], None),
        ("No fim do turno, o seu celular toca. É um número fixo que você conhece de cor. Pela primeira vez em um ano, alguém liga para você.",
         BAIA + ", a personal phone ringing on the desk next to the headset", "DIA 365", [A(YOU, "x", 0.45, beats=[["scared", 1.0], ["talk", 99]])], None),
        ("É o Seu Joaquim. Ele só quer saber se você está bem. E se, no ano que vem, você vai continuar ligando.",
         HOME + ", warm evening light", "DIA 365", [A(JOAQUIM, "talk", 0.5)], None),
        ("Agora me conta nos comentários: você aceitava virar supervisor e mudava a central por dentro, ou tirava o fone e ia embora de vez?",
         STREET + ", a bus arriving with its lights on", "DIA 365", [A(YOU, "x", 0.5, beats=[["look_up", 2.0], ["idle", 99]])], None),
    ]),
]

META = {
    "titles": ["Fiquei Preso 1 Ano Como Operador de Telemarketing",
               "365 Dias na Baia 47: Minha Vida no Telemarketing",
               "1 Ano no Telemarketing: o Supervisor Cronometrava o Banheiro",
               "E Se Você Fosse Quem Te Liga Para Vender Internet?",
               "Trabalhei 1 Ano no Telemarketing e Descobri a Lista Proibida"],
    "chosen_title": "Fiquei Preso 1 Ano Como Operador de Telemarketing",
    "hook_options": ["Seiscentas baias iguais, um fone de ouvido, e uma meta de trinta vendas que ninguém bate.",
                     "Sabe aquela ligação que você recusa sem nem olhar? Durante um ano, do outro lado, era você.",
                     "O supervisor cronometrava o banheiro. A lei dizia outra coisa."],
    "subject": "1 ano preso como operador de telemarketing",
    "tags": ["telemarketing", "operador de telemarketing", "call center", "não me perturbe", "0303", "nr-17",
             "um ano preso", "e se fosse você", "história animada", "vida no telemarketing"],
    "hashtags": ["Telemarketing", "365Dias", "CallCenter"],
    "thumbnail": {
        "phrases": ["365 DIAS", "NA BAIA"],
        "image_prompt": "the survivor, a stick figure with a round white head, small black dot eyes, an orange knit beanie and a green jacket, wearing a call center headset",
        "split": {
            "left_label": "DIA 1", "right_label": "DIA 365",
            "left_prompt": "the survivor, a stick figure with a round white head, small black dot eyes, an orange knit beanie and a green jacket wearing a call center headset, smiling and confident, sitting in a clean bright call center cubicle with a plant",
            "right_prompt": "the survivor, a stick figure with a round white head, small black dot eyes, a messy orange knit beanie and a wrinkled green jacket wearing a tangled headset, exhausted with dark circles under the eyes, sweating, in a dark crowded call center, angry speech bubbles with scribbles coming out of phones all around, a stopwatch on the desk",
        },
    },
}


def blocks():
    out = []
    for bid, title, src, shots in PLANS:
        items = []
        for narr, scene, overlay, actors, fx in shots:
            extra = {}
            if actors:
                extra["actors"] = actors
            if fx:
                extra["fx"] = fx
            items.append((narr, scene, overlay, extra) if extra else (narr, scene, overlay))
        out.append((bid, title, src, items))
    return out


if __name__ == "__main__":
    body = save(__file__, CHANNEL, TITLE, PRIORITY, META, SOURCES, blocks(), min_words=1350, max_words=1800)
    n = sum(1 for b in body["compact"]["blocks"] for s in b["shots"] if len(s) > 3)
    print(f"planos com stickman: {n}")
