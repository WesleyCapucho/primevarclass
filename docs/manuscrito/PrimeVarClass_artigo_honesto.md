# PrimeVarClass: da hipótese dos números primos a um classificador de variantes BRCA1/BRCA2 consciente de domínio e validado externamente

*Manuscrito para o 32º Prêmio Jovem Cientista — Categoria Estudante do Ensino Superior. Tema: Inteligência Artificial para o Bem Comum (linha IA & Saúde). Rascunho honesto v1 — fonte em Markdown; versão final em ABNT/DOCX derivada deste arquivo.*

---

## Resumo

A interpretação de variantes de significado incerto (VUS) em genes de predisposição ao câncer de mama e ovário, como *BRCA1* e *BRCA2*, é um gargalo clínico e de pesquisa: milhares de mutações *missense* permanecem sem classificação, o que limita o aconselhamento genético e o acesso equitativo à medicina de precisão no Brasil. Este trabalho apresenta o **PrimeVarClass**, um sistema de inteligência artificial explicável para priorização dessas variantes, desenvolvido sob um princípio central: **rigor metodológico e honestidade científica como fonte de valor**. Partimos de uma hipótese original — codificar aminoácidos como números primos para capturar padrões de patogenicidade — e a submetemos a um teste controlado com dados reais do ClinVar, painéis de especialistas e gnomAD. A hipótese foi **refutada de forma transparente**: características derivadas de primos tiveram desempenho inferior (AUC 0,742) ao de uma simples identidade de aminoácidos (AUC 0,902) e *reduziram* o desempenho ao serem adicionadas a um modelo bioquímico (0,834 → 0,810; DeLong p < 0,0001). No processo, diagnosticamos uma **armadilha de vazamento posicional**: a posição do resíduo memoriza os dados de treino (AUC interna 0,885) mas colapsa em coortes externas. A partir desse diagnóstico, construímos um classificador **consciente de domínio funcional**, que substitui a posição bruta por características de *região* anotadas a partir do UniProt (domínios RING/BRCT de BRCA1 e o domínio de ligação ao DNA de BRCA2). Esse modelo **generaliza para coortes externas independentes** com AUC de **0,847**, superando tanto a linha de base bioquímica (0,717) quanto o modelo que usa posição bruta (0,791; DeLong p = 1,8 × 10⁻¹³) — evidência de que capturamos biologia transferível, não memorização. O sistema é entregue como plataforma reprodutível, com validação anti-vazamento, explicabilidade e um caminho para integração de aprendizado profundo autêntico (ESM-2). A contribuição principal não é uma alegação inflada de desempenho, mas um **método honesto, auditável e generalizável** para apoiar a pesquisa genética responsável no país.

**Palavras-chave:** classificação de variantes; BRCA1; BRCA2; aprendizado de máquina; validação externa; vazamento de dados; domínios proteicos; IA explicável; saúde de precisão.

## Abstract

Interpreting variants of uncertain significance (VUS) in cancer-predisposition genes such as *BRCA1* and *BRCA2* is a clinical and research bottleneck. We present **PrimeVarClass**, an explainable AI system for prioritising *missense* variants, built on a principle of methodological rigour and scientific honesty. We began with an original hypothesis — encoding amino acids as prime numbers — and tested it on real ClinVar/expert-panel/gnomAD data. The hypothesis was **transparently refuted**: prime-derived features underperformed a plain amino-acid identity model (AUC 0.742 vs 0.902) and *lowered* accuracy when added to a biochemical model (0.834 → 0.810; DeLong p < 0.0001). We diagnosed a **positional-leakage trap** whereby the raw residue index memorises the training set (internal AUC 0.885) but collapses externally. We then built a **domain-aware** classifier that replaces raw position with UniProt functional-region features (BRCA1 RING/BRCT, BRCA2 DNA-binding domain). It **generalises to independent external cohorts** at AUC **0.847**, beating both the biochemical baseline (0.717) and the raw-position model (0.791; DeLong p = 1.8 × 10⁻¹³), indicating transferable biology rather than memorisation. The main contribution is an honest, auditable, generalisable method to support responsible genetic research.

**Keywords:** variant classification; BRCA1; BRCA2; machine learning; external validation; data leakage; protein domains; explainable AI; precision health.

---

## 1. Introdução

### 1.1 O problema clínico e social

