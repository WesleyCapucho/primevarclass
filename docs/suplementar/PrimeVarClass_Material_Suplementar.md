# Material Suplementar — PrimeVarClass

**Classificação consciente de domínio de variantes *missense* em BRCA1/BRCA2, validada externamente**

Este material suplementa o artigo principal (`docs/manuscrito/`) com análises adicionais que reforçam a validação e a relevância do método. Todas as análises são **reexecutáveis** a partir dos dados públicos deste repositório; os *scripts* correspondentes estão indicados em cada seção. Nenhum resultado, tabela ou figura foi fabricado ou simulado.

Coorte de avaliação (comum a S1–S3): as quatro coortes externas independentes de especialistas (ClinVar 2★+/ENIGMA/ClinGen), **n = 836** variantes; para as comparações que exigem escores de terceiros, o subconjunto com cobertura completa é **n = 621** (99 patogênicas, 522 benignas).

---

## S1. Benchmark contra o estado da arte

Comparamos o PrimeVarClass (modelo-carro-chefe: consciência de domínio + ESM-2) com preditores estabelecidos — **AlphaMissense** (Cheng et al., 2023), **REVEL** (Ioannidis et al., 2016) e **CADD** (Rentzsch et al., 2019) — nas **mesmas variantes externas** e sob a mesma métrica (AUC-ROC). Os escores de terceiros foram obtidos da API Ensembl VEP (transcrito MANE Select), de forma reprodutível.

**Tabela S1. Desempenho comparativo nas coortes externas (n = 621; script `scratch/benchmark_sota.py`).**

| Preditor | AUC-ROC | IC95% (bootstrap) | DeLong vs. PrimeVarClass |
| --- | ---: | :---: | :---: |
| REVEL | 0,930 | 0,895–0,961 | p = 0,145 |
| AlphaMissense | 0,926 | 0,883–0,962 | p = 0,244 |
| CADD | 0,920 | 0,886–0,951 | p = 0,434 |
| **PrimeVarClass (domínio + ESM-2)** | **0,907** | 0,864–0,943 | — |

**Leitura honesta.** No ponto estimado, o PrimeVarClass fica ligeiramente abaixo de REVEL, AlphaMissense e CADD; entretanto, **nenhuma dessas diferenças é estatisticamente significativa** (teste pareado de DeLong, todos os *p* > 0,14). Ou seja, um classificador **aberto, interpretável e calibrado**, treinado sob um protocolo anti-vazamento rigoroso, é **estatisticamente comparável ao estado da arte** — inclusive a modelos de escala muito maior e treinados sob supervisão massiva. Ressalva de justiça metodológica: AlphaMissense, REVEL e CADD podem ter sido expostos, em seus treinos, a rótulos das variantes de teste (vazamento **a favor deles**); reportamos a comparação mesmo assim, por transparência.

Ver **Figura S1** (curvas ROC sobrepostas e barras de AUC com IC95%).

![Figura S1](figuras/fig_benchmark_roc.png)

**Figura S1.** Comparação de desempenho no conjunto externo comum (n = 621). **(A)** Curvas ROC de PrimeVarClass, AlphaMissense, REVEL, CADD e do meta-classificador integrado (Seção S2). **(B)** AUC-ROC com intervalos de confiança de 95% por *bootstrap* (2000 reamostragens); as barras de erro se sobrepõem amplamente, coerente com a ausência de diferença estatística entre os preditores individuais.

---

## S2. Meta-classificador integrado (a contribuição de integração)

Nenhuma ferramenta computacional é a melhor em todos os contextos, e laboratórios clínicos já consultam múltiplos preditores. Avaliamos, então, se a **integração calibrada** dos sinais supera cada preditor isolado. Um meta-modelo logístico transparente combina PrimeVarClass + AlphaMissense + REVEL + CADD; o desempenho é medido **fora da amostra** por validação cruzada estratificada de 5 *folds* (sem vazamento).

**Tabela S2. Meta-classificador integrado (n = 621; script `scratch/meta_classifier.py`).**

| Modelo | AUC-ROC (fora da amostra) | IC95% |
| --- | ---: | :---: |
| **Meta-classificador (integração calibrada)** | **0,938** | 0,901–0,969 |
| REVEL | 0,930 | — |
| AlphaMissense | 0,926 | — |
| CADD | 0,920 | — |
| PrimeVarClass (domínio + ESM-2) | 0,907 | — |

Dois achados relevantes:

1. **A integração fornece a melhor estimativa pontual** (AUC 0,938), acima de qualquer preditor isolado — embora o ganho sobre o melhor individual (REVEL) **não** seja estatisticamente significativo (DeLong *p* = 0,43); reportamos isso explicitamente.
2. **O PrimeVarClass carrega sinal não redundante.** No meta-modelo, seu coeficiente logístico (0,60) é **comparável ao do REVEL** (0,59) e positivo, ao lado de AlphaMissense (1,03) e CADD (0,49). Isto é, mesmo na presença de AlphaMissense e REVEL, o sinal consciente de domínio + ESM-2 **contribui informação independente** — evidência objetiva de que o método não é uma mera réplica dos preditores existentes.

---

## S3. Calibração para força de evidência clínica (ACMG/AMP)

