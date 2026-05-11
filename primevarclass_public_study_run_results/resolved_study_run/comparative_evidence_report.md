# Comparative Evidence Package

- Generated at: 2026-04-03T04:33:16Z
- Baseline experiment: external_predictors_only
- Overall comparative strength: 25%
- Best supported experiment: consensus_top3 (consensus_top3)
- Mean supported delta AUC-ROC: 0.0000

## Criteria

### Pairwise external coverage

- Score: 100%
- Status: ready
- Critical: yes
- Evidence: 1/1 coortes externas possuem comparacao AUC-ROC vs baseline.
- Next step: Garantir comparacao pareada AUC-ROC para todas as coortes externas planejadas.

### Supported external gain

- Score: 0%
- Status: gap
- Critical: yes
- Evidence: 0% das coortes externas apresentam pelo menos um ganho suportado (IC inferior > 0).
- Next step: Buscar ganhos suportados em mais coortes externas com dados reais versionados.

### Prime-signal support rate

- Score: 0%
- Status: gap
- Critical: yes
- Evidence: Prime/hibrido teve 0% de suporte estrito e 0% de ganho positivo entre as coortes externas.
- Next step: Fortalecer a vantagem do bloco primo/hibrido contra o baseline em multiplas coortes.

### Internal-external alignment

- Score: 35%
- Status: gap
- Critical: no
- Evidence: Melhor experimento interno: biochemical_only / feature set biochemical_only.
- Next step: Alinhar o melhor experimento interno com ganhos positivos sustentados na validacao externa.

### Cross-cohort consistency

- Score: 0%
- Status: gap
- Critical: no
- Evidence: Feature set dominante entre as coortes externas: - com consistencia de 0%.
- Next step: Buscar consistencia do mesmo bloco de sinal entre as coortes externas do estudo.

## Cohort Summary

- bridges_like_external_validation: supported=- (delta=-) | prime_supported=no | prime_positive=no

## Experiment Support

- consensus_top3: supported=0% | positive=0% | mean delta=0.0000 | internal rank=-
- hybrid_plus_external: supported=0% | positive=0% | mean delta=0.0000 | internal rank=6.0000
- biochemical_only: supported=0% | positive=0% | mean delta=-0.7018 | internal rank=1.0000
- hybrid_plus_conservation: supported=0% | positive=0% | mean delta=-0.8509 | internal rank=4.0000
- hybrid_plus_conservation_structure: supported=0% | positive=0% | mean delta=-0.8509 | internal rank=5.0000
- hybrid: supported=0% | positive=0% | mean delta=-1.0000 | internal rank=3.0000
- prime_only: supported=0% | positive=0% | mean delta=-1.0000 | internal rank=7.0000

## Recommended Actions

- Buscar ganhos suportados em mais coortes externas com dados reais versionados.
- Fortalecer a vantagem do bloco primo/hibrido contra o baseline em multiplas coortes.
- Alinhar o melhor experimento interno com ganhos positivos sustentados na validacao externa.
- Buscar consistencia do mesmo bloco de sinal entre as coortes externas do estudo.