Mutações germinativas em *BRCA1* e *BRCA2* aumentam substancialmente o risco de câncer de mama e de ovário. A identificação de portadores permite estratégias de redução de risco, rastreamento intensificado e decisões terapêuticas informadas. Contudo, uma fração expressiva das variantes encontradas em testes genéticos é classificada como **variante de significado incerto (VUS)** — não se sabe se são patogênicas ou benignas. Para o paciente e a família, uma VUS significa ansiedade e ausência de conduta clínica clara; para o sistema de saúde, significa exames que não se convertem em decisão.

No Brasil, esse problema é agravado por desigualdade de acesso: a interpretação de variantes depende de expertise concentrada em poucos centros, e laboratórios públicos e universitários frequentemente carecem de ferramentas abertas, auditáveis e adaptadas à realidade nacional. Uma inteligência artificial que **acelere e organize** a interpretação de variantes — sem substituir o julgamento humano — tem potencial de impacto direto na formação de pesquisadores e no apoio à medicina de precisão pública.

### 1.2 A lacuna metodológica

Preditores computacionais de patogenicidade existem (REVEL, CADD, AlphaMissense, entre outros), mas muitos benchmarks sofrem de dois problemas recorrentes: **(i) vazamento de dados**, quando o modelo aprende atalhos que não se sustentam fora do conjunto de treino, e **(ii) falta de validação externa independente**, superestimando o desempenho real. Um sistema competitivo e cientificamente sólido precisa demonstrar não o melhor número em um teste interno, mas **generalização honesta** para dados nunca vistos.

### 1.3 A jornada científica deste trabalho

Este projeto nasceu de uma hipótese original e arrojada: e se a estrutura dos **números primos** — objetos matemáticos com propriedades de distribuição não triviais — pudesse codificar aminoácidos de forma a revelar padrões de patogenicidade? A ideia dá nome ao sistema (*PrimeVarClass*). Em vez de tratá-la como verdade a ser defendida, nós a tratamos como **hipótese a ser testada**. Este manuscrito relata honestamente esse teste, seu **resultado negativo**, o **diagnóstico** que ele possibilitou, e a **solução generalizável** que dele emergiu. Sustentamos que essa trajetória — hipótese ousada, teste rigoroso, refutação transparente e modelo validado — é, em si, a contribuição científica mais valiosa e mais alinhada ao espírito da ciência.

### 1.4 Objetivos

1. Testar de forma controlada se a codificação por números primos melhora a classificação de variantes *missense* em *BRCA1/BRCA2*.
2. Investigar e quantificar o efeito de vazamento posicional em benchmarks internos.
3. Desenvolver e **validar externamente** um classificador consciente de domínio funcional que generalize para coortes independentes.
4. Entregar o sistema de forma reprodutível, explicável e eticamente responsável, com aplicação concreta ao contexto brasileiro de saúde e pesquisa.

---

## 2. Materiais e Métodos

### 2.1 Fontes de dados (reais e públicas)

Utilizamos exclusivamente dados públicos e auditáveis de variantes *missense* de *BRCA1* (UniProt P38398) e *BRCA2* (UniProt P51587):

- **ClinVar** — classificações clínicas, com subconjunto de alta confiança revisado por painel de especialistas (ENIGMA/ClinGen).
- **gnomAD** — frequências alélicas populacionais.
- **Coortes externas independentes** — variantes classificadas por especialistas de BRCA1 e BRCA2, mantidas estritamente separadas do conjunto de treino para validação de generalização.

Rótulos foram normalizados em patogênico (1) vs benigno (0); classificações conflitantes ou de baixa confiança foram excluídas. Conjunto de treino: **n = 869**; conjunto externo: **n = 836**.

### 2.2 Representações de variante (características)

Cada substituição de aminoácido foi representada por famílias de características:

- **Bioquímicas**: variações de massa, hidrofobicidade, carga, polaridade, aromaticidade, mudança de classe química e escore de severidade bioquímica.
- **Hipótese dos primos**: aminoácidos mapeados a números primos, com derivações (razões, diferenças, densidade local, lacunas entre primos, resíduos módulo, etc.).
- **Identidade**: codificação categórica direta (gene, aminoácido de referência, aminoácido alternativo).
- **Domínio funcional** (proposta deste trabalho): rótulo categórico do domínio UniProt e indicador binário de domínio crítico (ver 2.4).
- **Preditores externos** (apenas como referência): quando disponíveis.

### 2.3 O teste da hipótese dos primos

Para avaliar a hipótese de forma justa, comparamos, sob **o mesmo classificador e o mesmo protocolo de validação**, conjuntos de características isolados: apenas-primos, apenas-bioquímico, apenas-identidade, e combinações (híbrido). A pergunta central foi operacionalizada em comparações pareadas: *os primos superam a identidade simples?* e *adicionar primos a um modelo bioquímico ajuda?*

