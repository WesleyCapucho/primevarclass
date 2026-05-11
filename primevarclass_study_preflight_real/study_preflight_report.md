# Public BRCA Benchmark Real Data - Study Preflight

- Generated at: 2026-04-03T14:12:09Z
- Overall preflight: 98%
- Ready to run benchmark: yes
- Cohorts: 2 total / 1 train / 1 external

## Criteria

### Study design structure

- Score: 100%
- Status: ready
- Critical: yes
- Evidence: 1 coorte(s) de treino e 1 coorte(s) externas declaradas.
- Next step: Garantir exatamente uma coorte train e pelo menos uma coorte externa.

### Source config resolution

- Score: 100%
- Status: ready
- Critical: yes
- Evidence: 100% das coortes tiveram source_config resolvido com sucesso.
- Next step: Corrigir caminhos TOML e padronizar referencias relativas das coortes.

### Curated cohort validity

- Score: 100%
- Status: ready
- Critical: yes
- Evidence: 100% das coortes produziram linhas validas apos curadoria.
- Next step: Revisar filtros, colunas obrigatorias e labels das coortes com zero linhas validas.

### Label diversity

- Score: 100%
- Status: ready
- Critical: yes
- Evidence: 100% das coortes ficaram com pelo menos duas classes apos curadoria.
- Next step: Assegurar rotulos positivos e negativos suficientes para treino e validacao.

### Cohort independence

- Score: 100%
- Status: ready
- Critical: yes
- Evidence: Max overlap treino/externo=0% e label-conflict pairs=0%.
- Next step: Remover sobreposicoes entre treino e validacao externa antes da rodada final.

### Public-source traceability

- Score: 96%
- Status: ready
- Critical: yes
- Evidence: Readiness media de catalogo publico = 96%.
- Next step: Elevar release/schema coverage dos catalogos publicos usados no estudo.

### Sync automation readiness

- Score: 87%
- Status: ready
- Critical: no
- Evidence: Readiness media de automacao/sync = 87%.
- Next step: Aumentar staging automatizado das fontes mais criticas antes da rodada final.

## Cohort Diagnostics

- public_brca_training (train): valid_rows=1260, classes=2, public=96%, sync=2/3 automatable.
- bridges_like_external_validation (external_test): valid_rows=432, classes=2, public=96%, sync=2/3 automatable.

## Warnings

- Nenhum alerta critico identificado no preflight.

## Recommended Actions

- O estudo parece pronto para a execucao benchmark.