# Graphical Abstract — prompt para Gemini (geração de imagem)

Este arquivo contém um **prompt avançado e pronto para colar** no Gemini (modelo de
geração de imagem, ex.: *Nano Banana* / Imagen no app Gemini) para produzir um
**graphical abstract** cientificamente preciso do PrimeVarClass, para o `README` e a
divulgação do repositório.

> **Dica importante sobre texto na imagem.** Modelos de imagem ainda erram texto — em
> especial acentos do português (ç, ã, ó). Duas estratégias:
> 1. **Recomendada:** gerar a ilustração **com rótulos curtos em inglês** (saem mais
>    limpos) e, se quiser, traduzir/reescrever os rótulos depois num editor.
> 2. Ou gerar **sem texto** (peça "no text labels") e adicionar os rótulos você mesmo.
> Peça sempre **"legible, no gibberish text"** e gere 3–4 variações.

---

## Prompt principal (colar no Gemini)

```
Create a clean, modern, publication-quality SCIENTIFIC GRAPHICAL ABSTRACT (infographic)
for a precision-medicine / computational-biology project named "PrimeVarClass".

STYLE: flat vector illustration, minimalist and professional, on a pure white
background; clear LEFT-TO-RIGHT narrative in 4 connected stages joined by thin arrows;
generous white space, balanced composition, subtle soft shadows, rounded panels,
consistent thin outlines. Accurate molecular biology. 3:2 landscape, high resolution.
Color palette: deep teal-blue (#1b5e7a) as primary, warm amber/gold (#e0a423) meaning
"detected / pathogenic", soft green (#2e7d46) meaning "benign / safe", neutral grays.

TITLE (top, bold dark navy): "PrimeVarClass"
SUBTITLE (smaller, gray): "domain-aware classification of BRCA1/BRCA2 missense variants —
open, externally validated, clinically calibrated"

STAGE 1 — "The problem" (far left): a stylized DNA double helix with ONE highlighted
point mutation (small red dot); a small pink cancer-awareness ribbon; a question mark
conveying clinical uncertainty. Label: "Variant of Uncertain Significance (VUS)".

STAGE 2 — "How the model sees the variant" (center-left): three feature streams flowing
into a funnel: (a) a horizontal PROTEIN DOMAIN MAP of BRCA1 with colored functional
domains marked "RING" (with two small zinc-ion spheres) and "BRCT"; (b) an abstract
PROTEIN LANGUAGE MODEL block labeled "ESM-2" drawn as a small neural-network / attention
motif; (c) three tiny biochemistry icons (charge, size, hydrophobicity).

STAGE 3 — "Classifier" (center): a compact machine-learning box labeled
"Random Forest (domain + ESM-2)" outputting a calibrated semicircular gauge that sweeps
from green ("benign") to gold ("pathogenic"), with a small clinical evidence tag
"ACMG PP3 / BP4".

STAGE 4 — "Clinical impact" (right): a triage worklist where many gray "VUS" rows become
a few gold "urgent review" rows and many green "deprioritized" rows; a small Brazil map
with a public-health (SUS) cross icon; and a row of small protein icons labeled
"BRCA1/2 · TP53 · VHL · Lynch · MEN2" to show multi-gene generalization.

BOTTOM RIBBON (thin banner, three small badges): "external validation (out-of-distribution)"
· "complements AlphaMissense where it abstains" · "no GPU · open · reproducible".

RULES: use ONLY the short label texts given above; do NOT invent numbers, formulas, extra
words, journal names or logos; keep every text element crisp and legible (no gibberish).
No photorealism, no human faces, no brand logos. Elegant, editorial, scientific.
```

---

## Variante em português (rótulos PT — use se preferir, ciente do risco de acento)

Troque os rótulos do prompt acima por estes:
- Título/subtítulo: **"PrimeVarClass"** / **"classificação de variantes BRCA1/BRCA2 consciente de domínio — aberta, validada externamente, calibrada clinicamente"**
- Estágio 1: **"Variante de Significado Incerto (VUS)"**
- Estágio 2: mapa de domínios **"RING"**, **"BRCT"**; bloco **"ESM-2"**; ícones de bioquímica
- Estágio 3: **"Random Forest (domínio + ESM-2)"**, medidor **"benigno → patogênico"**, selo **"ACMG PP3 / BP4"**
- Estágio 4: worklist **"revisão urgente"** (dourado) / **"despriorizadas"** (verde); mapa do Brasil + **"SUS"**; ícones **"BRCA1/2 · TP53 · VHL · Lynch · MEN2"**
- Rodapé: **"validação externa"** · **"complementa o AlphaMissense"** · **"sem GPU · aberto · reprodutível"**

---

## Precisão científica (não altere estes fatos ao iterar)

- O modelo combina **características bioquímicas + domínio funcional curado + ESM-2 (650M)**
  em um **Random Forest**; **não** é um modelo de imagem nem uma rede profunda de ponta a ponta.
- BRCA1 tem os domínios **RING** (coordenação de dois íons de zinco) e **BRCT**; BRCA2 tem o
  **DBD** (domínio de ligação ao DNA). Não invente outros domínios nessas proteínas.
- O diferencial é **complementar** o AlphaMissense onde ele se abstém — **não** "superá-lo".
- Generalização real demonstrada: BRCA1/2, TP53, VHL, Lynch (MLH1/MSH2/MSH6), MEN2 (RET).
- Contexto de impacto: triagem de VUS para laboratórios públicos (SUS) no Brasil.

Depois de gerar, salve a imagem como `docs/graphical_abstract.png` e referencie-a no `README`.