### 2.4 Anotação de domínio funcional (UniProt)

Mapeamos cada posição de resíduo aos domínios funcionais curados das proteínas:

- **BRCA1 (P38398)**: domínio RING (1–109; ligação a BARD1, E3-ligase) e as repetições BRCT (1642–1736 e 1756–1855) como regiões **críticas**; domínios SCD e *coiled-coil* de ligação a PALB2 como não críticos.
- **BRCA2 (P51587)**: domínio de ligação ao DNA (DBD: helicoidal 2481–2667 e três folhas OB até 3186) como região **crítica**; repetições BRC de ligação a RAD51 e demais regiões como não críticas.

Definimos duas características: `functional_domain` (categórica) e `in_critical_domain` (binária). O ponto essencial é que essas características são funções de **região**, não do índice único do resíduo — portanto codificam biologia transferível em vez de memorizar quais posições exatas foram patogênicas no treino.

### 2.5 Protocolo de validação anti-vazamento

Adotamos dois níveis de avaliação:

- **(A) Validação cruzada bloqueada por posição** (StratifiedGroupKFold, 5 *folds*), em que todas as variantes de uma mesma posição ficam no mesmo *fold*. Isso impede que o modelo "veja" a mesma posição no treino e no teste, neutralizando o vazamento posicional.
- **(B) Generalização externa**: treino no conjunto interno completo e teste em coortes externas independentes de especialistas.

Comparações de AUC entre modelos foram feitas com o **teste pareado de DeLong**. A métrica primária foi a AUC-ROC.

### 2.6 Modelo e implementação

Classificador *Random Forest* balanceado, com codificação apropriada por tipo de característica, em *pipeline* reprodutível (semente fixa). O sistema é implementado em Python, com testes automatizados (cobertura das características de domínio e de ingestão de escores), e disponibilizado como pacote auditável. A anotação de domínio é um módulo independente e citável (`domain_annotation.py`), e a ingestão de escores de aprendizado profundo (ESM-2) é desacoplada do treino (`esm_scores.py`), sem dependência obrigatória de GPU.

---

## 3. Resultados

### 3.1 A hipótese dos números primos foi refutada

Sob validação bloqueada por posição, com o mesmo classificador, as características derivadas de primos tiveram desempenho **inferior** ao de uma codificação de identidade trivial, e **pioraram** um modelo bioquímico ao serem adicionadas.

**Tabela 1. Desempenho por conjunto de características (AUC-ROC, validação *out-of-fold*).**

| Conjunto de características | nº de *features* | AUC |
| --- | ---: | ---: |
| Identidade (gene + aa_ref + aa_alt) | 4 | **0,902** |
| Bioquímico | 28 | 0,834 |
| Híbrido + preditores externos | 87 | 0,832 |
| Híbrido (bioquímico + primos) | 76 | 0,810 |
| **Apenas primos** | 50 | 0,742 |
| Apenas preditores externos (só gnomAD AF) | 5 | 0,616 |

**Tabela 2. Comparações pareadas (DeLong).**

| Comparação | AUC A | AUC B | Δ | p |
| --- | ---: | ---: | ---: | ---: |
| Apenas-primos vs identidade | 0,742 | 0,902 | −0,161 | < 0,0001 |
| Híbrido vs apenas-bioquímico | 0,810 | 0,834 | −0,025 | < 0,0001 |

A conclusão é inequívoca e honesta: **os números primos não agregam sinal preditivo** para esta tarefa; onde parecem contribuir, é por características bioquímicas correlacionadas, e sua adição introduz ruído que reduz o desempenho.

### 3.2 Diagnóstico: a armadilha do vazamento posicional

Investigando por que certos modelos internos pareciam fortes, identificamos que a **posição bruta do resíduo** atinge AUC interna de ~0,885 — mas por **memorização**: como muitas posições aparecem com o mesmo rótulo no treino e no teste em validações ingênuas, o modelo "decora" posições em vez de aprender biologia. Sem a posição, a identidade gene+aa_ref+aa_alt cai para 0,783, e o gene isolado para 0,640. Este é um alerta metodológico central: **benchmarks internos que não bloqueiam a posição superestimam o desempenho real.**

### 3.3 A solução: modelo consciente de domínio, validado externamente

Substituindo a posição bruta por características de **região funcional**, obtivemos um modelo que não só resiste ao bloqueio por posição como **generaliza melhor** para coortes externas independentes.