Para tornar o escore **clinicamente acionável**, calibramos o modelo-carro-chefe às categorias de força de evidência **PP3/BP4** do arcabouço ACMG/AMP, pelo método de razão de verossimilhança local de Tavtigian et al. (2018) e Pejaver et al. (2022), recomendado pelo ClinGen SVI (prior de patogenicidade 0,10). Os limiares de escore foram derivados **fora da amostra** (validação cruzada bloqueada por posição na coorte interna) e depois **validados na coorte externa independente**.

**Tabela S3. Limiares de escore e validação externa (script `scratch/acmg_calibration.py`).**

| Força de evidência | Limiar de escore | *n* externo | Fração patogênica | LR local (externo) |
| --- | :---: | ---: | ---: | ---: |
| **PP3_Forte** (patogênico) | escore ≥ 0,675 | 84 | **0,94** | **75,9** |
| PP3_Moderado | 0,345 ≤ escore < 0,675 | 117 | 0,32 | 2,2 |
| **BP4_Moderado** (benigno) | escore ≤ 0,255 | 444 | 0,03 | 0,16 |

**Leitura honesta.** A evidência **transfere-se robustamente nos extremos**: variantes com escore ≥ 0,675 recebem **PP3_Forte**, e na coorte externa esse grupo é 94% patogênico, com LR local de 75,9 — acima até do patamar "forte" (≥ 18,7). Simetricamente, escore ≤ 0,255 dá **BP4_Moderado** (3% patogênicas). A faixa intermediária é deixada **não informativa** — o comportamento clinicamente responsável: uma VUS só é movida quando a evidência é real. É exatamente esse par (evidência forte nos extremos + abstenção no meio) que sustenta o uso do escore para **priorizar VUS** para reclassificação.

![Figura S2](figuras/fig_acmg_calibration.png)

**Figura S2.** Calibração ACMG/AMP: razão de verossimilhança local (LR⁺) da evidência "escore ≥ t" em função do limiar *t* (escala logarítmica). As linhas tracejadas horizontais marcam os patamares de força PP3 (supporting/moderate/strong); as linhas pontilhadas verticais, os limiares de escore correspondentes. A curva é monotônica: quanto maior o escore, mais forte a evidência patogênica.

---

## S4. Validação funcional ortogonal (*deep mutational scanning*) — preliminar

Um teste independente de rótulos clínicos: o escore acompanha a **função molecular medida em laboratório**? Correlacionamos as predições com ensaios de *saturation genome editing* (Findlay et al., 2018) e de reparo por recombinação homóloga — HDR (Starita et al., 2015) para BRCA1, obtidos do MaveDB (script `scratch/functional_validation.py`).

**Estado atual (honesto).** Os escores ESM-2 pré-computados cobrem a coorte clínica, mas **ainda não** a maioria das posições cobertas por esses ensaios de DMS (por exemplo, apenas 84 variantes do ensaio HDR têm ESM-2 disponível). No subconjunto coberto do ensaio HDR de Starita, o sinal ESM-2 já separa perda de função com **AUC = 0,836** — direção promissora. A validação funcional em escala completa está **em andamento**, alimentada pela expansão da cobertura ESM-2 (execução em GPU, Colab; ver Seção S5 e `scratch/colab_esm2_panel.py`), e será consolidada quando os escores expandidos forem integrados.

![Figura S3](figuras/fig_functional_validation.png)

**Figura S3.** Predições do modelo *versus* escore funcional experimental (BRCA1), por ensaio de DMS. A validação é limitada pela cobertura atual de ESM-2 nas regiões ensaiadas; a versão completa acompanhará a expansão da cobertura.

---

## S5. Reprodutibilidade e proveniência dos dados

Todas as fontes são **públicas e auditáveis**:

- **Rótulos clínicos:** ClinVar (revisão 2★+), painéis de especialistas ENIGMA/ClinGen.
- **Frequências populacionais:** gnomAD (r4).
- **Anotação de domínios:** UniProt (BRCA1 P38398; BRCA2 P51587).
- **Estruturas 3D:** coordenadas experimentais do RCSB PDB (1JM7, 1JNX, 1N5O, 1MJE).
- **Escores de terceiros (S1):** Ensembl VEP REST (AlphaMissense, REVEL, CADD; transcrito MANE Select).
- **Ensaios funcionais (S4):** MaveDB (`urn:mavedb:00001222`, `urn:mavedb:00000081`).

Reexecução (a partir da raiz do repositório):

```bash
pip install -e ".[explain,dev]"
python scratch/benchmark_sota.py        # S1 — escores de terceiros + AUC/DeLong
python scratch/meta_classifier.py       # S2 — meta-classificador integrado
python scratch/benchmark_figure.py      # Figura S1
python scratch/acmg_calibration.py      # S3 — calibração ACMG + Figura S2
python scratch/functional_validation.py # S4 — validação funcional (DMS)
```

Sementes aleatórias fixas garantem reprodutibilidade determinística. Artefatos numéricos (`.json`, `.csv`) são gravados em `primevarclass_manuscript_analysis/`.

---

## Declaração de integridade

Nenhum dado, figura ou métrica foi fabricado. Todas as comparações desfavoráveis ao PrimeVarClass (por exemplo, o desempenho ligeiramente superior de REVEL/AlphaMissense na Tabela S1) são reportadas de forma transparente. As limitações — comparação sujeita a possível vazamento a favor de terceiros, cobertura funcional ainda parcial, escopo de dois genes — estão declaradas em seus respectivos pontos. O uso de ferramentas de inteligência artificial no desenvolvimento é declarado no artigo principal, sob responsabilidade humana integral.
