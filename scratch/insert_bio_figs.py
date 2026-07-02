# -*- coding: utf-8 -*-
"""Insert the two new biological figures (disease mechanism; structural
consequence of mutations) into the manuscript, add prose, and renumber."""
import re

P = "docs/manuscrito/PrimeVarClass_artigo_honesto.md"
t = open(P, encoding="utf-8").read()

# 1) remap existing figure numbers: current -> new
mapping = {1: 2, 2: 4, 3: 5, 4: 6, 5: 7, 6: 8, 7: 9, 8: 10, 9: 11}
t = re.sub(r"Figuras (\d+) e (\d+)",
           lambda m: f"Figuras {mapping[int(m.group(1))]} e {mapping[int(m.group(2))]}", t)
t = re.sub(r"Figura (\d+)", lambda m: f"Figura {mapping[int(m.group(1))]}", t)

# 2) disease prose + Figure 1 in section 1.1
disease_anchor = "para o sistema de saúde, significa exames que não se convertem em decisão."
disease_block = disease_anchor + """

A base biológica desse problema reside na função de BRCA1 e BRCA2 na manutenção da integridade do genoma. Ambas são essenciais ao reparo de quebras de dupla fita do DNA pela via de **recombinação homóloga (RH)**, de alta fidelidade: BRCA2 controla o carregamento da recombinase RAD51 sobre o DNA de fita simples, enquanto BRCA1, em complexo com BARD1, atua na sinalização e no processamento do dano. Quando uma variante germinativa compromete essa função, a RH torna-se deficiente e a célula recorre a mecanismos de reparo propensos a erro, acumulando mutações e instabilidade genômica — o substrato da transformação maligna. Clinicamente, isso se traduz em risco elevado e precoce de câncer de mama e de ovário, com penetrância cumulativa que pode ultrapassar 70% ao longo da vida, e fundamenta tanto estratégias de redução de risco quanto terapias-alvo (inibidores de PARP). A Figura 1 sintetiza esse mecanismo.

![Figura 1](figuras/fig_disease_mechanism.png)

**Figura 1.** Mecanismo biológico que conecta as proteínas BRCA1/BRCA2 ao câncer hereditário de mama e ovário (HBOC). À esquerda (verde), em uma célula com BRCA1/BRCA2 funcionais, uma quebra de dupla fita no DNA é reparada com fidelidade pela via de recombinação homóloga (RH) — na qual essas proteínas recrutam a recombinase RAD51 —, mantendo a estabilidade genômica e protegendo contra o câncer. À direita (vermelho), uma variante patogênica germinativa (por exemplo, Cys61Gly no domínio RING ou Met1775Arg no domínio BRCT do BRCA1) compromete um domínio funcional crítico, tornando a RH deficiente; o DNA passa a ser reparado por vias propensas a erro, com acúmulo de mutações, instabilidade genômica e, por fim, tumorigênese. A penetrância é elevada (risco cumulativo de câncer de mama de ~45–72% e de ovário de ~11–44% ao longo da vida em portadoras de BRCA1/BRCA2) e a deficiência de RH é explorada terapeuticamente por inibidores de PARP (letalidade sintética). Este é o contexto clínico que torna crítica a classificação precisa das variantes."""
assert disease_anchor in t
t = t.replace(disease_anchor, disease_block, 1)

# 3) morphology prose + Figure 3 in section 2.4 (after the structures caption)
mut_anchor = "As três regiões em destaque são os domínios funcionais críticos usados pelo modelo consciente de domínio."
mut_block = mut_anchor + """

A importância dessas regiões torna-se evidente ao observar o efeito estrutural de variantes patogênicas conhecidas (Figura 3). No domínio RING, cisteínas como Cys61 e Cys64 coordenam um íon de zinco estrutural; substituições como p.Cys61Gly e p.Cys64Gly removem esses ligantes, colapsam o domínio e abolem a atividade de E3-ligase e a interação com BARD1. No domínio BRCT, a variante p.Met1775Arg desestabiliza a interface entre as duas repetições e prejudica o reconhecimento de fosfopeptídeos. Ou seja, as mutações patogênicas danificam precisamente as regiões que o modelo consciente de domínio identifica como críticas — a base biológica que sustenta a abordagem.

![Figura 3](figuras/fig_mutation_consequence.png)

**Figura 3.** Consequência estrutural de variantes patogênicas nos domínios críticos do BRCA1, a partir de estruturas experimentais reais (renderização com PyMOL open-source). **(A)** Sítio de coordenação de zinco no domínio RING (PDB 1JM7): o íon Zn²⁺ (esfera roxa) é mantido por cisteínas, entre elas Cys61 e Cys64 (bastões vermelhos, rotulados). Variantes patogênicas clássicas como p.Cys61Gly e p.Cys64Gly substituem essas cisteínas, abolindo a coordenação do zinco e desestruturando o domínio. **(B)** Domínio BRCT (PDB 1N5O) contendo a variante patogênica p.Met1775Arg: o resíduo 1775 (bastões vermelhos) situa-se na interface entre as duas repetições BRCT, e sua substituição desestabiliza o dobramento e compromete a função. Em ambos os casos, a mutação danifica exatamente a região funcional crítica — a mesma informação de região que o modelo utiliza para generalizar."""
assert mut_anchor in t
t = t.replace(mut_anchor, mut_block, 1)

# 4) update the figure list: add Figura 1 (disease) and Figura 3 (mutation)
t = t.replace("- **Figura 2.** Estruturas 3D experimentais das proteínas-alvo",
              "- **Figura 1.** Mecanismo BRCA1/BRCA2 no reparo do DNA e o câncer hereditário de mama e ovário (HBOC).\n- **Figura 2.** Estruturas 3D experimentais das proteínas-alvo", 1)
t = t.replace("- **Figura 4.** Arquitetura de domínios",
              "- **Figura 3.** Consequência estrutural de variantes patogênicas (sítio de zinco do RING; mutante BRCT M1775R).\n- **Figura 4.** Arquitetura de domínios", 1)

open(P, "w", encoding="utf-8").write(t)
caps = re.findall(r"\*\*Figura (\d+)\.\*\*", t)
print("figure captions in order:", caps)
