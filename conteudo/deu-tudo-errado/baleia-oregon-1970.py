"""Roteiro e shotlist escritos pelo Claude para o Deu Tudo Errado.
Tema: O dia em que uma baleia foi explodida numa praia do Oregon (1970)

Cada trecho é (narração, prompt visual em inglês, texto na tela). A narração de cada bloco é a junção
dos trechos, então os narration_span batem palavra por palavra com a narração.
Gera conteudo/deu-tudo-errado/baleia-oregon-1970.json no formato de topics.prepared.
"""
import json
from pathlib import Path

TITLE = "O dia em que uma baleia foi explodida numa praia do Oregon (1970)"

SOURCES = [
    {"id": "src1", "title": "Florence Whale Explosion — The Oregon Encyclopedia",
     "url": "https://oregonencyclopedia.org/articles/florence_whale_explosion/",
     "claim": "Cachalote de 45 pés e 8 toneladas encalhou em 9/11/1970; Oregon State Highway Division usou meia tonelada de dinamite em 12/11; coluna de areia e baleia de 100 pés; sedã esmagado; ninguém ferido; restos enterrados; coluna de Dave Barry em 20/05/1990; 'primeira história a viralizar na internet' (NPR, 2013); em 1979, 41 cachalotes foram enterrados."},
    {"id": "src2", "title": "Exploding whale — Wikipedia",
     "url": "https://en.wikipedia.org/wiki/Exploding_whale",
     "claim": "Detonação às 15h45 de 12/11/1970; George Thornton assumiu porque o chefe estava caçando; vinte caixas de dinamite; veterano sugeriu 20 bananas; pedaços a até 800 pés (cerca de 240 m); Paul Linnman e o cinegrafista Doug Brazil, da KATU; Thornton promovido para Medford; parque batizado em 2020."},
    {"id": "src3", "title": "An Oregon Park Has Been Named After The Infamous Exploding Whale Incident Of 1970 — IFLScience",
     "url": "https://www.iflscience.com/editors-blog/an-oregon-park-has-been-named-after-the-infamous-exploding-whale-incident-of-1970/",
     "claim": "Walt Umenhofer, treinado em explosivos na Segunda Guerra, avisou que a carga estava errada; carro novo comprado na promoção 'whale of a deal' teve o teto amassado; frases 'suco de tomate' de Linnman e 'saiu exatamente certo' de Thornton; votação nomeou o Exploding Whale Memorial Park."},
]

C_ENG = "the highway engineer, a middle-aged man with short gray hair, tan 1970s work jacket and hard hat"
C_REP = "the TV reporter, a young man in a 1970s suit and tie holding a microphone"
C_VET = "the veteran, an older man with a flat cap and a windbreaker, arms crossed"

