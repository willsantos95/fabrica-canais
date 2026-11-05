"""Roteiro e shotlist (formato stickman) escritos pelo Claude para o canal "Um Ano Preso".
História original. Fatos práticos (água do mar, sinal de socorro, escorbuto) vêm das fontes.
Plano = (narração, cenário ou cena, selo, actors | None, fx | None):
- com actors: a IA gera só o cenário vazio e o worker anima os stickmen por cima;
- sem actors: a IA desenha a cena inteira (objetos, paisagens, detalhes).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _compact import save  # noqa: E402

CHANNEL = "um-ano-preso"
TITLE = "Fiquei Preso 1 Ano numa Ilha Deserta (e Não Estava Sozinho)"
PRIORITY = 10

SOURCES = [
    {"id": "src1", "title": "Can humans drink seawater? — NOAA Ocean Service",
     "url": "https://oceanservice.noaa.gov/facts/drinksw.html",
     "claim": "Os rins só produzem urina menos salgada que a água do mar; para eliminar o sal de um gole, o corpo gasta mais água do que bebeu, e a desidratação piora."},
    {"id": "src2", "title": "Emergency Signaling — Be Ready Utah",
     "url": "https://beready.utah.gov/?p=4067",
     "claim": "Três de qualquer coisa em sequência é sinal internacional de socorro; três fogueiras em triângulo, em lugar aberto visível do alto; folhas verdes fazem fumaça grossa de dia; reflexo de espelho é visto a quilômetros."},
    {"id": "src3", "title": "Scurvy — NHS factsheet (AXA Health)",
     "url": "https://axahealth.co.uk/staying-healthy/nhs-factsheets/scurvy",
     "claim": "O escorbuto aparece depois de pelo menos 3 meses sem vitamina C suficiente: cansaço, gengiva inchada e sangrando, dor nas pernas, manchas na pele; frutas e verduras são a principal fonte."},
]

BEACH = "a small tropical island beach with white sand, palm trees and calm turquoise sea"
CAMP = "a castaway camp on a tropical beach: a small palm-leaf shelter, a fire pit with stones and a rain-catching tarp"
JUNGLE = "dense green tropical jungle with big leaves and vines, a narrow dirt path"
ROCKS = "the rocky other side of a tropical island, dark rocks, waves crashing, a cave entrance"
HILL = "the grassy top of a hill on a small tropical island, open sky, the sea all around below"


def A(who, action="idle", x=0.5, **kw):
    return {"who": who, "action": action, "x": x, **kw}


YOU = "you"
ARI = "tomas"  # o velho da ilha usa o visual de barba grisalha

PLANS = [
    ("b01", "O naufrágio", ["src1"], [
        ("A tempestade dura a noite inteira. Quando o mastro quebra, você só tem tempo de agarrar uma mochila e pular.",
         "a small sailboat broken in a huge storm at night, giant waves, lightning, a broken mast", "DIA 0", None, None),
        ("Você acorda com sol no rosto e areia na boca. O barco sumiu. Os outros dois tripulantes também. Na sua frente, uma praia branca, coqueiros, e um silêncio que dá medo.",
         BEACH + ", morning light, a backpack lying on the sand, pieces of wood in the water", "DIA 0",
         [A(YOU, "x", 0.35, beats=[["sleep", 2.0], ["sit", 99]])], None),
        ("Você anda a praia inteira. Em quarenta minutos, está de volta ao mesmo ponto. É uma ilha. Pequena.",
         BEACH + ", wide view, the whole small island visible", "DIA 0", [A(YOU, "walk", 0.1, to=0.8)], None),
        ("Na mochila: um canivete, um isqueiro, uma garrafa vazia, uma lona azul e um espelhinho de barbear.",
         "items laid out on the sand: a pocket knife, a lighter, an empty plastic bottle, a folded blue tarp and a small shaving mirror", "DIA 0", None, None),
        ("Nenhum telefone, nenhuma comida, nenhum rádio. Só você, o que coube numa mochila, e uma ilha que ninguém escolheu.",
         BEACH + ", a lonely backpack on the sand, long shadow", "DIA 0", [A(YOU, "sit", 0.55, facing=-1)], None),
        ("O sol bate forte. Em poucas horas, a sede vira a única coisa em que você consegue pensar.",
         BEACH + ", harsh midday sun, heat waves", "DIA 0", [A(YOU, "sad", 0.45)], None),
        ("E a água está ali, na sua frente. O oceano inteiro. É aqui que muita gente erra.",
         "the edge of the turquoise sea on white sand, gentle waves, endless horizon", "DIA 0", [A(YOU, "look_up", 0.4, facing=1)], None),
        ("A água do mar é muito mais salgada do que o seu corpo aguenta. Os rins só conseguem fazer urina menos salgada que ela. Para jogar fora o sal de um gole, o corpo gasta mais água do que você bebeu.",
         "simple cartoon diagram of a kidney filtering salty seawater, salt crystals, arrows showing water leaving the body", "DIA 0", None, None),
        ("Quem bebe água do mar, seca mais rápido. Você fecha a garrafa vazia e vai procurar outro jeito.",
         BEACH + ", afternoon", "DIA 0", [A(YOU, "walk", 0.6, to=0.2)], None),
    ]),
    ("b02", "Água e fogo", ["src1"], [
        ("Os coqueiros salvam o primeiro dia. Coco verde tem água dentro. Você leva uma hora para abrir o primeiro com o canivete.",
         "a green coconut cut open with a pocket knife on the sand, coconut water inside", "DIA 1", None, None),
        ("Você aprende do jeito difícil que subir num coqueiro é muito mais complicado do que parece nos filmes. Na terceira tentativa, a casca arranha os braços inteiros.",
         BEACH + ", a tall palm tree with coconuts high up", "DIA 1", [A(YOU, "x", 0.45, beats=[["jump", 1.1], ["sad", 99]])], None),
        ("Mas coco não chove do céu todo dia. Então você estica a lona entre duas árvores, com uma ponta mais baixa, e coloca a garrafa embaixo.",
         CAMP + ", a blue tarp tied between two palm trees with a low corner above an empty bottle", "DIA 2",
         [A(YOU, "work", 0.4)], None),
        ("Três dias depois, chove. Você fica parado na chuva, de boca aberta, rindo sozinho. Em meia hora, a garrafa enche. É a melhor água que você já bebeu na vida.",
         CAMP + ", heavy tropical rain, water pouring from the tarp into a bottle", "DIA 5", [A(YOU, "cheer", 0.5)], None),
        ("Depois vem o fogo. O isqueiro é precioso demais para gastar à toa. Você só acende quando junta folha seca, galhinho e paciência.",
         CAMP + ", a small new campfire starting in a ring of stones, evening", "DIA 6", [A(YOU, "work", 0.45)], None),
        ("Fogo é calor, é comida cozida, é luz. E, você descobre logo, também é um jeito de falar com quem está longe.",
         CAMP + ", a strong campfire at night, sparks rising, stars", "DIA 6", [A(YOU, "sit", 0.38, facing=1)], None),
        ("Você monta uma rotina: de manhã, água. Ao meio-dia, sombra. À tarde, comida. À noite, fogo.",
         "a sand calendar with lines scratched in the sand next to a stick, a tropical beach", "DIA 12", None, None),
        ("Peixe pego com lança de bambu, caranguejo, coco. O corpo emagrece, mas segura.",
         "a shallow lagoon with clear water and small fish, a sharpened bamboo spear stuck in the sand", "DIA 20",
         [A(YOU, "point", 0.35, facing=1)], None),
        ("À noite, deitado perto do fogo, você conversa com as estrelas. Primeiro em pensamento. Depois em voz alta. Ninguém responde, mas ajuda a dormir.",
         CAMP + ", night, a small fire and a sky full of stars", "DIA 25", [A(YOU, "sleep", 0.45)], None),
    ]),
    ("b03", "O sinal", ["src2"], [
        ("No dia trinta e um, você ouve um motor. Um avião, alto, cruzando o céu de uma ponta à outra.",
         HILL + ", a tiny airplane far up in the blue sky", "DIA 31", [A(YOU, "x", 0.4, beats=[["look_up", 1.5], ["wave", 99]])], None),
        ("Você grita, pula, balança os braços. Lá de cima, você é um pontinho numa ilha cheia de pontinhos.",
         HILL + ", the airplane getting smaller in the distance", "DIA 31", [A(YOU, "jump", 0.45)], None),
        ("O avião some. E você entende que gritar não adianta. Você precisa de um sinal que alguém lá de cima reconheça na hora, mesmo passando rápido.",
         HILL + ", empty sky, sunset", "DIA 31", [A(YOU, "sad", 0.5)], None),
        ("Existe uma regra conhecida no mundo inteiro: três de qualquer coisa, repetidos, querem dizer socorro. Três apitos. Três flashes. Três fogueiras.",
         "three campfires arranged in a triangle seen from above, on an open grassy hilltop, simple illustration", "DIA 32", None, None),
        ("Você sobe o morro e prepara três montes de lenha em triângulo, num lugar aberto, longe das árvores, onde dá para ver do alto.",
         HILL + ", three piles of firewood arranged in a triangle on the grass", "DIA 33", [A(YOU, "work", 0.3)], None),
        ("De dia, folha verde por cima, para a fumaça sair grossa. E o espelhinho de barbear vira a sua lanterna: reflexo de sol se vê a quilômetros.",
         "a small mirror flashing a bright beam of sunlight toward the sky, thick white smoke rising from green leaves on a fire", "DIA 34", None, None),
        ("Você passa a vigiar o céu e o mar todos os dias. Ninguém vem.",
         HILL + ", calm sea, endless horizon, afternoon", "DIA 45", [A(YOU, "look_up", 0.55, facing=-1)], None),
        ("Um barco de pesca aparece no dia cinquenta e dois. Você acende as fogueiras, mas a lenha está úmida da chuva e a fumaça demora. Quando ela sobe, o barco já é um ponto.",
         HILL + ", a tiny fishing boat far away on the sea, weak grey smoke", "DIA 52", [A(YOU, "run", 0.15, to=0.5, beats=[["run", 1.8, 0.5], ["sad", 99]])], None),
        ("Daquele dia em diante, você guarda lenha seca embaixo da lona, sempre. Erro na ilha não se repete duas vezes.",
         CAMP + ", firewood stacked under a blue tarp", "DIA 53", [A(YOU, "work", 0.5)], None),
    ]),
    ("b04", "As pegadas", [], [
        ("Dia sessenta e oito. A maré baixa mais do que nunca e abre uma passagem pelas pedras até o outro lado da ilha.",
         ROCKS + ", very low tide, a path of wet rocks", "DIA 68", [A(YOU, "walk", 0.15, to=0.5)], None),
        ("E lá, na areia molhada, tem pegadas. Grandes. Recentes. E não são suas.",
         "close-up of fresh human footprints in wet sand leading toward dark rocks", "DIA 68", None, None),
        ("Você congela. Numa ilha deserta, a única coisa mais assustadora do que estar sozinho é descobrir que não está.",
         ROCKS + ", shadows, tense atmosphere", "DIA 68", [A(YOU, "scared", 0.45)], None),
        ("Você segue as pegadas até uma caverna. Na entrada, um varal de peixe seco e um calendário riscado na pedra. Muitos riscos.",
         ROCKS + ", a cave entrance with dried fish hanging on a line and many tally marks carved on the rock", "DIA 68",
         [A(YOU, "walk", 0.2, to=0.42, beats=[["walk", 2.0, 0.42], ["point", 99]])], None),
        ("Uma voz rouca sai lá de dentro: pode sair daí, garoto. Eu te vi chegar faz dois meses.",
         ROCKS + ", the dark cave entrance", "DIA 68",
         [A(YOU, "scared", 0.3, facing=1), A(ARI, "walk", 0.85, to=0.62, beats=[["walk", 2.5, 0.62], ["talk", 99]])], None),
        ("O nome dele é Ari. Pescador. Está na ilha há seis anos. O barco dele afundou na mesma corrente que trouxe você.",
         ROCKS + ", evening, a small fire at the cave entrance", "DIA 68", [A(YOU, "sit", 0.36, facing=1), A(ARI, "talk", 0.62, facing=-1)], None),
        ("Por que ele nunca apareceu? Ari dá de ombros: quis ver se você durava. A maioria não dura.",
         ROCKS + ", night, firelight", "DIA 68", [A(ARI, "idle", 0.6, facing=-1), A(YOU, "sad", 0.36, facing=1)], None),
        ("Naquela noite, você quase não dorme. Fica olhando para o velho do outro lado do fogo, tentando decidir se ele é a sua salvação ou o seu maior problema.",
         ROCKS + ", night, a fire between two sleeping spots", "DIA 68", [A(ARI, "sleep", 0.65, facing=-1), A(YOU, "sit", 0.35, facing=1)], None),
    ]),
    ("b05", "Gengivas", ["src3"], [
        ("Com dois na ilha, a vida melhora. Ari conhece cada pedra, cada maré, cada peixe que dá para comer.",
         "a shallow lagoon at sunrise with fish traps made of sticks", "DIA 80",
         [A(ARI, "work", 0.35), A(YOU, "work", 0.6)], None),
        ("Ele te ensina a fazer armadilha de peixe com galho, a achar ovo de tartaruga sem matar a tartaruga, e a nunca, nunca, nadar quando a maré está virando.",
         "a fish trap made of sticks in shallow clear water, sea turtle tracks on the sand", "DIA 85", None, None),
        ("Mas no terceiro mês, alguma coisa começa a dar errado com você. Um cansaço que não passa com sono.",
         CAMP + ", afternoon", "DIA 95", [A(YOU, "sit", 0.45)], None),
        ("Depois, as pernas doem. A gengiva incha e sangra quando você morde o peixe. Aparecem manchinhas roxas na canela.",
         "simple cartoon close-up of a stick figure leg with small purple spots and a red swollen gum drawing, medical illustration style", "DIA 98", None, None),
        ("Ari olha e já sabe. Escorbuto. Falta de vitamina C. Acontece com quem passa uns três meses sem comer fruta ou verdura.",
         CAMP + ", a fire, evening", "DIA 98", [A(ARI, "talk", 0.36), A(YOU, "sad", 0.62, facing=-1)], None),
        ("Era a doença dos marinheiros antigos. E, numa ilha onde você só come peixe e coco, ela chega devagar e sem barulho.",
         "an old wooden sailing ship on the sea, vintage illustration style, sailors on deck", "DIA 99", None, None),
        ("Ari te leva para o meio do mato, até uma árvore que você nunca tinha visto. Goiabas. Pequenas, verdes, azedas.",
         JUNGLE + ", a guava tree with small green fruits", "DIA 100",
         [A(ARI, "point", 0.6, facing=1), A(YOU, "walk", 0.15, to=0.4)], None),
        ("Ele guardava aquela árvore só para ele. Agora divide. Em duas semanas, a gengiva para de sangrar.",
         JUNGLE + ", a guava tree, sunlight through the leaves", "DIA 114", [A(YOU, "cheer", 0.4), A(ARI, "idle", 0.62, facing=-1)], None),
        ("Você entende uma coisa ali: o Ari não é perigoso. Ele só está acostumado a cuidar de tudo sozinho.",
         JUNGLE + ", late afternoon light", "DIA 115", [A(ARI, "work", 0.4), A(YOU, "idle", 0.62, facing=-1)], None),
    ]),
    ("b06", "A tempestade", [], [
        ("Em outubro, o céu fica verde no fim da tarde. Ari para de falar e começa a amarrar tudo.",
         BEACH + ", strange green stormy sky at dusk, palm trees bending", "DIA 190", [A(ARI, "work", 0.4), A(YOU, "look_up", 0.62)], None),
        ("Vocês levam a lona, a lenha seca e a garrafa para dentro da caverna, e rolam pedra na frente da entrada.",
         ROCKS + ", the cave entrance with heavy wind and rain starting", "DIA 190", [A(YOU, "run", 0.1, to=0.45), A(ARI, "work", 0.6)], None),
        ("A noite inteira, o vento grita. O mar entra até o pé das pedras. Ari reza baixinho. Você nunca tinha ouvido ele rezar.",
         "inside a dark cave lit by a tiny fire, huge waves and storm visible outside the entrance", "DIA 190",
         [A(ARI, "sit", 0.4, facing=1), A(YOU, "scared", 0.6, facing=-1)], None),
        ("De manhã, o acampamento da praia não existe mais. O abrigo, o varal, a lança de bambu, os três montes de lenha no morro. Tudo levado pelo mar. Você senta na areia e fica um tempão sem conseguir falar.",
         BEACH + ", destroyed after a storm, broken palm trees, debris everywhere", "DIA 191", [A(YOU, "sad", 0.45)], None),
        ("Ari ri, cansado: na ilha, nada é seu. Tudo é emprestado. E você começa tudo de novo.",
         BEACH + ", destroyed, morning sun coming out", "DIA 191", [A(ARI, "talk", 0.35), A(YOU, "idle", 0.6, facing=-1)], None),
        ("Três montes de lenha. Folha verde. Espelho. Todo dia, mesmo sem esperança.",
         HILL + ", three new piles of firewood in a triangle", "DIA 200", [A(YOU, "work", 0.3), A(ARI, "work", 0.7)], None),
        ("O Ari sobe o morro todos os dias com você. Carrega lenha, junta folha verde. Mas nunca, nem uma vez, é ele quem acende o fogo.",
         HILL + ", afternoon, piles of firewood", "DIA 220", [A(ARI, "walk", 0.8, to=0.6), A(YOU, "work", 0.3)], None),
    ]),
    ("b07", "O segredo do Ari", [], [
        ("Numa noite de lua cheia, Ari conta por que nunca acendeu fogueira de sinal em seis anos.",
         ROCKS + ", full moon night, a small fire at the cave entrance", "DIA 260", [A(ARI, "talk", 0.4), A(YOU, "sit", 0.62, facing=-1)], None),
        ("No continente, ele tinha uma dívida, uma briga feia, e um irmão que não fala mais com ele. Aqui, ninguém cobra nada.",
         "a symbolic illustration of an old fishing village on the mainland at night, a small boat leaving the harbor", "DIA 260", None, None),
        ("Para ele, a ilha não é prisão. É esconderijo. E cada fogueira que você acende no morro é, para o Ari, uma ameaça de ser encontrado.",
         ROCKS + ", full moon reflected on the sea", "DIA 260", [A(ARI, "sad", 0.45)], None),
        ("Você não sabe o que responder. Só sabe que, do outro lado do mar, alguém ainda deve estar procurando por você.",
         HILL + ", night, the moon over the sea", "DIA 261", [A(YOU, "look_up", 0.5, facing=1)], None),
        ("No dia seguinte, ele age como se a conversa não tivesse acontecido. Pesca, assobia, conserta a armadilha. Você também não toca no assunto.",
         "a shallow lagoon at sunrise with fish traps made of sticks", "DIA 262", [A(ARI, "work", 0.35), A(YOU, "work", 0.65)], None),
        ("Os meses passam. Você conta os dias riscando o mesmo pedaço de pedra que Ari usava. Duzentos e noventa. Trezentos. Trezentos e trinta.",
         "a rock wall full of tally marks, some old and faded, some fresh", "DIA 330", None, None),
    ]),
    ("b08", "Fumaça", ["src2"], [
        ("Dia trezentos e sessenta e cinco. Meio da manhã. Um barulho diferente, baixo e constante. Um navio.",
         HILL + ", a cargo ship far away on the horizon", "DIA 365", [A(YOU, "point", 0.4, facing=1)], None),
        ("Você corre para o morro, joga o isqueiro nos três montes e cobre de folha verde. A fumaça sobe grossa, branca, em três colunas.",
         HILL + ", three columns of thick white smoke rising from fires in a triangle", "DIA 365", [A(YOU, "run", 0.1, to=0.45)], None),
        ("Com o espelho, você manda flashes para o navio. Três. Pausa. Três. Pausa. Três.",
         "a small mirror flashing three beams of sunlight toward a ship on the horizon", "DIA 365", None, None),
        ("O navio diminui a velocidade. Vira devagar. E solta três apitos longos de volta. Alguém viu. Depois de um ano inteiro, alguém finalmente viu.",
         "a cargo ship turning toward a small tropical island, steam from its horn", "DIA 365", None, None),
        ("Você grita e pula como um louco. Depois olha para trás. Ari está parado na beira da mata, sem se mexer.",
         HILL + ", the edge of the jungle behind", "DIA 365", [A(YOU, "jump", 0.4, beats=[["jump", 1.1], ["look_up", 99]]), A(ARI, "idle", 0.8, facing=-1)], None),
        ("Ele diz que não vai. Que alguém precisa cuidar da goiabeira. E pede uma coisa: não contar para ninguém que ele está aqui.",
         JUNGLE + ", the edge of the jungle, morning light", "DIA 365", [A(ARI, "talk", 0.6, facing=-1), A(YOU, "sad", 0.35, facing=1)], None),
        ("O bote do navio já está na água, vindo na sua direção.",
         BEACH + ", a small rescue boat coming from a big ship", "DIA 365", [A(YOU, "wave", 0.45)], None),
        ("Os marinheiros pulam na areia, te enrolam num cobertor e perguntam a primeira coisa que qualquer um perguntaria: você estava sozinho aqui?",
         BEACH + ", a small rescue boat pulled onto the sand", "DIA 365", [A("extra", "talk", 0.62, facing=-1), A(YOU, "idle", 0.38, facing=1)], None),
        ("Agora me conta nos comentários: você guardava o segredo do Ari, ou contava para a tripulação que ainda tem alguém na ilha?",
         BEACH + ", a small rescue boat on the left and the jungle edge on the right", "DIA 365", [A(YOU, "x", 0.5, beats=[["look_up", 2.0], ["idle", 99]])], None),
    ]),
]

META = {
    "titles": ["Fiquei Preso 1 Ano numa Ilha Deserta (e Não Estava Sozinho)",
               "365 Dias numa Ilha Deserta: as Pegadas Não Eram Minhas",
               "1 Ano Preso numa Ilha: Quem Bebe Água do Mar Perde",
               "E Se Você Ficasse 1 Ano numa Ilha Deserta?",
               "Sobrevivi 365 Dias numa Ilha e Descobri um Segredo"],
    "chosen_title": "Fiquei Preso 1 Ano numa Ilha Deserta (e Não Estava Sozinho)",
    "hook_options": ["Você acorda numa praia. O barco sumiu. E no dia sessenta e oito, aparecem pegadas que não são suas.",
                     "O oceano inteiro na sua frente, e você não pode beber uma gota.",
                     "Três fogueiras em triângulo. É assim que se pede socorro de uma ilha."],
    "subject": "1 ano preso numa ilha deserta",
    "tags": ["ilha deserta", "1 ano numa ilha", "sobrevivência", "e se fosse você", "365 dias", "náufrago",
             "história animada", "um ano preso", "sobreviver na ilha", "historia de sobrevivencia"],
    "hashtags": ["IlhaDeserta", "365Dias", "Sobrevivência"],
    "thumbnail": {
        "phrases": ["365 DIAS", "NA ILHA"],
        "image_prompt": "the survivor, a stick figure with a round white head, small black dot eyes, an orange knit beanie and a green jacket, on a small tropical island beach",
        "split": {
            "left_label": "DIA 1", "right_label": "DIA 365",
            "left_prompt": "the survivor, a stick figure with a round white head, small black dot eyes, an orange knit beanie and a green jacket, smiling and waving on a sunny tropical beach with palm trees and turquoise sea, clean and happy",
            "right_prompt": "the survivor, a stick figure with a round white head, small black dot eyes, a torn orange knit beanie and a ragged green jacket, thin and scared, sweating, on a dark stormy island beach at night, broken palm trees, three signal fires burning behind, a mysterious shadowy figure watching from the jungle",
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
