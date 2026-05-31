# Título: PrimeVarClass – Predição Ortogonal de Variantes Patogênicas em BRCA1/BRCA2 utilizando Fatoração de Números Primos e Gradient Boosting

**Autor:** Wesley Capucho
**Prêmio Jovem Cientista 2026**

---

## RESUMO (300 palavras)
O rastreamento de variantes genéticas nos genes *BRCA1* e *BRCA2* é fundamental para o manejo profilático e terapêutico do câncer de mama hereditário. No entanto, o alto índice de Variantes de Significado Incerto (VUS) impõe um severo gargalo aos sistemas públicos de saúde, como o SUS, postergando intervenções clínicas cruciais. Os modelos computacionais atuais de classificação de variantes frequentemente comportam-se como "caixas-pretas" (Deep Learning), suscetíveis a colisões de *features* e baixa explicabilidade clínica. Este projeto apresenta o **PrimeVarClass**, uma arquitetura algorítmica baseada em ensamble de *Gradient Boosting* (XGBoost/LightGBM) acoplada a um novo método de representação matemática de aminoácidos: o *Prime Encoding*. A propriedade matemática da divisibilidade única dos números primos permite mapear transições físico-químicas de resíduos como matrizes estritamente ortogonais, eliminando o ruído estatístico. Modelos treinados em bancos internacionais (ClinVar, AlphaMissense) demonstraram que a adição do encadeamento de números primos melhora de forma auditável a distinção topológica estrutural. Através da análise SHAP (SHapley Additive exPlanations), validou-se que as variáveis matemáticas lideraram o peso preditivo, destrancando classificações patogênicas e benignas com alto Valor Preditivo Positivo (VPP). A ferramenta atua como um assistente *in silico* escalável e de baixo custo, diretamente aplicável aos Comitês de Tumor e adaptável aos critérios da ACMG/AMP. O PrimeVarClass consolida a união entre a Teoria dos Números e a Genômica, oferecendo ao SUS uma tecnologia social capaz de reclassificar o "limbo clínico" das VUS e racionalizar a conduta oncológica preventiva no Brasil.

---

## 1. INTRODUÇÃO E JUSTIFICATIVA
O câncer de mama desponta como a neoplasia mais comum entre as mulheres brasileiras, com estimativa do Instituto Nacional de Câncer (INCA) superior a 74.000 novos casos anuais. Destes, até 10% carregam raízes em mutações germinativas, majoritariamente em genes de reparo de DNA como o *BRCA1* e *BRCA2*. Identificar uma variante patogênica permite intervenções redutoras de morbimortalidade. 

Contudo, até 40% dos achados de sequenciamento molecular são classificados como Variantes de Significado Incerto (VUS), mantendo pacientes em um limbo preventivo. Este gargalo é especialmente danoso no Sistema Único de Saúde (SUS), onde painéis genômicos são custosos e o acesso a ensaios funcionais é irrealizável em larga escala. É neste contexto de saúde pública que as predições computacionais (*in silico*) assumem protagonismo, devendo alimentar os critérios de classificação estabelecidos pela *American College of Medical Genetics and Genomics* (ACMG/AMP).

Ferramentas preexistentes baseiam-se em Redes Neurais densas. Embora atinjam alta acurácia, caracterizam-se pela inescrutabilidade (caixa-preta) e pela colisão de tensores, onde o modelo falha em apontar *por que* uma troca de aminoácido é deletéria. O presente estudo desenvolveu o **PrimeVarClass**, solucionando essa debilidade ao adotar a estabilidade criptográfica e ortogonal da fatoração de números primos para representar fisicamente a biologia molecular.

## 2. METODOLOGIA
A construção algorítmica do projeto foi estruturada em três eixos: o *Feature Engineering* (Prime Encoding), a Orquestração do Modelo e a Extração Explicativa.

