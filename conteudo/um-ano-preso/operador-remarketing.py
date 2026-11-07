"""Roteiro e shotlist (formato stickman) escritos pelo Claude para o canal "Um Ano Preso".
História original e fictícia (empresa, pessoas e casos inventados). Fatos sobre remarketing,
abandono de carrinho e cookies vêm das fontes.
Plano = (narração, cenário ou cena, selo, actors | None, fx | None)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _compact import save  # noqa: E402

CHANNEL = "um-ano-preso"
TITLE = "Fiquei Preso 1 Ano Como Operador de Remarketing"
PRIORITY = 10

SOURCES = [
    {"id": "src1", "title": "Shopping cart abandonment rate statistics — Contentsquare (dados do Baymard Institute)",
     "url": "https://contentsquare.com/blog/shopping-cart-abandonment-rate-statistics/",
     "claim": "A taxa média de abandono de carrinho no comércio online fica perto de 70%, média de dezenas de estudos reunidos pelo Baymard Institute."},
    {"id": "src2", "title": "Membership duration — Google Authorized Buyers Help",
     "url": "https://support.google.com/adxbuyer/answer/166268?hl=en",
     "claim": "A duração de participação numa lista de remarketing é quanto tempo o cookie do visitante fica na lista depois que ele para de visitar o site: padrão de 30 dias, máximo de 540 dias."},
    {"id": "src3", "title": "ANPD publica guia orientativo sobre o uso de cookies — Lefosse (2022)",
     "url": "https://lefosse.com/noticias/alerta/anpd-publica-guia-orientativo-sobre-o-uso-de-cookies/",
     "claim": "Para cookies de publicidade, o consentimento é a base mais adequada; cookies não necessários devem vir desativados por padrão, e o banner deve permitir rejeitá-los, sem apenas um botão de aceitar tudo."},
]

OFFICE = "a windowless basement office with rows of computer monitors showing ad dashboards and graphs, fluorescent ceiling lights"
DESK = "a cluttered office desk with two big monitors showing ad campaign dashboards, sticky notes and an old coffee mug"
BOSS = "a small glass-walled manager office with a big desk, a framed chart on the wall and a city view poster"
WARROOM = "a dark basement office at night lit only by many glowing monitors, pizza boxes and energy drink cans on the desks"
STREET = "a city sidewalk at sunset outside a modern office building with glass doors"
LIVING = "a cozy living room with a sofa and a laptop open on a coffee table"

YOU, VERA, CAIO = "you", "extra", "bento"  # Vera usa o visual de terno cinza; Caio, o de óculos


def A(who, action="idle", x=0.5, **kw):
    return {"who": who, "action": action, "x": x, **kw}


PLANS = [
    ("b01", "A vaga", [], [
        ("Oito meses desempregado. Então chega o e-mail: vaga de operador de remarketing, salário bom, começo imediato. Você nem lê o contrato direito.",
         "a phone screen showing a job offer email with a big green 'HIRED' stamp, cartoon style", "DIA 0", None, None),
        ("Primeiro dia. A empresa se chama LojaJá. Prédio bonito, recepção de vidro, cafezinho de graça. Você sorri para tudo.",
         "a shiny modern office lobby with glass walls, plants and a reception desk", "DIA 1", [A(YOU, "walk", 0.15, to=0.5)], None),
        ("Aí o elevador desce. E desce. Subsolo dois. Uma sala sem janela, cheia de telas. Na porta, uma plaquinha: Sala do Pixel.",
         OFFICE + ", a door with a small sign 'SALA DO PIXEL'", "DIA 1", [A(YOU, "look_up", 0.4, facing=1)], None),
        ("Quem te recebe é a Vera, gerente de performance. Terno cinza, voz baixa, e um sorriso que não chega nos olhos.",
         OFFICE, "DIA 1", [A(VERA, "talk", 0.62, facing=-1), A(YOU, "idle", 0.35, facing=1)], None),
        ("Ela aponta a cláusula sete do seu contrato: doze meses de permanência. Quem sair antes paga três salários de multa.",
         "a contract page on a desk with clause 7 highlighted in yellow and a pen, cartoon style", "DIA 1", None, None),
        ("Você engole seco. Três salários você não tem. A Vera sorri: bem-vindo. Aqui ninguém escapa. Nem você, nem o cliente.",
         OFFICE, "DIA 1", [A(VERA, "point", 0.6, facing=-1), A(YOU, "scared", 0.36, facing=1)], None),
        ("Você assina a última página do manual de conduta e ganha um crachá com a sua foto. Embaixo do nome, em letra pequena: acesso restrito ao subsolo.",
         "an employee badge with a stick figure photo and small text 'ACESSO: SUBSOLO 2', cartoon style", "DIA 1", None, None),
        ("Na mesa ao lado, o Caio, que está lá há dois anos, levanta a caneca de café e diz baixinho: corre enquanto dá. Você acha que é piada.",
         DESK, "DIA 1", [A(CAIO, "talk", 0.62, facing=-1), A(YOU, "idle", 0.36, facing=1)], None),
    ]),
    ("b02", "O pixel", ["src1"], [
        ("O Caio te explica o trabalho. Toda vez que alguém entra no site da LojaJá, um código minúsculo, o pixel, marca o navegador da pessoa.",
         "simple cartoon diagram of a web browser with a tiny glowing pixel attaching a small tag to a shopper icon", "DIA 2", None, None),
        ("A pessoa olha um tênis, coloca no carrinho, e vai embora sem pagar. Isso acontece o tempo todo. Em média, de cada dez carrinhos, uns sete são abandonados.",
         "a cartoon chart: ten shopping carts, seven of them abandoned and grey, three green with a check mark", "DIA 2", None, None),
        ("O seu trabalho é ir atrás dessas sete pessoas. Mostrar o tênis no celular, na rede social, no site de notícias, no vídeo de receita. Até elas voltarem.",
         DESK + ", the screen showing the same sneaker ad on many different websites", "DIA 3", [A(YOU, "work", 0.4)], None),
        ("Na primeira semana, você até gosta. Monta campanha, ajusta público, vê as vendas voltando em tempo real. Cada compra recuperada faz um plim no painel. Parece um jogo, e você está ganhando.",
         DESK + ", a rising green sales graph on the monitor", "DIA 7", [A(YOU, "cheer", 0.45)], None),
        ("O Caio te mostra o painel com o número que manda em tudo: carrinho recuperado. Se esse número cai, a Vera desce.",
         OFFICE + ", a giant screen on the wall with a big number labeled 'CARRINHOS RECUPERADOS'", "DIA 10", [A(CAIO, "point", 0.35, facing=1), A(YOU, "look_up", 0.6, facing=1)], None),
        ("Você aprende os truques. Quem olhou e não comprou ganha desconto de cinco por cento. Quem voltou duas vezes, frete grátis. Quem desistiu no pagamento, um alerta de últimas unidades.",
         DESK + ", the screen showing three ad versions with discount, free shipping and 'last units' banners", "DIA 12", [A(YOU, "work", 0.4), A(CAIO, "point", 0.66, facing=-1)], None),
        ("E você descobre rápido que a Vera desce todo dia.",
         OFFICE + ", the elevator door opening", "DIA 14", [A(VERA, "walk", 0.85, to=0.6, beats=[["walk", 1.8, 0.6], ["point", 99]]), A(YOU, "scared", 0.3, facing=1)], None),
    ]),
    ("b03", "Quinhentos e quarenta dias", ["src2"], [
        ("No segundo mês, a Vera chama você na sala dela. Os números estão bons, mas ela quer mais.",
         BOSS, "DIA 45", [A(VERA, "talk", 0.6, facing=-1), A(YOU, "idle", 0.35, facing=1)], None),
        ("Primeira ordem: a lista de quem visitou o site guarda as pessoas por trinta dias. Ela quer o máximo que a ferramenta permite. Quinhentos e quarenta dias.",
         "a settings screen with a slider labeled membership duration being pushed from 30 days to 540 days, cartoon style", "DIA 45", None, None),
        ("Ou seja: alguém que olhou uma air fryer hoje vai ver a mesma air fryer daqui a um ano e meio.",
         "a cartoon calendar flipping many pages while the same air fryer ad keeps appearing", "DIA 45", None, None),
        ("Segunda ordem: sem limite de frequência. Se der para mostrar o anúncio vinte vezes no mesmo dia para a mesma pessoa, mostra.",
         BOSS, "DIA 45", [A(VERA, "cheer", 0.6, facing=-1), A(YOU, "sad", 0.35, facing=1)], None),
        ("Você tenta argumentar que gente irritada não compra. A Vera responde sem levantar os olhos: irritada, mas lembrando da gente.",
         BOSS, "DIA 46", [A(YOU, "talk", 0.35, facing=1), A(VERA, "idle", 0.62, facing=-1)], None),
        ("Em três semanas, a LojaJá vira piada na internet. Montagem do tênis aparecendo na geladeira, no espelho do banheiro, na sopa.",
         "funny cartoon collage of the same sneaker ad appearing on a fridge, a bathroom mirror and in a soup bowl", "DIA 66", None, None),
        ("Você começa a reconhecer os clientes pelos códigos. O usuário quatro, cinco, sete, que olha a mesma geladeira toda madrugada. A usuária da mala de viagem, que nunca viaja.",
         OFFICE + ", a list of anonymous user codes on a monitor with small icons of a fridge and a suitcase", "DIA 70", [A(YOU, "work", 0.45)], None),
        ("O Caio lê os comentários em voz alta, rindo de nervoso. Você não ri. Você é o cara que aperta o botão.",
         DESK, "DIA 67", [A(CAIO, "talk", 0.38), A(YOU, "sad", 0.64, facing=-1)], None),
    ]),
    ("b04", "O anel", [], [
        ("No quinto mês, chega um e-mail diferente. Não é reclamação de preço. É de um cliente chamado Rafael.",
         DESK + ", a long email open on the screen", "DIA 140", [A(YOU, "work", 0.42)], None),
        ("Rafael tinha olhado um anel de noivado no site. Colocou no carrinho, pensou no preço, desistiu de pagar naquela noite.",
         "a small engagement ring in a shopping cart icon on a laptop screen at night", "DIA 140", None, None),
        ("Só que o computador da casa é dividido com a namorada. E durante duas semanas, o anel apareceu para ela. No jornal, no vídeo, na receita de bolo.",
         LIVING + ", the laptop showing a big engagement ring ad", "DIA 140", [A("nina", "look_up", 0.42, facing=1)], None),
        ("O pedido que ele planejava há meses virou uma pergunta no café da manhã: Rafael, que anel é esse?",
         LIVING + ", morning light", "DIA 140", [A("nina", "point", 0.36, facing=1), A("extra", "scared", 0.64, facing=-1, scale=0.95)], None),
        ("No fim do e-mail, uma frase: eu sei que tem uma pessoa aí dentro apertando esses botões. Você dormiu bem?",
         "close-up of the last line of an email on a dark screen, cursor blinking", "DIA 140", None, None),
        ("O e-mail não vai para o jurídico. Não vai para a Vera. Ele cai direto na caixa de entrada da Sala do Pixel, porque o atendimento não sabe para onde mandar.",
         OFFICE + ", a lonely monitor glowing with an unread email notification", "DIA 140", [A(YOU, "sad", 0.45)], None),
        ("Você não dorme bem. Nem naquela noite, nem na seguinte.",
         "a dark bedroom at night, a phone glowing on the nightstand", "DIA 141", [A(YOU, "sit", 0.5)], None),
    ]),
    ("b05", "O banner", ["src3"], [
        ("Tentando entender onde tudo deu errado, você abre o site da LojaJá como se fosse um cliente. E repara no aviso de cookies.",
         DESK + ", a website with a cookie banner at the bottom of the screen", "DIA 150", [A(YOU, "point", 0.42, facing=1)], None),
        ("Ele tem um botão só: aceitar tudo. Nada de recusar. E, lá dentro, a caixinha de publicidade já vem marcada.",
         "close-up cartoon of a cookie consent banner with one giant 'ACEITAR TUDO' button and pre-ticked checkboxes", "DIA 150", None, None),
        ("Você pesquisa. A autoridade de proteção de dados do Brasil, a ANPD, publicou um guia sobre isso. Para cookie de publicidade, o caminho é pedir consentimento de verdade.",
         "a cartoon government guide booklet about cookies and personal data next to a magnifying glass", "DIA 151", None, None),
        ("Cookie que não é necessário tem que vir desligado. E o aviso tem que deixar a pessoa recusar, não só aceitar.",
         "a cartoon cookie banner done right: switches turned off by default and two equal buttons, accept and reject", "DIA 151", None, None),
        ("Ou seja: boa parte da lista de quinhentos e quarenta dias pode ter sido montada com gente que nunca disse sim de verdade.",
         OFFICE + ", a huge list of user icons on the big wall screen", "DIA 151", [A(YOU, "scared", 0.45)], None),
        ("Você passa a noite lendo o guia inteiro no celular, embaixo do cobertor, como se fosse um livro de suspense. Em cada página, um botão que você mesmo apertou.",
         "a dark bedroom at night, a phone glowing under a blanket", "DIA 151", [A(YOU, "sit", 0.5)], None),
        ("Você leva o print para a Vera. Ela olha três segundos e devolve: o jurídico cuida disso. Volta para o seu número.",
         BOSS, "DIA 152", [A(YOU, "talk", 0.36, facing=1), A(VERA, "idle", 0.62, facing=-1)], None),
        ("O Caio te puxa no corredor: o jurídico nunca viu esse banner. Fui eu que fiz, dois anos atrás, porque ela mandou.",
         "a narrow office corridor with a vending machine", "DIA 152", [A(CAIO, "talk", 0.42), A(YOU, "scared", 0.64, facing=-1)], None),
    ]),
    ("b06", "Black Friday", [], [
        ("Novembro chega, e com ele a Black Friday. A Vera instala um colchão na Sala do Pixel. Ninguém sai até domingo.",
         WARROOM + ", an air mattress on the floor in the corner", "DIA 200", [A(VERA, "point", 0.5)], None),
        ("Meia-noite de quinta. O site recebe tanta gente que as campanhas começam a gastar sozinhas, a cada segundo, sem ninguém olhando.",
         WARROOM + ", money counter numbers spinning on the screens", "DIA 201", [A(YOU, "work", 0.36), A(CAIO, "work", 0.64)], None),
        ("Três da manhã, a Vera dorme sentada na cadeira dela. O Caio olha para você. Vocês dois pensam a mesma coisa.",
         WARROOM + ", very late at night", "DIA 201", [A(VERA, "sleep", 0.75, facing=-1), A(CAIO, "idle", 0.42, facing=1), A(YOU, "idle", 0.25, facing=1)], None),
        ("Você sabe que, se der errado, a multa da cláusula sete vai ser o menor dos seus problemas. O Caio sabe também. Ele só fala: se for pra cair, a gente cai fazendo o certo.",
         WARROOM + ", two chairs side by side in front of the screens", "DIA 201", [A(CAIO, "talk", 0.4, facing=1), A(YOU, "idle", 0.6, facing=-1)], None),
        ("O Caio troca o banner: botão de recusar do mesmo tamanho do de aceitar, publicidade desmarcada. Você coloca limite de três anúncios por dia por pessoa e volta a lista para trinta dias.",
         WARROOM, "DIA 201", [A(CAIO, "work", 0.36), A(YOU, "work", 0.62)], None),
        ("Vinte minutos de trabalho. Você aperta salvar com a mão tremendo.",
         "close-up cartoon of a finger pressing a big SAVE button on a keyboard, dramatic lighting", "DIA 201", None, None),
        ("De manhã, a Vera acorda e olha o painel. As reclamações nas redes caíram. As vendas também. Um pouco.",
         WARROOM + ", morning, the big wall screen showing one line going down and a complaints counter dropping", "DIA 201", [A(VERA, "look_up", 0.5, facing=1)], None),
        ("Ela não sabe o motivo. Ainda. Você passa o resto do fim de semana sem conseguir olhar para ela, esperando o momento em que alguém vai abrir o histórico de alterações.",
         WARROOM + ", morning", "DIA 201", [A(VERA, "idle", 0.5, facing=-1)], None),
    ]),
    ("b07", "A sala da Vera", [], [
        ("Em dezembro, chega um relatório do diretor da LojaJá, que nunca tinha descido ao subsolo. As vendas caíram pouco. Mas as compras de quem voltou ao site cresceram, e quase ninguém mais pediu reembolso.",
         "a printed report on a desk with two charts: a small dip and a growing line, cartoon style", "DIA 230", None, None),
        ("No mesmo dia, a Vera te chama na sala dela e fecha a porta. Ela já sabe de tudo.",
         BOSS, "DIA 230", [A(VERA, "talk", 0.62, facing=-1), A(YOU, "scared", 0.35, facing=1)], None),
        ("Ela lembra da cláusula sete. Fala em justa causa. Em processo. Em multa.",
         BOSS, "DIA 230", [A(VERA, "point", 0.6, facing=-1), A(YOU, "sad", 0.36, facing=1)], None),
        ("Aí a porta abre. É o Caio, com o relatório do diretor na mão e um e-mail impresso: o Rafael ficou noivo. E escreveu de novo, agradecendo por terem parado de seguir ele.",
         BOSS, "DIA 230", [A(CAIO, "walk", 0.95, to=0.78, beats=[["walk", 1.6, 0.78], ["talk", 99]]), A(VERA, "idle", 0.55, facing=1), A(YOU, "look_up", 0.3, facing=1)], None),
        ("O diretor quer saber quem mudou a estratégia. A Vera olha para você, para o Caio, e de novo para você. Ela poderia mentir. Você vê ela pensando nisso.",
         BOSS, "DIA 230", [A(VERA, "idle", 0.55, facing=-1), A(YOU, "scared", 0.3, facing=1), A(CAIO, "idle", 0.78, facing=-1)], None),
        ("A Vera fica em silêncio por muito tempo. Depois só diz: voltem para as mesas.",
         BOSS, "DIA 230", [A(VERA, "sad", 0.55)], None),
        ("Nos meses seguintes, ninguém fala do assunto. Mas o banner continua do jeito novo. E a lista continua em trinta dias.",
         OFFICE + ", calm afternoon", "DIA 300", [A(YOU, "work", 0.36), A(CAIO, "work", 0.64)], None),
    ]),
    ("b08", "Dia trezentos e sessenta e cinco", [], [
        ("Dia trezentos e sessenta e cinco. O contrato acabou. A cláusula sete não vale mais nada. Você pode sair pela porta e nunca mais voltar.",
         OFFICE + ", a calendar on the wall with the last day circled", "DIA 365", [A(YOU, "look_up", 0.45, facing=1)], None),
        ("Antes de você pegar a mochila, a Vera aparece na porta. Pela primeira vez, ela sorri de verdade.",
         OFFICE, "DIA 365", [A(VERA, "walk", 0.9, to=0.66, beats=[["walk", 1.6, 0.66], ["idle", 99]]), A(YOU, "idle", 0.38, facing=1)], None),
        ("Ela oferece a vaga dela. Vai ser promovida para outro setor. Quer você como novo gerente de performance. Salário dobrado. Contrato de mais doze meses.",
         OFFICE, "DIA 365", [A(VERA, "talk", 0.62, facing=-1), A(YOU, "scared", 0.38, facing=1)], None),
        ("O Caio, lá do fundo, levanta a caneca de café e diz baixinho a mesma frase do primeiro dia: corre enquanto dá.",
         DESK, "DIA 365", [A(CAIO, "talk", 0.6, facing=-1), A(YOU, "look_up", 0.36, facing=1)], None),
        ("Você olha em volta. As mesmas telas, o mesmo colchão no canto, a mesma lâmpada piscando há onze meses. Mas a sala não parece mais tão escura.",
         OFFICE + ", a deflated air mattress in the corner, one flickering ceiling light", "DIA 365", [A(YOU, "look_up", 0.5, facing=1)], None),
        ("Você sobe o elevador para pensar. Na calçada, o celular vibra. É um anúncio. Uma mochila que você olhou ontem, te seguindo.",
         STREET, "DIA 365", [A(YOU, "x", 0.45, beats=[["walk", 1.8, 0.45], ["look_up", 99]])], None),
        ("Você ri sozinho no meio da calçada. Agora você sabe exatamente quem está do outro lado daquele anúncio. Alguém num subsolo, olhando um número, decidindo se você vale mais um plim.",
         STREET + ", golden light", "DIA 365", [A(YOU, "cheer", 0.5)], None),
        ("Agora me conta nos comentários: você aceitava a promoção e mudava a Sala do Pixel por dentro, ou saía correndo enquanto dá?",
         STREET + ", the glass doors of the building behind", "DIA 365", [A(YOU, "x", 0.5, beats=[["look_up", 2.0], ["idle", 99]])], None),
    ]),
]

META = {
    "titles": ["Fiquei Preso 1 Ano Como Operador de Remarketing",
               "1 Ano Preso na Sala do Pixel: Eu Era o Anúncio Que Te Persegue",
               "365 Dias Seguindo Pessoas na Internet (Era Meu Trabalho)",
               "E Se Você Fosse Quem Faz o Anúncio Te Seguir?",
               "Trabalhei 1 Ano Fazendo Anúncios Te Perseguirem"],
    "chosen_title": "Fiquei Preso 1 Ano Como Operador de Remarketing",
    "hook_options": ["Doze meses de contrato, três salários de multa, e uma sala sem janela chamada Sala do Pixel.",
                     "Sabe aquele anúncio que te persegue? Durante um ano, quem apertava o botão era você.",
                     "De cada dez carrinhos, sete são abandonados. O seu trabalho era ir atrás deles."],
    "subject": "1 ano preso como operador de remarketing",
    "tags": ["remarketing", "operador de remarketing", "anúncio que persegue", "cookies", "lgpd", "um ano preso",
             "e se fosse você", "história animada", "marketing digital", "black friday"],
    "hashtags": ["Remarketing", "365Dias", "MarketingDigital"],
    "thumbnail": {
        "phrases": ["365 DIAS", "NO PIXEL"],
        "image_prompt": "the survivor, a stick figure with a round white head, small black dot eyes, an orange knit beanie and a green jacket, in an office full of computer screens",
        "split": {
            "left_label": "DIA 1", "right_label": "DIA 365",
            "left_prompt": "the survivor, a stick figure with a round white head, small black dot eyes, an orange knit beanie and a green jacket with an employee badge, smiling and giving a thumbs up in a bright clean modern office with plants and a big window",
            "right_prompt": "the survivor, a stick figure with a round white head, small black dot eyes, a messy orange knit beanie and a wrinkled green jacket, exhausted with dark circles under the eyes, sweating, in a dark windowless basement surrounded by dozens of glowing screens full of the same sneaker ad, empty coffee cups everywhere",
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