BLOCKS = [
    ("b01", "O cheiro que ninguém aguentava", ["src1", "src2"], [
        ("Imagine uma praia tranquila no Oregon, em novembro de 1970. Gaivotas, vento frio, ondas cinzentas. E, no meio da areia, uma montanha de carne de quatorze metros que ninguém sabe como tirar dali.",
         "wide shot of a quiet gray Oregon beach in November, cold wind, seagulls, a huge dark sperm whale carcass lying on the sand in the distance", "OREGON, 1970"),
        ("Agora imagine que a solução escolhida pelas autoridades foi explodir essa montanha com meia tonelada de dinamite. Na frente de dezenas de curiosos. E de uma câmera de televisão.",
         "low angle shot of wooden crates of dynamite stacked on the sand next to the enormous whale carcass, curious people watching from far away", None),
        ("Parece piada, mas aconteceu. E o que veio depois daquela explosão virou uma das histórias mais famosas, e mais vergonhosas, da engenharia americana.",
         "dramatic silhouette of the whale carcass against a stormy sky, tense atmosphere, beach dunes on the horizon", None),
        ("Tudo começou no dia nove de novembro de 1970, quando uma cachalote encalhou na praia perto da cidadezinha de Florence, na costa sul do Oregon.",
         "the sperm whale washed ashore at the tide line, small coastal town houses visible on the dunes behind, overcast morning", "9 DE NOVEMBRO"),
        ("Ela tinha cerca de quatorze metros de comprimento e pesava algo em torno de oito toneladas. Viva, uma criatura impressionante. Morta, na areia, um problema que crescia a cada hora.",
         "close-up of the wrinkled gray skin of the dead whale, scale shown by a small human figure standing next to it", "8 TONELADAS"),
        ("Porque uma baleia morta não fica parada esperando. Ela apodrece. E o cheiro de oito toneladas apodrecendo começou a se espalhar pela cidade.",
         "townspeople on a beach path covering their noses with handkerchiefs, faint haze drifting from the carcass", None),
        ("No começo, a baleia virou atração. Gente da região descia até a praia para ver de perto, tirar foto, mostrar para as crianças. Mas a cada dia que passava, a visita ficava mais curta. E o nariz ficava mais tampado.",
         "families in 1970s coats taking photos next to the stranded whale, a child pinching his nose, seagulls nearby", None),
    ]),
    ("b02", "Quem resolve uma baleia?", ["src1", "src2"], [
        ("Os moradores reclamavam do mau cheiro. E havia um medo ainda maior: que curiosos subissem na carcaça, que o corpo estourasse sozinho ou que alguém caísse lá dentro.",
         "children and adults climbing near the whale carcass while a worried official waves them back, wind blowing sand", None),
        ("A responsabilidade ficou com a Divisão de Rodovias do Estado do Oregon. Isso mesmo: o órgão que cuidava de estradas teve que decidir o que fazer com uma baleia.",
         "a 1970s state highway division office, desk with road maps and a rotary phone, a memo about the whale on the desk", "DIVISÃO DE RODOVIAS"),
        ("O chefe do distrito, naquela semana, estava fora, caçando. Então o problema caiu no colo do engenheiro assistente, George Thornton.",
         f"{C_ENG} standing at a desk reading a report with a frown, empty chair of the absent boss beside him", "GEORGE THORNTON"),
        ("Thornton não era biólogo, nem especialista em animais marinhos. Era engenheiro de estradas. E engenheiro de estradas, quando encontra uma pedra enorme no caminho, sabe muito bem o que fazer.",
         f"{C_ENG} looking at a large boulder on a mountain road under construction, workers with drills in the background", None),
        ("Ele decidiu tratar a baleia como se fosse uma rocha. Se uma rocha atrapalha, você explode. Simples assim.",
         f"{C_ENG} standing on the beach facing the whale carcass, hands on hips, determined expression, wide shot", None),
        ("As alternativas não eram nada atraentes. Cortar oito toneladas de carne podre em pedaços, na mão, seria um trabalho lento e nojento. Arrastar aquilo para longe exigiria máquinas que atolariam na areia. A dinamite parecia o caminho rápido e limpo.",
         "workers with long knives and a stuck tractor near the carcass, wheels sunk in the sand, frustrated faces", None),
        ("Para não errar, a equipe consultou especialistas da Marinha dos Estados Unidos e de munições. A conclusão parecia lógica no papel: com explosivo suficiente, a baleia viraria pedacinhos.",
         "a group of men in 1970s uniforms and work clothes leaning over a table with papers and sketches of the whale and blast radius", None),
    ]),
    ("b03", "O plano perfeito no papel", ["src1", "src2", "src3"], [
        ("O plano era o seguinte. A dinamite seria colocada do lado da baleia voltado para a terra, para que a explosão empurrasse os restos em direção ao mar.",
         "top-down diagram-like view of the beach, whale carcass with dynamite placed on the land side, arrows pointing toward the ocean", "O PLANO"),
        ("O que sobrasse ficaria em pedaços pequenos. E aí entrariam os ajudantes da natureza: gaivotas, caranguejos e outros bichos que comem carniça dariam conta do resto.",
         "flock of seagulls circling over the ocean shore, waiting, golden light breaking through clouds", None),
        ("A quantidade escolhida foi de vinte caixas de dinamite. Meia tonelada de explosivo. Mais ou menos quatrocentos e cinquenta quilos.",
         "workers in hard hats carrying wooden dynamite crates across the sand toward the whale, one after another", "20 CAIXAS"),
        ("Antes da detonação, Thornton deu entrevista. Confiante, ele admitiu uma coisa curiosa: a equipe não tinha certeza de quanto explosivo seria preciso para desintegrar aquilo.",
         f"{C_ENG} talking to {C_REP.split(', ', 1)[1]} on the beach, the whale carcass behind them", None),
        ("Ou seja, ninguém sabia direito. Mas a decisão estava tomada, a dinamite estava na areia e a cidade inteira queria ver.",
         "crowd of townspeople gathering on the dunes with binoculars and cameras, cars parked in a lot behind them", None),
        ("E aqui está o detalhe que faltou na conta. Uma rocha é dura e se parte em pedaços. Uma baleia é carne, gordura e água. Ela não se comporta como pedra. E explosivo empurra tudo para o lado onde encontra menos resistência.",
         "split image concept: on the left a rock cracking into stones, on the right the soft bulky whale carcass on wet sand", None),
        ("Quem fazia aquilo pela primeira vez não tinha como prever. E, na prática, era exatamente isso: uma equipe de estradas fazendo, pela primeira vez, algo que quase ninguém no mundo tinha feito.",
         f"{C_ENG} kneeling beside the dynamite crates, checking wires, sweat on his forehead despite the cold wind", None),
    ]),
    ("b04", "O aviso que ninguém ouviu", ["src2", "src3"], [
        ("No meio dos curiosos havia um homem chamado Walt Umenhofer. Empresário da região, ele tinha aprendido a lidar com explosivos durante a Segunda Guerra Mundial.",
         f"{C_VET} standing among the crowd on the dunes, studying the dynamite crates with a skeptical look", "WALT UMENHOFER"),
        ("Ele olhou para aquilo e percebeu que a conta não fechava. Foi até os responsáveis e avisou que a quantidade estava errada.",
         f"{C_VET} walking up to {C_ENG}, pointing at the dynamite crates, serious conversation", None),
        ("Na opinião dele, o certo seriam vinte bananas de dinamite, não vinte caixas. Ou então muito, muito mais explosivo, para sumir de vez com a carcaça. O meio-termo era o pior dos mundos.",
         "close-up comparison: a single stick of dynamite in a hand versus a full wooden crate packed with dozens of sticks", "20 BANANAS"),
        ("O aviso foi ignorado. Umenhofer se afastou para assistir de longe. E há um detalhe que torna tudo ainda melhor: poucos dias antes, ele tinha comprado um carro novinho.",
         f"{C_VET} walking away toward a parking lot where a shiny new 1970s sedan is parked", None),
        ("A concessionária fazia uma promoção chamada, em inglês, de uma oferta do tamanho de uma baleia. Ele estacionou o carro novo ali perto. Guarde essa informação.",
         "a shiny new 1970s sedan with a dealership tag parked near the dunes, the whale far in the background, ominous sky", None),
        ("Pense na cena. Um senhor que já tinha visto explosivo de verdade, na guerra, tentando explicar para uma equipe de estradas que aquilo ia dar errado. E a equipe seguindo em frente, porque o plano tinha sido aprovado.",
         f"{C_VET} looking back over his shoulder at the workers wiring the dynamite, shaking his head slowly", None),
        ("Também estavam lá o repórter Paul Linnman e o cinegrafista Doug Brazil, da emissora KATU, de Portland. Eles tinham ido gravar uma matéria curiosa. Iam gravar história.",
         f"{C_REP} standing next to a cameraman with a large 1970s 16mm film camera on a tripod, pointed at the whale", "KATU, PORTLAND"),
    ]),
    ("b05", "Chuva de baleia", ["src1", "src2", "src3"], [
        ("Doze de novembro de 1970, três e quarenta e cinco da tarde. O público foi afastado para cerca de quatrocentos metros. A contagem regressiva começou.",
         "wide shot of the crowd standing far back on the dunes, everyone looking toward the distant whale, tense silence", "12 DE NOVEMBRO, 15H45"),
        ("E então a praia explodiu. Um jornal local descreveu a cena como uma coluna de areia e baleia com uns trinta metros de altura.",
         "massive explosion on the beach, a tall column of sand and dark red debris shooting into the sky, shockwave rippling the sand", None),
        ("O repórter da TV comparou com os filmes. Nas explosões de cinema, disse ele, a gente vê fogo e fumaça. Aquela parecia mais um jato gigante de suco de tomate.",
         "slow-motion like view of reddish debris spraying through the air above the beach, crowd in the foreground looking up in shock", None),
        ("E aí veio o problema que ninguém tinha calculado: tudo o que sobe, desce. Pedaços de gordura de baleia começaram a cair do céu sobre a multidão.",
         "people running and covering their heads as chunks of blubber fall from the sky onto the dunes and the parking lot", "TUDO O QUE SOBE..."),
        ("Alguns pedaços voaram até uns duzentos e quarenta metros. Caíram perto de prédios, em cima de carros no estacionamento, no meio das pessoas que corriam.",
         "aerial view of the beach and parking lot with debris scattered across cars and rooftops, people scattering", "240 METROS"),
        ("Um pedaço enorme acertou em cheio um carro estacionado. Adivinhe de quem. O teto do carro novo de Walt Umenhofer afundou com o impacto.",
         "a huge chunk of blubber crushing the roof of the shiny new sedan in the parking lot, glass cracked", None),
        ("Vendo um funcionário tirar a gordura do carro com uma pá, ele soltou a frase que resume aquele dia: a seguradora nunca vai acreditar nisso.",
         f"{C_VET} standing next to his crushed car while a worker scoops blubber off the roof with a shovel, deadpan expression", None),
        ("Quem estava lá lembra do cheiro, do barulho dos pedaços batendo no chão e da correria. A plateia que tinha ido ver um espetáculo virou alvo do espetáculo.",
         "spectators wiping their coats and hair, some laughing nervously, others disgusted, blubber stains on the sand", None),
        ("O mais incrível de tudo: ninguém ficou ferido. Mas a baleia continuava ali. Grande parte da carcaça nem tinha se mexido.",
         "the beach after the blast, a large crater and most of the whale carcass still lying there, seagulls keeping their distance", None),
    ]),
    ("b06", "Saiu exatamente certo", ["src1", "src2", "src3"], [
        ("E as gaivotas, que iam fazer a limpeza? Assustadas com o estrondo, elas sumiram. Ninguém quis chegar perto do que sobrou.",
         "empty sky over the beach, a few distant seagulls flying away from the shore, quiet aftermath", None),
        ("A equipe da Divisão de Rodovias teve que voltar ao trabalho do jeito antigo. Os restos e os pedaços espalhados foram recolhidos e enterrados na areia.",
         "highway workers with shovels and a small bulldozer burying the remains of the whale in the sand, overcast afternoon", None),
        ("O cinegrafista da KATU tinha registrado tudo. A matéria foi ao ar, e o repórter fechou com uma ironia: se um dia outra baleia aparecer por ali, os responsáveis vão saber exatamente o que não fazer.",
         f"{C_REP} speaking to the camera on the beach with the burial work behind him, slight smirk", None),
        ("E George Thornton? Depois da explosão, ele disse a um jornal que tudo tinha saído exatamente certo. Segundo ele, o problema foi a cratera que se formou embaixo da baleia, que mandou os pedaços na direção do público.",
         f"{C_ENG} giving an interview to newspaper reporters with notepads, gesturing calmly as if everything were fine", "\"EXATAMENTE CERTO\""),
        ("Anos depois, ele ainda defendia a operação. Para Thornton, aquilo tinha sido um sucesso, transformado em desastre de imagem por uma imprensa que queria rir dele.",
         f"older version of {C_ENG}, now retired, sitting in an armchair with old newspaper clippings on a coffee table", None),
        ("E a carreira dele não sofreu. Pouco tempo depois, Thornton foi promovido para o escritório de Medford, onde trabalhou até se aposentar.",
         "a small 1970s state office building in a sunny Oregon town, nameplate on an office door, quiet ordinary day", "MEDFORD"),
        ("Dá para entender os dois lados. Thornton recebeu um problema que não era da área dele, consultou especialistas e seguiu o que eles disseram. Mas também ignorou o único aviso que veio de alguém com experiência prática bem ali, na areia.",
         f"split composition: {C_ENG} on one side studying papers, {C_VET} on the other side shaking his head", None),
        ("E é aí que mora a lição desse dia. A teoria dizia uma coisa. A pessoa que já tinha mexido com explosivo de verdade dizia outra. E a praia de Florence mostrou, em poucos segundos, quem estava certo.",
         "the crater on the beach with scattered debris, footprints of the crowd running away, late afternoon light", None),
    ]),
    ("b07", "A primeira história viral", ["src1", "src2", "src3"], [
        ("O Oregon aprendeu a lição. Em 1979, quarenta e uma cachalotes encalharam e morreram numa praia ao sul de Florence. Dessa vez, ninguém falou em dinamite. Elas foram enterradas.",
         "a long beach with many stranded sperm whales at dusk, workers and machines beginning to dig, somber mood", "1979: 41 BALEIAS"),
        ("Hoje, a regra no estado é essa: baleia encalhada é enterrada na areia. Simples, silencioso e sem chuva de gordura.",
         "calm beach at sunset with a smooth mound of sand where a whale was buried, gentle waves", None),
        ("Mas a história não morreu em 1970. Vinte anos depois, em maio de 1990, o colunista Dave Barry escreveu sobre a baleia explosiva, contando que tinha o vídeo e assistia sempre.",
         "a newspaper column on a 1990 breakfast table next to a cup of coffee, a VHS tape labeled with a whale drawing beside it", "1990"),
        ("Uma versão do texto foi parar nos primeiros fóruns da internet. E começou a circular como se fosse notícia fresca. O órgão de transportes do Oregon passou a receber ligações de gente indignada com uma explosão de vinte anos antes.",
         "early 1990s computer screen with a green text bulletin board, a phone ringing on a cluttered office desk beside it", None),
        ("Um porta-voz do órgão chegou a dizer que aquela foi a primeira história a viralizar na internet. Muito antes dos vídeos de gatinhos.",
         "montage of glowing old computer monitors in different homes, all showing the same blurry beach explosion video", "1º VIRAL DA INTERNET"),
        ("Em 2020, os moradores de Florence votaram o nome de uma nova área de lazer da cidade. Concorriam nomes tranquilos, de parque de bairro. O vencedor foi Parque Memorial da Baleia Explosiva.",
         "a small town park with a wooden sign shaped like a whale, families walking, playful mood, sunny day", "2020"),
        ("O vídeo daquela tarde continua circulando até hoje e a história virou o exemplo clássico de plano que funciona no papel e explode na prática. E a cidade, em vez de esconder, abraçou a fama. Florence transformou o dia mais constrangedor da sua história em parte da própria identidade.",
         "a lecture hall with students watching the old explosion footage on a projector screen, some laughing", None),
        ("No fim, uma baleia que ninguém sabia como tirar da praia virou monumento. E a frase que mais combina com esse dia é a do próprio engenheiro: saiu exatamente certo.",
         "the whale-shaped park sign at golden hour with the ocean in the background, seagulls flying peacefully", None),
        ("E você, conhece alguma solução que parecia genial no papel e deu tudo errado na prática? Conta aqui nos comentários.",
         "the empty Oregon beach at dusk, gentle waves, a single seagull standing where the whale once was", None),
    ]),
]

