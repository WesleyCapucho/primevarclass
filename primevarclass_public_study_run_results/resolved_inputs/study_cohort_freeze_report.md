# Study Cohort Freeze

- Generated at: 2026-04-03T04:29:31Z
- Study: Public BRCA Benchmark Example
- Real-data readiness: 19%
- Ready for real-data study: not yet
- Ready cohorts: 0/2

## Cohorts

- public_brca_training (train): 19% | example=3 | placeholder_release=3 | ready=no
- bridges_like_external_validation (external_test): 19% | example=3 | placeholder_release=3 | ready=no

## Recommended Actions

- Remover arquivos de exemplo do estudo final antes da rodada real.
- Trocar placeholders por release_version/release_date reais para ClinVar, gnomAD, MaveDB e ENIGMA.
- Substituir demos por dados reais e manter apenas fontes congeladas para o benchmark final.
- Preferir staging em data/raw ou artefatos resolvidos versionados para coortes finais.
- Congelar cada coorte apenas com dados reais versionados antes do benchmark final.