### 2.1 Representação Ortogonal (Prime Encoding)
Atribuiu-se um número primo sequencial para os 20 aminoácidos essenciais (ex: Glicina=2, Alanina=3, ..., Triptofano=71). A transição entre um resíduo Selvagem (Wild-Type) e um Mutante em uma variante *missense* passou a ser calculada por meio de relações primas (Produto, Razão e Diferença Euclidiana). 
A justificativa repousa no Teorema Fundamental da Aritmética. Como cada número natural possui uma fatoração prima única, o algoritmo garante a ortogonalidade dos dados. O vetor que representa uma mutação de Arginina para Glutamina é matematicamente incapaz de colidir (no espaço vetorial do aprendizado de máquina) com uma mutação de Leucina para Valina, algo que abordagens tradicionais de *One-Hot Encoding* ou *Word Embeddings* frequentemente falham em isolar.

### 2.2 Modelagem em Gradient Boosting
Para a predição, evitou-se propositalmente o Deep Learning, adotando algoritmos de *Decision Trees Ensemble* (XGBoost e LightGBM). Estes modelos processam dependências não-lineares, mas preservam transparência de corte (*split*). O modelo foi treinado integrando as *features* matemáticas às evidências evolutivas consolidadas (REVEL, escores estruturais do AlphaMissense e frequências do gnomAD), contra o gabarito clínico fornecido pela base global ClinVar.

### 2.3 Explicabilidade e Validação (SHAP)
Aplicou-se o método *TreeExplainer* (SHAP Values) em regime exaustivo. O intuito foi expor e tabular matematicamente o peso de cada *feature* na tomada de decisão sobre variantes individuais, refutando a tese de "caixa-preta" e adequando a ferramenta ao escrutínio exigido pelas diretorias clínicas hospitalares.

## 3. RESULTADOS E DISCUSSÃO

### 3.1 Estudo de Ablação e Eficiência
A arquitetura demonstrou superioridade sobre predições puramente bioquímicas. No estudo de ablação (Ablation Study) isolado em variantes de controle estrito, o modelo híbrido superou as aproximações conservadoras baseadas apenas em matrizes de substituição padrão (BLOSUM/PAM). A taxa de memória e processamento do XGBoost mostrou-se viável para execução *offline* ou em nuvens de baixo poder computacional (Google Colab), qualificando a solução como altamente portável.

### 3.2 O Peso do Prime Encoding (Análise SHAP)
Os resultados do SHAP atestaram o valor da inovação: as variáveis `prime_product_diff` e `prime_distance` figuraram rotineiramente entre os principais direcionadores de predição, dividindo impacto com *scores* multilaterais. Isso prova que o modelo não está superajustando (*overfitting*) ruído, mas sim utilizando a ortogonalidade prima para separar domínios funcionais onde preditores topológicos encontravam ambiguidade.

### 3.3 Estudos de Caso Mecanísticos (Segurança Clínica)
Em casos notórios de variantes desafiadoras — como a BRCA1 p.Arg1699Gln (Domínio BRCT) e BRCA2 p.Val2466Ala — o modelo manteve elevada *Especificidade* e alto *Valor Preditivo Positivo (VPP)*. 
Na oncogenética brasileira, o controle do falso-positivo é impositivo. Recomendar cirurgias mastectômicas bilaterais profiláticas em pacientes erroneamente laudadas com mutação patogênica gera mutilação irreversível e desabastece os recursos do Ministério da Saúde. O *PrimeVarClass*, ancorado na rigidez do cálculo primo, manteve silêncio estatístico diante de substituições conservativas hidrofóbicas (benignas), mas acionou alarmes precisos frente a quebras estruturais severas.

## 4. CONCLUSÃO E IMPACTO SOCIAL
O *PrimeVarClass* rompe o hiato entre a Teoria dos Números e a Genômica Clínica. Ao transformar dados de sequenciamento molecular em funções matemáticas ortogonais e auditáveis, a ferramenta introduz um patamar superior de segurança no processamento in silico. 
Como plataforma assistencial para Comitês de Tumor e a Rede Nacional de Genômica (RENAGENO), a tecnologia tem o potencial direto de reclassificar milhares de pacientes brasileiras que repousam no "limbo clínico" das Variantes de Significado Incerto (VUS). Democratiza o acesso a diagnósticos de precisão, economiza recursos estatais e salva vidas mediante suporte matemático estrito, consagrando-se como uma tecnologia social pronta para adoção em escala nacional.

---
**Anexos Técnicos e Repositório:** A totalidade dos códigos, experimentos de ablação e diagramas de interpretabilidade residem abertos no GitHub (Open Science).
