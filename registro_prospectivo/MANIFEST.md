# Registro prospectivo de predições — PrimeVarClass

**Data de registro:** 2026-07-09
**Arquivo de predições:** `brca_vus_predictions_2026-07-09.csv`
**SHA-256:** `ecc464ccac579b0b20dd9b5eb4c385208e5a099e20b4655b33b2d01ceeb9e040`

## O que é isto

Um **compromisso público, datado e imutável**. Registramos aqui a predição
calibrada do PrimeVarClass para **todas as variantes** *missense* de BRCA1/BRCA2
que, nesta data, são **VUS** (significado incerto) ou têm **classificações
conflitantes** no ClinVar. À medida que painéis de especialistas resolverem essas
variantes nos próximos anos, qualquer pessoa poderá conferir nossa taxa de acerto
contra este registro — que não pode ser alterado retroativamente (verifique o
SHA-256 acima).

Esta é a versão **falsificável** de "validação prospectiva": não
afirmamos ter validação prospectiva hoje; nós a *tornamos possível* para o futuro.

## Conteúdo (12196 variantes não resolvidas)

| Predição | n | Interpretação |
| --- | ---: | --- |
| **PP3_Forte → patogênica** | 326 | predizemos reclassificação como (provavelmente) patogênica |
| **BP4_Moderado → benigna** | 9566 | predizemos reclassificação como (provavelmente) benigna |
| Indeterminada (mantém VUS) | 2304 | abstenção responsável — não arriscamos um palpite |

As predições PP3_Forte e BP4_Moderado usam apenas os dois níveis de evidência
externamente validados (Material Suplementar S3): na coorte externa, PP3_Forte
correspondeu a 94% de patogênicas e BP4_Moderado a 3%.

## Como validar no futuro

1. Confirme a integridade: `sha256sum brca_vus_predictions_2026-07-09.csv` deve
   bater com o valor acima.
2. Baixe o ClinVar atual e verifique, entre as variantes aqui listadas como VUS
   em 2026-07-09, quantas foram reclassificadas — e em que direção.
3. Compare a direção real com a coluna `predicted_reclassification`.

Metodologia de pontuação: `scratch/generate_evidence_resource.py` e
`scratch/acmg_calibration.py` (limiares PP3_Forte ≥ 0,675 e BP4_Moderado ≤ 0,255).
