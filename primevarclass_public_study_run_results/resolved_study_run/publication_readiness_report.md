# Public BRCA Benchmark Example - Publication Readiness

- Generated at: 2026-04-03T04:33:16Z
- Overall readiness: 71%
- Overall status: partial
- Claim tier: insufficient (37%)
- Real-data freeze: 19%
- Ready for high-impact submission: not yet
- Cohorts: 2 total / 1 external

## Executive Summary

- Strong areas: Cohort design and labels, Data versioning and manifests, Cohort independence, External validation coverage, Artifact package completeness
- Critical gaps: Real-data cohort freeze, Comparative evidence strength, Claim strength and framing
- Best external signal: bridges_like_external_validation -> external_predictors_only (AUC-ROC=1.0000, delta=0.0000, evidence=no_gain)

## Criteria

### Cohort design and labels

- Score: 100%
- Status: ready
- Critical: yes
- Evidence: 1 cohort(s) de treino, 1 coorte(s) externas e 100% das coortes com pelo menos duas classes.
- Next step: Garantir exatamente uma coorte de treino e ampliar coortes externas rotuladas quando necessario.

### Data versioning and manifests

- Score: 100%
- Status: ready
- Critical: yes
- Evidence: 100% das coortes com data release manifest e 100% com fingerprint do dataset integrado.
- Next step: Assegurar manifests e fingerprints para todas as coortes usadas no estudo.

### Public source traceability

- Score: 72%
- Status: partial
- Critical: yes
- Evidence: Media de release=45%, schema=100% e catalog readiness=72%.
- Next step: Completar tracking de release e cobertura estrutural das fontes publicas reais por coorte.

### Cohort independence

- Score: 100%
- Status: ready
- Critical: yes
- Evidence: Independencia global em 100% com max overlap treino/externo=0%.
- Next step: Eliminar sobreposicao de variantes entre treino e validacao externa antes da submissao final.

### Real-data cohort freeze

- Score: 19%
- Status: gap
- Critical: yes
- Evidence: Freeze de coortes em 19% com 2 coorte(s) ainda bloqueadas por demo/example.
- Next step: Substituir datasets de exemplo por coortes reais versionadas antes da submissao final.

### Internal validation package

- Score: 75%
- Status: partial
- Critical: no
- Evidence: Training metrics=100%, repeated holdout=0%, gene-stratified metrics=100% e model registry=100%.
- Next step: Manter repeated holdout, modelos versionados e analise gene-estratificada em toda release.

### External validation coverage

- Score: 100%
- Status: ready
- Critical: yes
- Evidence: 100% das coortes externas com metrica combinada e 100% com comparacao pareada AUC-ROC.
- Next step: Executar validacao externa para todas as coortes planejadas e preservar comparacoes pareadas.

### Comparative evidence strength

- Score: 25%
- Status: gap
- Critical: yes
- Evidence: 0% das coortes com ganho suportado, 0% com ganho positivo e melhor experimento consensus_top3.
- Next step: Rodar o benchmark em dados reais e buscar ganho consistente contra o baseline declarado.

### Claim strength and framing

- Score: 37%
- Status: gap
- Critical: yes
- Evidence: Claim tier insufficient em 37% para hybrid_plus_external vs external_predictors_only.
- Next step: Fortalecer a alegacao central do estudo ate um tier moderado ou forte antes da submissao.

### Artifact package completeness

- Score: 100%
- Status: ready
- Critical: yes
- Evidence: 100% dos artefatos centrais do estudo foram materializados no output final.
- Next step: Garantir que tabelas, dossie e manifestos sejam exportados em toda execucao de estudo.

## Cohort Evidence

- public_brca_training (train): n=4, release=45%, schema=100%, benchmark=36%.
- bridges_like_external_validation (external_test): n=4, release=45%, schema=100%, benchmark=36%.

## External Comparative Evidence

- bridges_like_external_validation: best=external_predictors_only (AUC-ROC=1.0000) | delta vs baseline=0.0000 [0.0000, 0.0000] => no_gain

## Recommended Next Actions

- Completar tracking de release e cobertura estrutural das fontes publicas reais por coorte.
- Substituir datasets de exemplo por coortes reais versionadas antes da submissao final.
- Manter repeated holdout, modelos versionados e analise gene-estratificada em toda release.
- Rodar o benchmark em dados reais e buscar ganho consistente contra o baseline declarado.
- Fortalecer a alegacao central do estudo ate um tier moderado ou forte antes da submissao.