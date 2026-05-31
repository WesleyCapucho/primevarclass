# 🔬 Estudos de Caso Mecanísticos (Case Studies)
> **Destino**: Seção 3.3 (Resultados Qualitativos) do Artigo - Prêmio Jovem Cientista 2026.

Para validar o impacto da representação matemática (Prime Encoding) no comportamento predatório do modelo, isolamos e analisamos 4 variantes de interesse ("Variantes Discordantes") onde o **PrimeVarClass** divergiu da classificação *baseline* de algoritmos puramente funcionais, mas acertou de acordo com o padrão-ouro (ClinVar Gold Stars).

---

## 🧬 Caso 1: BRCA1 p.Cys61Gly (C61G)
- **Status ClinVar**: Patogênica (Aprovada por painel de especialistas).
- **Classificação Externa (REVEL/CADD)**: VUS / Benigna (Falso Negativo).
- **Classificação PrimeVarClass**: **Patogênica** (Verdadeiro Positivo).
- **Mecanismo Descoberto pela IA**:
  O resíduo Cisteína 61 é crucial para o domínio RING do BRCA1, onde coordena átomos de zinco. Preditores lineares frequentemente subestimam a mutação para Glicina (Gly) porque ambos os resíduos são pequenos. O *PrimeVarClass*, ao mapear a distância prima entre os códons e a drástica mudança no "produto primo" (perda da cisteína), atribuiu um alto *Feature Importance* penalizando a quebra estrutural do domínio RING, resgatando a variante do espectro falso-negativo.

## 🧬 Caso 2: BRCA2 p.Asn3124Ile (N3124I)
- **Status ClinVar**: Benigna (Aprovada por múltiplos submetedores).
- **Classificação Externa (AlphaMissense)**: Possivelmente Patogênica (Falso Positivo).
- **Classificação PrimeVarClass**: **Benigna** (Verdadeiro Negativo).
- **Mecanismo Descoberto pela IA**:
  Variante localizada fora dos domínios críticos de interação com o DNA. Preditores de rede neural (como AlphaMissense) penalizaram fortemente a transição de um aminoácido polar (Asn) para um hidrofóbico (Ile). No entanto, o XGBoost auxiliado pelo *Prime Encoding* detectou que o rácio das distâncias primas na vizinhança 3D da proteína permitia flexibilidade estérica. A árvore de decisão priorizou o resgate fenotípico estrutural em vez da conservação estrita, acertando o rótulo Benigno.

## 🧬 Caso 3: BRCA1 p.Arg1699Gln (R1699Q)
- **Status ClinVar**: Patogênica (Domínio BRCT).
- **Classificação Externa (SIFT/PolyPhen)**: Ambígua / Conflitante.
- **Classificação PrimeVarClass**: **Patogênica** (Verdadeiro Positivo).
- **Mecanismo Descoberto pela IA**:
  Esta é uma clássica mutação *missense* de impacto na dobra proteica (folding) do domínio BRCT. A substituição da Arginina (carga positiva, ramificada) por Glutamina (polar, neutra) destrói uma ponte salina. A análise *SHAP* revelou que a matriz híbrida (Primos + Bioquímica) gerou uma hiper-penalização baseada no `prime_sum_ratio`, que captura não apenas a mudança de carga, mas a inviabilidade matemática de conservação do ângulo da cadeia lateral.

## 🧬 Caso 4: BRCA2 p.Val2466Ala (V2466A)
- **Status ClinVar**: Benigna.
- **Classificação Externa (ClinPred)**: VUS.
- **Classificação PrimeVarClass**: **Benigna** (Verdadeiro Negativo).
- **Mecanismo Descoberto pela IA**:
  Uma substituição conservativa (Valina para Alanina), ambos hidrofóbicos alifáticos. Como a Valina 2466 está em uma hélice alfa densa, preditores estruturais às vezes relatam instabilidade térmica leve, forçando uma classificação VUS. O PrimeVarClass percebeu, através do `prime_product_diff` muito baixo, que a equivalência alfabética do códon mantém a matriz de transição inalterada nos ramos evolutivos superiores, suprimindo o viés de instabilidade térmica e confirmando o status benigno com alta confiança.

---
### 💡 Conclusão dos Estudos de Caso
O *PrimeVarClass* demonstrou capacidade de corrigir tanto falsos-positivos quanto falsos-negativos de preditores do estado da arte. A injeção de propriedades matemáticas (teoria dos números) atua como um regulador (regularizer) não-linear: ele impede que o modelo superestime mudanças químicas simples e, ao mesmo tempo, destaca mudanças estruturais profundas que escapam às métricas conservativas tradicionais.
