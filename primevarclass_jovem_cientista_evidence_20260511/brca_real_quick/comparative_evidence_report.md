# Comparative Evidence Package

- Generated at: 2026-05-11T05:08:02Z
- Baseline experiment: external_predictors_only
- Overall comparative strength: 85%
- Best supported experiment: gene_balanced_specialist (gene_balanced_specialist)
- Mean supported delta AUC-ROC: 0.1792
- Aggregate multicohort effect: gene_balanced_specialist => delta=0.1504 [0.0982, 0.2026] | confidence=100%
- Pooled multicohort effect: gene_balanced_specialist => delta=0.2210 [0.1636, 0.2844] | confidence=100%

## Criteria

### Pairwise external coverage

- Score: 100%
- Status: ready
- Critical: yes
- Evidence: 4/4 coortes externas possuem comparacao AUC-ROC vs baseline.
- Next step: Garantir comparacao pareada AUC-ROC para todas as coortes externas planejadas.

### Supported external gain

- Score: 100%
- Status: ready
- Critical: yes
- Evidence: 75% das coortes externas apresentam pelo menos um ganho suportado por coorte, enquanto o pooled multicohorte para gene_balanced_specialist ficou em 0.2210 [0.1636, 0.2844].
- Next step: Buscar ganhos suportados por coorte e manter o suporte pooled multicohorte na rodada final.

### High-confidence clinical leadership

- Score: 85%
- Status: ready
- Critical: no
- Evidence: gene_balanced_specialist lidera as coortes clinicas de alta confianca com 100% de ganho positivo e 50% de suporte estrito.
- Next step: Aumentar o suporte estrito nas coortes clinicas de maior confianca para aproximar o estudo de uma alegacao mais forte.

### Aggregate multicohort direction

- Score: 100%
- Status: ready
- Critical: no
- Evidence: Meta-efeito: gene_balanced_specialist = 0.1504 [0.0982, 0.2026], pooled: gene_balanced_specialist = 0.2210 [0.1636, 0.2844] com confianca direcional de 100%.
- Next step: Consolidar o ganho agregado ate cruzar zero com margem mais confortavel e replicacao multicohorte.

### Pooled cross-metric support

- Score: 100%
- Status: ready
- Critical: yes
- Evidence: O pooled multicohorte ficou em 100% de confianca direcional simultanea para AUC-ROC e AUC-PR.
- Next step: Sustentar ganho pooled simultaneo em AUC-ROC e AUC-PR para fortalecer a narrativa central do paper.

### Prime-signal support rate

- Score: 62%
- Status: partial
- Critical: yes
- Evidence: Prime/hibrido teve 50% de suporte estrito e 75% de ganho positivo entre as coortes externas, com pooled de 100%.
- Next step: Fortalecer a vantagem do bloco primo/hibrido contra o baseline em multiplas coortes.

### Internal-external alignment

- Score: 100%
- Status: ready
- Critical: no
- Evidence: Melhor experimento interno: hybrid_plus_external__logistic_regression / feature set hybrid_plus_external.
- Next step: Alinhar o melhor experimento interno com ganhos positivos sustentados na validacao externa.

### Cross-cohort consistency

- Score: 25%
- Status: gap
- Critical: no
- Evidence: Feature set dominante entre as coortes externas: hybrid com consistencia de 25%.
- Next step: Buscar consistencia do mesmo bloco de sinal entre as coortes externas do estudo.

## Cohort Summary

- bridges_like_external_validation_brca1: supported=nan (delta=-) | prime_supported=no | prime_positive=no
- bridges_like_external_validation_brca2: supported=hybrid__logistic_regression (delta=0.5175) | prime_supported=yes | prime_positive=yes
- clinvar_expert_external_validation_brca1: supported=gene_balanced_specialist (delta=0.1704) | prime_supported=no | prime_positive=yes
- clinvar_expert_external_validation_brca2: supported=hybrid_plus_conservation_structure__logistic_regression (delta=0.1376) | prime_supported=yes | prime_positive=yes

## Experiment Support

- gene_balanced_specialist: supported=50% | positive=75% | mean delta=0.1792 | aggregate=0.1504 (100%) | pooled=0.2210 (100%) | internal rank=6.0000
- consensus_top3: supported=50% | positive=75% | mean delta=0.1513 | aggregate=0.0795 (100%) | pooled=0.2178 (100%) | internal rank=-
- hybrid_plus_external__logistic_regression: supported=50% | positive=75% | mean delta=0.1509 | aggregate=0.0818 (100%) | pooled=0.2195 (100%) | internal rank=1.0000
- biochemical_only__logistic_regression: supported=50% | positive=50% | mean delta=0.1538 | aggregate=0.0838 (100%) | pooled=0.2201 (100%) | internal rank=5.0000
- hybrid_plus_conservation_structure__logistic_regression: supported=50% | positive=50% | mean delta=0.1514 | aggregate=0.0817 (100%) | pooled=0.2161 (100%) | internal rank=4.0000
- hybrid__logistic_regression: supported=50% | positive=50% | mean delta=0.1514 | aggregate=0.0817 (100%) | pooled=0.2161 (100%) | internal rank=2.0000
- hybrid_plus_conservation__logistic_regression: supported=50% | positive=50% | mean delta=0.1514 | aggregate=0.0817 (100%) | pooled=0.2161 (100%) | internal rank=3.0000
- prime_only__logistic_regression: supported=25% | positive=50% | mean delta=0.0391 | aggregate=-0.0270 (22%) | pooled=0.0833 (100%) | internal rank=7.0000

## Recommended Actions

- Fortalecer a vantagem do bloco primo/hibrido contra o baseline em multiplas coortes.
- Buscar consistencia do mesmo bloco de sinal entre as coortes externas do estudo.