Sanidade biológica: a taxa de patogenicidade dentro de domínios críticos é de **45%**, contra **9%** fora deles — coerente com o papel funcional dessas regiões.

**Tabela 3. Consciência de domínio: validação bloqueada por posição e generalização externa (AUC-ROC).**

| Modelo | CV bloqueada por posição | Coortes externas |
| --- | ---: | ---: |
| Bioquímico (sem posição) | 0,743 | 0,717 |
| **Bioquímico + domínio (proposto)** | **0,818** | **0,847** |
| Bioquímico + posição bruta (referência de vazamento) | 0,802 | 0,791 |

DeLong (domínio vs bioquímico): p = 3,2 × 10⁻⁹ (interno) e **p = 1,8 × 10⁻¹³** (externo). Decisivamente, o modelo de domínio (0,847) **supera** o de posição bruta (0,791) *justamente nas coortes externas* — ou seja, o sinal de região **transfere-se** para dados novos, enquanto a posição **memoriza** e falha ao generalizar. Este é o resultado central do trabalho.

### 3.4 Integração de aprendizado profundo autêntico (ESM-2)

Como camada ortogonal e cientificamente legítima, integramos o modelo de linguagem de proteínas **ESM-2** (Lin et al., 2023; Meier et al., 2021), que pontua substituições de forma *zero-shot* pela razão de verossimilhança logarítmica com o resíduo mascarado — um sinal profundo que não depende de rótulos nem vaza de outros preditores. A infraestrutura de ingestão desses escores está pronta e testada; a avaliação quantitativa do modelo *domínio + ESM-2* em dados reais é a etapa em andamento. *(Resultados a inserir após a execução do ESM-2.)*

---

## 4. Discussão

*(A desenvolver — pontos-chave já definidos.)*

- **Biologia transferível vs memorização.** A superioridade externa do modelo de domínio sobre a posição bruta é a evidência mais forte de que o sistema aprende mecanismo funcional, não atalho estatístico.
- **A honestidade como contribuição.** Reportar a refutação dos primos e o diagnóstico de vazamento fortalece — não enfraquece — o trabalho: é ciência reprodutível e à prova de auditoria.
- **Posicionamento frente a preditores estabelecidos.** Discutir uso de AlphaMissense/REVEL como *referência* e não como *feature* (para evitar circularidade), e o valor de um método aberto e auditável.
- **Limitações.** Duas proteínas; fronteiras de domínio aproximadas; ausência de confirmação funcional experimental; escores ESM-2 em integração.

## 5. Impacto social e aplicação

*(A desenvolver.)* Conexão com o SUS e a desigualdade de acesso à interpretação genética; apoio a laboratórios públicos/universitários; formação de pesquisadores; plataforma web/API auditável; explicitamente **não** um diagnóstico clínico automático, mas uma ferramenta de aceleração de pesquisa responsável.

## 6. Ética e uso de inteligência artificial

*(A desenvolver.)* Declaração explícita de uso de IA no desenvolvimento; governança de dados públicos; limites, vieses e necessidade de validação experimental independente; ausência de qualquer dado fabricado.

## 7. Conclusão

*(A desenvolver.)* Uma hipótese ousada, testada e refutada com transparência, conduziu a um classificador consciente de domínio que generaliza externamente — um método honesto e reprodutível para apoiar a saúde de precisão no Brasil.

---

## Referências

*(A consolidar em formato ABNT.)*

1. UniProt Consortium. UniProt: the Universal Protein Knowledgebase. *Nucleic Acids Res.* 2023. (P38398; P51587).
2. Landrum M.J. et al. ClinVar. *Nucleic Acids Res.* 2018.
3. Karczewski K.J. et al. The mutational constraint spectrum quantified from variation in 141,456 humans (gnomAD). *Nature* 2020.
4. Meier J. et al. Language models enable zero-shot prediction of the effects of mutations on protein function. *NeurIPS* 2021.
5. Lin Z. et al. Evolutionary-scale prediction of atomic-level protein structure with a language model (ESM-2). *Science* 2023.
6. DeLong E.R. et al. Comparing the areas under two or more correlated ROC curves. *Biometrics* 1988.
7. Yang H. et al. BRCA2 function in DNA binding and recombination from a BRCA2–DSS1–ssDNA structure. *Science* 2002.
8. Richards S. et al. Standards and guidelines for the interpretation of sequence variants (ACMG/AMP). *Genet Med* 2015.
