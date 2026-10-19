"""Roteiro e shotlist escritos pelo Claude para o Deu Tudo Errado.
Tema: O dia em que a ponte de Tacoma Narrows dançou até cair (1940)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _compact import save

CHANNEL, TITLE, PRIORITY = "deu-tudo-errado", "O dia em que a ponte de Tacoma Narrows dançou até cair (1940)", 60

SOURCES = [
    {"id": "src1", "title": "Tacoma Narrows Bridge (1940) — Wikipedia",
     "url": "https://en.wikipedia.org/wiki/Tacoma_Narrows_Bridge_(1940)",
     "claim": "Inaugurada em 1/7/1940, vão central de 2.800 pés (853 m), terceira maior ponte pênsil do mundo; Eldridge propôs treliças de 25 pés, Moisseiff vigas de 8 pés, mais baratas; custo de US$ 6,4 milhões; cabos de amarração em blocos de 50 t romperam; amortecedores danificados no jateamento; Farquharson testou modelos 1:200 e 1:20, resultados em 2/11/1940; colapso em 7/11/1940 com ventos de ~40 mph (64 km/h) e movimento de torção; flutter aeroelástico, não ressonância forçada; Coatsworth e o cão Tubby; reembolso de US$ 814,40; filme de Barney Elliott e Harbine Monroe (16 mm Kodachrome, National Film Registry 1998; 16 vs 24 qps); corretor Hallett French e apólice de US$ 800 mil; comissão com Ammann e von Kármán; nova ponte em 14/10/1950 sobre as fundações originais; destroços a 180 pés (55 m), recife artificial no Registro Nacional de Lugares Históricos."},
    {"id": "src2", "title": "Tacoma Narrows Bridge collapses — HistoryLink.org (Essay 5048)",
     "url": "https://historylink.org/File/5048",
     "claim": "Operários chupavam limões contra o enjoo durante a obra; motoristas esperavam o vento 'certo' para 'andar' na ponte; Coatsworth descreve a ponte balançando violentamente; Farquharson estava medindo a ponte, tentou salvar Tubby e foi mordido; Howard Clifford correu da ponte; Tubby foi a única vítima."},
    {"id": "src3", "title": "On this date: The Tacoma Narrows Bridge collapse — ABC27",
     "url": "https://www.abc27.com/history/on-this-date-the-tacoma-narrows-bridge-collapse/amp/",
     "claim": "Ponte caiu cerca de quatro meses depois da inauguração; apelido Galloping Gertie dado pelos operários; ao menos quatro pessoas filmaram, em parte em cores; vão substituído em 1950 e parte do tabuleiro virou recife no fundo do estreito."},
]

ENG = "a 1940s bridge engineer in a gray suit and fedora"
PROF = "the professor, a thin man in his fifties with round glasses, a long coat and a movie camera"
REP = "the newspaper editor, a man in his forties in a 1940s suit and hat"
DOG = "a small black three-legged cocker spaniel"
ST = "cinematic illustrated documentary style, 1940s"

BLOCKS = [
    ("b01", "A ponte que dançava", ["src1", "src3"], [
        ("Imagine dirigir por uma ponte novinha, no estado de Washington, nos Estados Unidos, em 1940. De repente, o carro da frente some numa descida. Depois reaparece, subindo, como se estivesse numa montanha-russa.",
         f"a 1940s car driving on a long suspension bridge whose deck rises and falls like a wave in front of it, {ST}", "WASHINGTON, 1940"),
        ("Não era ilusão de ótica. A ponte inteira subia e descia com o vento. E as pessoas faziam fila para atravessar justamente por causa disso.",
         f"a line of 1940s cars waiting at a toll booth to cross a swaying bridge, families smiling inside, {ST}", None),
        ("Ela tinha até apelido: Galloping Gertie, algo como Gertie, a galopante. Durante quatro meses, foi uma das atrações mais estranhas do país.",
         f"a vintage postcard style illustration of the suspension bridge with the nickname written in elegant letters in the sky, {ST}", "GALLOPING GERTIE"),
        ("Até que, numa manhã de novembro, a dança ficou violenta demais. Na frente de câmeras, de fotógrafos e de um cientista que estava ali justamente para estudá-la, a ponte se torceu como uma fita de papel e despencou no mar.",
         f"the bridge deck twisting violently in the wind, one side up and the other down, gray stormy sky, {ST}", None),
        ("Essa é a história da ponte de Tacoma Narrows. E de como uma ideia para economizar dinheiro virou uma das falhas de engenharia mais famosas de todos os tempos.",
         f"dramatic wide shot of the twisted suspension bridge over a dark strait, cables hanging, {ST}", None),
    ]),
    ("b02", "A ponte mais elegante do mundo", ["src1", "src3"], [
        ("Para entender o que deu errado, a gente precisa voltar um pouco. Tacoma Narrows é um estreito de água no estado de Washington, que separa a cidade de Tacoma da península de Kitsap.",
         f"aerial illustrated map of a narrow strait between a city and a forested peninsula in the Pacific Northwest, {ST}", "TACOMA NARROWS"),
        ("Durante décadas, quem queria atravessar dependia de balsas. Nos anos trinta, a região finalmente conseguiu dinheiro federal para construir uma ponte pênsil gigante.",
         f"an old ferry boat crossing the strait with cars on deck, foggy morning, {ST}", None),
        ("O vão central teria oitocentos e cinquenta e três metros. Na época, só duas pontes pênseis no mundo eram maiores: a Golden Gate, em São Francisco, e a George Washington, em Nova York.",
         f"side by side illustration of three suspension bridges compared by size, the Tacoma one in the center, {ST}", "853 METROS"),
        ("O engenheiro do estado, Clark Eldridge, tinha feito um projeto tradicional. Por baixo da pista, uma treliça de aço com quase oito metros de altura, para deixar a estrutura rígida.",
         f"{ENG} at a drafting table drawing a bridge with a deep steel truss under the roadway, {ST}", "PROJETO 1: TRELIÇA DE 7,6 M"),
        ("Mas aí entrou em cena Leon Moisseiff, um dos engenheiros de pontes mais respeitados de Nova York. Ele propôs algo mais moderno, mais bonito e, principalmente, mais barato.",
         f"a confident older engineer with a mustache in a New York office presenting a sleek bridge drawing, {ST}", "LEON MOISSEIFF"),
        ("No lugar da treliça alta, vigas de aço de apenas dois metros e meio. A pista ficaria fina, elegante, quase uma lâmina flutuando sobre a água. E o preço caía bastante.",
         f"comparison illustration: a thick truss bridge deck next to a very thin plate girder deck, {ST}", "PROJETO 2: VIGA DE 2,4 M"),
        ("O projeto mais barato venceu. A obra começou no fim de 1938 e custou seis milhões e quatrocentos mil dólares. Em pouco mais de um ano e meio, a ponte estava pronta.",
         f"construction workers on the towers of a suspension bridge, steel cables being spun, {ST}", "US$ 6,4 MILHÕES"),
    ]),
    ("b03", "Os operários chupavam limão", ["src1", "src2"], [
        ("Só que, ainda durante a construção, os operários perceberam uma coisa esquisita. Bastava um vento moderado para a pista começar a ondular.",
         f"construction workers holding onto railings as the unfinished bridge deck ripples in the wind, {ST}", None),
        ("O movimento era tão forte que muitos trabalhadores ficavam enjoados, como se estivessem num barco. Para aguentar o turno, eles chupavam limões.",
         f"a construction worker in overalls sucking a lemon on the bridge, looking queasy, {ST}", None),
        ("Foram eles que deram o apelido de Galloping Gertie. E quando a ponte foi inaugurada, no dia primeiro de julho de 1940, o público sentiu na pele a mesma coisa.",
         f"opening day ceremony with flags, a ribbon and a crowd on the bridge, the deck slightly wavy, {ST}", "1º DE JULHO DE 1940"),
        ("Em dias de vento, a pista subia e descia mais de um metro, com ondas que iam e voltavam a cada quatro ou cinco segundos. Quem estava num carro via os veículos à frente sumirem e reaparecerem.",
         f"view from inside a 1940s car on the bridge, the road ahead rising like a hill and falling again, {ST}", None),
        ("E, em vez de medo, isso virou diversão. Moradores esperavam o vento certo e iam até a ponte só para dar uma volta. Era a montanha-russa mais barata da região.",
         f"happy 1940s couples in a convertible laughing as the bridge rises under them, {ST}", None),
        ("Quase todo mundo acreditava que era seguro. Afinal, a ponte tinha sido projetada por especialistas renomados. O balanço seria só uma característica curiosa.",
         f"a smiling official in a hat reassuring a group of reporters with the bridge in the background, {ST}", None),
    ]),
    ("b04", "Tentando acalmar a Gertie", ["src1", "src2"], [
        ("Mas os engenheiros responsáveis não estavam tão tranquilos assim. Começou uma corrida para tentar domar a ponte.",
         f"{ENG} with a worried face looking at the swaying deck through binoculars, {ST}", None),
        ("Primeiro, instalaram cabos de amarração, presos a blocos de concreto de cinquenta toneladas no chão. Pouco depois, os cabos arrebentaram.",
         f"a thick steel cable snapping near a huge concrete block on the shore, sparks and dust, {ST}", "BLOCOS DE 50 T"),
        ("Depois, colocaram cabos inclinados e amortecedores hidráulicos. Os amortecedores não funcionaram, porque as vedações tinham sido danificadas quando a estrutura foi jateada para a pintura.",
         f"close-up of a broken hydraulic damper leaking oil under the bridge deck, {ST}", None),
        ("Então chamaram um especialista: o professor Frederick Burt Farquharson, da Universidade de Washington. Ele construiu modelos da ponte e colocou dentro de um túnel de vento.",
         f"{PROF} in a university lab adjusting a small model of the bridge inside a wind tunnel, {ST}", "PROF. FARQUHARSON"),
        ("Os primeiros resultados saíram no dia dois de novembro de 1940. A sugestão era furar as vigas e instalar defletores aerodinâmicos para o vento passar sem empurrar a pista.",
         f"technical drawings of the bridge with holes drilled in the girders and curved fairings added, {ST}", "2 DE NOVEMBRO"),
        ("Era um bom plano. O problema é que a ponte não ia esperar. Cinco dias depois, ela caiu.",
         f"a calendar on a wall with days crossed off, the bridge visible through a rainy window, {ST}", None),
    ]),
    ("b05", "Sete de novembro", ["src1", "src2"], [
        ("Na manhã de sete de novembro de 1940, ventava forte no estreito, algo em torno de sessenta e quatro quilômetros por hora. Nada extraordinário para a região.",
         f"windy gray morning over the strait, whitecaps on the water, the bridge swaying, {ST}", "7 DE NOVEMBRO DE 1940"),
        ("A ponte começou a ondular como de costume. Mas, pouco antes das dez da manhã, o movimento mudou. Em vez de subir e descer, a pista começou a se torcer.",
         f"the bridge deck starting to twist along its length, the center line still while the edges move, {ST}", None),
        ("Um lado da pista descia enquanto o outro subia. A linha do meio ficava parada, e as bordas giravam em volta dela, cada vez mais.",
         f"illustrated diagram style shot of the deck rotating around its center line, arrows showing opposite motion, {ST}", "TORÇÃO"),
        ("Pouco depois, a passagem seria fechada. Na entrada da ponte, curiosos, policiais e fotógrafos assistiam sem acreditar. Uma estrutura de aço e concreto, com milhares de toneladas, estava se comportando como uma bandeira ao vento.",
         f"a crowd of 1940s onlookers and police officers behind a barrier at the bridge entrance, watching the deck twist, {ST}", None),
        ("Mas, quando o balanço mudou, um carro já estava em cima da ponte. Era o de Leonard Coatsworth, editor do jornal The News Tribune, de Tacoma.",
         f"{REP} gripping the steering wheel of a black 1940s sedan on the tilting bridge, {ST}", "LEONARD COATSWORTH"),
        ("No banco de trás, estava Tubby, um cocker spaniel de três patas que pertencia à filha dele.",
         f"{DOG} sitting on the back seat of a 1940s car, looking out the window nervously, {ST}", "TUBBY"),
        ("Coatsworth contou depois que, assim que passou pelas torres, a ponte começou a balançar violentamente de um lado para o outro. O carro deslizou e ele perdeu o controle.",
         f"the sedan sliding sideways on the steeply tilted bridge deck, {REP} terrified inside, {ST}", None),
        ("Ele saiu do carro, mas não conseguiu levar o cachorro. Com a pista se inclinando cada vez mais, Coatsworth concluiu que a ponte estava se desfazendo e que a única chance era voltar para a margem.",
         f"{REP} crawling on his hands and knees on the tilted concrete roadway, holding onto the curb, {ST}", None),
        ("Ele foi rastejando e cambaleando pela pista, se segurando onde dava, até chegar de volta à cabine de pedágio, na entrada da ponte.",
         f"{REP} reaching the toll booth exhausted, people pulling him to safety, {ST}", None),
    ]),
    ("b06", "A câmera estava ligada", ["src1", "src2", "src3"], [
        ("E aqui entra um detalhe incrível. O professor Farquharson estava na ponte naquela manhã, medindo o movimento. Ele viu o carro abandonado e tentou salvar o Tubby.",
         f"{PROF} walking carefully along the twisting deck toward the abandoned sedan, {ST}", None),
        ("O cachorro, em pânico, mordeu o professor. Ele desistiu e voltou. O fotógrafo Howard Clifford também tentou chegar ao carro, mas precisou correr quando a ponte começou a se partir.",
         f"a photographer in a 1940s coat running away from the camera along the bridge as pieces fall behind him, {ST}", None),
        ("Enquanto isso, dois donos de uma loja de câmeras de Tacoma, Barney Elliott e Harbine Monroe, estavam filmando tudo em cores, num filme de dezesseis milímetros.",
         f"two men in hats operating 16mm movie cameras on tripods at the end of the bridge, {ST}", "FILMADO EM CORES"),
        ("Por volta das onze da manhã, os cabos que seguravam a pista começaram a arrebentar, um atrás do outro. E o vão central caiu de uma vez nas águas do estreito.",
         f"the central span of the bridge breaking apart and plunging into the water, huge splash, {ST}", "11H"),
        ("O carro de Coatsworth caiu junto. Tubby foi a única vítima do desastre. Nenhuma pessoa morreu.",
         f"the black sedan falling with a section of road into the water, seen from a distance, {ST}", "ÚNICA VÍTIMA: TUBBY"),
        ("As imagens rodaram o mundo nos cinejornais. Em 1998, o filme foi incluído no Registro Nacional de Filmes dos Estados Unidos. Até hoje é mostrado em aulas de física e engenharia.",
         f"a 1940s movie theater audience watching newsreel footage of the bridge collapse on the big screen, {ST}", None),
        ("Tem até uma curiosidade técnica: parte da filmagem foi feita a dezesseis quadros por segundo. Quando é exibida a vinte e quatro, a ponte parece se mexer cinquenta por cento mais rápido do que realmente se mexeu.",
         f"close-up of a vintage film strip with frames of the twisting bridge, a projector beam behind it, {ST}", None),
    ]),
    ("b07", "Por que ela caiu", ["src1"], [
        ("Depois do desastre, uma comissão federal com alguns dos maiores engenheiros da época, como Othmar Ammann e Theodore von Kármán, foi investigar.",
         f"a group of 1940s engineers in suits examining the broken bridge towers from a boat, {ST}", "INVESTIGAÇÃO"),
        ("Muita gente aprendeu na escola que a ponte caiu por ressonância, como uma taça de cristal que quebra com uma nota musical. Mas a explicação mais aceita hoje é outra.",
         f"a crystal glass shattering from a sound wave next to a question mark, {ST}", None),
        ("O nome é flutter aeroelástico. A pista fina e flexível, ao se torcer, mudava o jeito como o vento passava por ela. E esse novo fluxo de vento empurrava ainda mais a torção.",
         f"diagram style illustration of wind flowing around a thin twisting deck, swirling vortices growing, {ST}", "FLUTTER AEROELÁSTICO"),
        ("Era um ciclo que se alimentava sozinho. Quanto mais a ponte torcia, mais força o vento fazia. E isso não para enquanto houver vento suficiente.",
         f"a circular arrow diagram drawn over the twisting bridge: twist, wind force, more twist, {ST}", None),
        ("Pontes antigas, com treliças altas, deixavam o vento atravessar a estrutura. A Gertie, com sua pista fina e lisa, funcionava quase como a asa de um avião. Só que uma asa presa nas duas pontas, sem ter para onde ir.",
         f"comparison illustration: wind passing through an open steel truss versus hitting a thin solid deck shaped like a wing, {ST}", None),
        ("No fim das contas, o problema estava naquela escolha de projeto: a pista fina, estreita e flexível demais, que tinha deixado a ponte mais barata e mais elegante.",
         f"the thin bridge girder shown next to the deep truss that had been rejected, {ENG} looking at both, {ST}", None),
        ("O próprio Ammann escreveu depois que a engenharia de pontes não é uma ciência exata, e que estruturas novas trazem problemas que nem a teoria nem a experiência conseguem resolver por completo.",
         f"an old engineer writing a report by lamplight, papers about the bridge on the desk, {ST}", None),
    ]),
    ("b08", "O seguro, o cachorro e o recife", ["src1", "src3"], [
        ("E a história ainda teve um capítulo policial. Um corretor de seguros, Hallett French, tinha vendido uma apólice de oitocentos mil dólares para a ponte, mas nunca repassou o dinheiro para a seguradora.",
         f"a nervous man in a 1940s office stuffing papers into a drawer, insurance documents on the desk, {ST}", "US$ 800 MIL"),
        ("Ao que tudo indica, ele apostou que uma ponte daquele tamanho nunca ia cair. Quando caiu, a fraude veio à tona, e ele foi acusado de furto.",
         f"newspaper headline style illustration about the insurance agent being charged, police officers at his door, {ST}", None),
        ("Coatsworth recebeu oitocentos e catorze dólares e quarenta centavos de indenização: quatrocentos e cinquenta pelo carro e o resto pelo que estava dentro dele.",
         f"{REP} reading a reimbursement check at his desk with a sad smile, a photo of {DOG} on the desk, {ST}", "US$ 814,40"),
        ("A Segunda Guerra atrasou a substituição. A nova ponte só foi inaugurada em outubro de 1950, mais pesada, mais rígida, aproveitando as fundações da antiga.",
         f"a new sturdier suspension bridge with a deep truss deck under a clear sky, 1950s cars crossing, {ST}", "NOVA PONTE: 1950"),
        ("E os restos da Galloping Gertie? Continuam lá embaixo, a cerca de cinquenta e cinco metros de profundidade. Viraram um recife artificial, cheio de vida marinha, e hoje são protegidos como patrimônio histórico.",
         f"underwater view of twisted bridge steel covered with anemones and fish, rays of light from the surface, {ST}", "55 M DE PROFUNDIDADE"),
        ("A ponte de Tacoma Narrows mudou para sempre a engenharia. Desde então, praticamente toda grande ponte é testada em túnel de vento antes de ser construída.",
         f"modern engineers testing a bridge model in a wind tunnel, the old bridge collapse footage on a screen behind them, {ST}", None),
        ("Tudo por causa de uma ponte que dançava, de uma economia que saiu caríssima e de um cachorro de três patas que entrou para a história.",
         f"a memorial-style illustration of {DOG} sitting on a hill overlooking the new bridge at sunset, {ST}", None),
        ("E você, teria atravessado a Galloping Gertie só pela emoção, ou ficaria bem longe dela? Me conta aqui nos comentários.",
         f"the swaying 1940s bridge at sunset with a single car waiting at the entrance, {ST}", "VOCÊ ATRAVESSARIA?"),
    ]),
]

META = {
    "titles": ["A ponte que dançou até cair", "Galloping Gertie: a ponte que se torceu como papel",
               "Economizaram na ponte. Ela caiu em 4 meses", "A ponte que virou montanha-russa (e desabou)",
               "Tacoma Narrows: o desastre filmado em cores", "Por que essa ponte se torceu até quebrar",
               "A ponte, o cachorro de três patas e a fraude do seguro", "O erro de engenharia mais famoso da história",
               "1940: a ponte que balançava com o vento", "A ponte que ensinou o mundo a usar túnel de vento"],
    "chosen_title": "A ponte que dançou até cair",
    "hook_options": ["Em 1940, uma ponte nos Estados Unidos balançava tanto que virou atração turística. Até que caiu.",
                     "Os operários chupavam limão para não enjoar. Era o primeiro aviso.",
                     "Uma ponte se torceu como uma fita de papel. E alguém estava filmando.",
                     "Economizar na espessura da pista parecia uma boa ideia. Custou a ponte inteira.",
                     "A única vítima foi um cachorro de três patas. E a história ainda tem uma fraude."],
    "subject": "Tacoma Narrows Bridge",
    "tags": ["ponte de tacoma", "tacoma narrows", "galloping gertie", "ponte que caiu", "deu tudo errado",
             "desastres de engenharia", "história real", "curiosidades", "flutter aeroelástico", "ressonância ponte"],
    "hashtags": ["DeuTudoErrado", "HistoriaReal", "Engenharia"],
    "thumbnail": {"phrases": ["A PONTE", "DANÇOU"],
                  "image_prompt": "a long suspension bridge twisting dramatically in the wind, one edge up and the other down, on the right two thirds, small 1940s car on the deck, left third dark stormy sky empty for text, high contrast, illustrated"},
}

if __name__ == "__main__":
    save(__file__, CHANNEL, TITLE, PRIORITY, META, SOURCES, BLOCKS, min_words=1500, max_words=2100)