MOVES = ["push_in", "pan_right", "pull_out", "pan_left", "push_in", "pan_up", "pan_down"]


def build():
    blocks, sl_blocks, k = [], [], 0
    for bid, title, srcs, spans in BLOCKS:
        narration = " ".join(s for s, _, _ in spans)
        blocks.append({"block_id": bid, "title": title, "narration": narration, "source_ids": srcs})
        shots = []
        for i, (span, prompt, overlay) in enumerate(spans):
            shots.append({"narration_span": span, "visual_prompt": prompt, "text_overlay": overlay,
                          "kenburns": MOVES[k % len(MOVES)], "is_hook": bid == "b01" and i < 2})
            k += 1
        sl_blocks.append({"block_id": bid, "shots": shots})
    words = sum(len(b["narration"].split()) for b in blocks)
    script = {
        "titles": [
            "Explodiram uma baleia na praia (e choveu gordura)",
            "A baleia explodida do Oregon: o plano que deu errado",
            "O dia em que choveu baleia numa cidade dos EUA",
            "Meia tonelada de dinamite contra uma baleia morta",
            "Explodir uma baleia: a pior ideia de 1970",
            "Por que nunca se deve explodir uma baleia",
            "Baleia explosiva: a primeira história viral da internet",
            "Engenheiros explodiram uma baleia. Não saiu como planejado",
            "O carro novo, a baleia e a dinamite",
            "Florence, 1970: a explosão que virou parque",
        ],
        "chosen_title": "Explodiram uma baleia na praia (e choveu gordura)",
        "hook_options": [
            "Em 1970, engenheiros do Oregon tiveram uma ideia para sumir com uma baleia morta: dinamite.",
            "Meia tonelada de dinamite, uma baleia de oito toneladas e uma câmera ligada. O que podia dar errado?",
            "Essa é a história do dia em que choveu baleia numa praia dos Estados Unidos.",
            "Um homem avisou que a conta estava errada. Ninguém ouviu. E o carro novo dele pagou o preço.",
            "Antes dos vídeos de gatinhos, o primeiro viral da internet foi uma baleia explodindo.",
        ],
        "sources": SOURCES,
        "blocks": blocks,
        "subject": "baleia explodida",
        "tags": ["baleia explodida", "baleia explosiva oregon", "exploding whale", "Florence Oregon 1970", "deu tudo errado",
                 "histórias bizarras", "curiosidades", "história real", "engenharia que deu errado", "primeiro viral da internet"],
        "hashtags": ["DeuTudoErrado", "HistoriaReal", "Curiosidades"],
    }
    shotlist = {"blocks": sl_blocks, "thumbnail": {
        "phrases": ["EXPLODIRAM", "UMA BALEIA"],
        "image_prompt": "huge explosion of sand and red debris on a beach with a sperm whale silhouette, shocked crowd small in the foreground, subject on the right third, left half dark sky empty for text, high contrast"}}
    return {"script": script, "shotlist": shotlist}, words, k


if __name__ == "__main__":
    prepared, words, shots = build()
    out = Path(__file__).with_suffix(".json")
    out.write_text(json.dumps({"channel_slug": "deu-tudo-errado", "title": TITLE, "priority": 50, "author": "claude",
                               "prepared": prepared}, ensure_ascii=False, indent=1), "utf-8")
    print(f"{words} palavras, {len(prepared['script']['blocks'])} blocos, {shots} planos -> {out}")
