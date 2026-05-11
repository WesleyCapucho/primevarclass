# PrimeVarClass Multigene Study Factory

- Generated at: `2026-04-18T06:01:48Z`
- Total scaffolded genes: `6`
- Phase 1 genes: `TP53`
- Phase 2 genes: `GCK, PTEN, MSH2, F9, KRAS`

## Recommended Next Move

- Start with `TP53` as the first multigene real benchmark.

## Scaffold Index

| gene | rollout_phase | prime_priority | benchmark_config_path | train_config_path | external_clinical_config_path | external_secondary_config_path |
| --- | --- | --- | --- | --- | --- | --- |
| TP53 | phase_1_immediate | high | C:\Users\Wesley Capucho\Documents\IA dos números primos\configs\multigene\tp53\public_tp53_benchmark.toml | C:\Users\Wesley Capucho\Documents\IA dos números primos\configs\multigene\tp53\public_tp53_real.toml | C:\Users\Wesley Capucho\Documents\IA dos números primos\configs\multigene\tp53\public_tp53_external_clinical.toml | C:\Users\Wesley Capucho\Documents\IA dos números primos\configs\multigene\tp53\public_tp53_external_secondary.toml |
| GCK | phase_2_expansion | high | C:\Users\Wesley Capucho\Documents\IA dos números primos\configs\multigene\gck\public_gck_benchmark.toml | C:\Users\Wesley Capucho\Documents\IA dos números primos\configs\multigene\gck\public_gck_real.toml | C:\Users\Wesley Capucho\Documents\IA dos números primos\configs\multigene\gck\public_gck_external_clinical.toml | C:\Users\Wesley Capucho\Documents\IA dos números primos\configs\multigene\gck\public_gck_external_secondary.toml |
| PTEN | phase_2_expansion | high | C:\Users\Wesley Capucho\Documents\IA dos números primos\configs\multigene\pten\public_pten_benchmark.toml | C:\Users\Wesley Capucho\Documents\IA dos números primos\configs\multigene\pten\public_pten_real.toml | C:\Users\Wesley Capucho\Documents\IA dos números primos\configs\multigene\pten\public_pten_external_clinical.toml | C:\Users\Wesley Capucho\Documents\IA dos números primos\configs\multigene\pten\public_pten_external_secondary.toml |
| MSH2 | phase_2_expansion | medium | C:\Users\Wesley Capucho\Documents\IA dos números primos\configs\multigene\msh2\public_msh2_benchmark.toml | C:\Users\Wesley Capucho\Documents\IA dos números primos\configs\multigene\msh2\public_msh2_real.toml | C:\Users\Wesley Capucho\Documents\IA dos números primos\configs\multigene\msh2\public_msh2_external_clinical.toml | C:\Users\Wesley Capucho\Documents\IA dos números primos\configs\multigene\msh2\public_msh2_external_secondary.toml |
| F9 | phase_2_expansion | medium | C:\Users\Wesley Capucho\Documents\IA dos números primos\configs\multigene\f9\public_f9_benchmark.toml | C:\Users\Wesley Capucho\Documents\IA dos números primos\configs\multigene\f9\public_f9_real.toml | C:\Users\Wesley Capucho\Documents\IA dos números primos\configs\multigene\f9\public_f9_external_clinical.toml | C:\Users\Wesley Capucho\Documents\IA dos números primos\configs\multigene\f9\public_f9_external_secondary.toml |
| KRAS | phase_2_expansion | medium | C:\Users\Wesley Capucho\Documents\IA dos números primos\configs\multigene\kras\public_kras_benchmark.toml | C:\Users\Wesley Capucho\Documents\IA dos números primos\configs\multigene\kras\public_kras_real.toml | C:\Users\Wesley Capucho\Documents\IA dos números primos\configs\multigene\kras\public_kras_external_clinical.toml | C:\Users\Wesley Capucho\Documents\IA dos números primos\configs\multigene\kras\public_kras_external_secondary.toml |

## Data Tasks

| gene | rollout_phase | artifact | path | status |
| --- | --- | --- | --- | --- |
| TP53 | phase_1_immediate | training_clinvar_like | C:\Users\Wesley Capucho\Documents\IA dos números primos\data\raw\multigene\tp53\tp53_clinvar_training.tsv | placeholder_created |
| TP53 | phase_1_immediate | external_clinical | C:\Users\Wesley Capucho\Documents\IA dos números primos\data\raw\multigene\tp53\tp53_clinical_external.tsv | placeholder_created |
| TP53 | phase_1_immediate | external_secondary | C:\Users\Wesley Capucho\Documents\IA dos números primos\data\raw\multigene\tp53\tp53_secondary_external.tsv | placeholder_created |
| TP53 | phase_1_immediate | gnomad_annotations | C:\Users\Wesley Capucho\Documents\IA dos números primos\data\raw\gnomad\tp53_missense_annotations.tsv | placeholder_created |
| TP53 | phase_1_immediate | mavedb_scores | C:\Users\Wesley Capucho\Documents\IA dos números primos\data\raw\mavedb\tp53_function_scores.csv | placeholder_created |
| GCK | phase_2_expansion | training_clinvar_like | C:\Users\Wesley Capucho\Documents\IA dos números primos\data\raw\multigene\gck\gck_clinvar_training.tsv | placeholder_created |
| GCK | phase_2_expansion | external_clinical | C:\Users\Wesley Capucho\Documents\IA dos números primos\data\raw\multigene\gck\gck_clinical_external.tsv | placeholder_created |
| GCK | phase_2_expansion | external_secondary | C:\Users\Wesley Capucho\Documents\IA dos números primos\data\raw\multigene\gck\gck_secondary_external.tsv | placeholder_created |
| GCK | phase_2_expansion | gnomad_annotations | C:\Users\Wesley Capucho\Documents\IA dos números primos\data\raw\gnomad\gck_missense_annotations.tsv | placeholder_created |
| GCK | phase_2_expansion | mavedb_scores | C:\Users\Wesley Capucho\Documents\IA dos números primos\data\raw\mavedb\gck_function_scores.csv | placeholder_created |
| PTEN | phase_2_expansion | training_clinvar_like | C:\Users\Wesley Capucho\Documents\IA dos números primos\data\raw\multigene\pten\pten_clinvar_training.tsv | placeholder_created |
| PTEN | phase_2_expansion | external_clinical | C:\Users\Wesley Capucho\Documents\IA dos números primos\data\raw\multigene\pten\pten_clinical_external.tsv | placeholder_created |
| PTEN | phase_2_expansion | external_secondary | C:\Users\Wesley Capucho\Documents\IA dos números primos\data\raw\multigene\pten\pten_secondary_external.tsv | placeholder_created |
| PTEN | phase_2_expansion | gnomad_annotations | C:\Users\Wesley Capucho\Documents\IA dos números primos\data\raw\gnomad\pten_missense_annotations.tsv | placeholder_created |
| PTEN | phase_2_expansion | mavedb_scores | C:\Users\Wesley Capucho\Documents\IA dos números primos\data\raw\mavedb\pten_function_scores.csv | placeholder_created |
| MSH2 | phase_2_expansion | training_clinvar_like | C:\Users\Wesley Capucho\Documents\IA dos números primos\data\raw\multigene\msh2\msh2_clinvar_training.tsv | placeholder_created |
| MSH2 | phase_2_expansion | external_clinical | C:\Users\Wesley Capucho\Documents\IA dos números primos\data\raw\multigene\msh2\msh2_clinical_external.tsv | placeholder_created |
| MSH2 | phase_2_expansion | external_secondary | C:\Users\Wesley Capucho\Documents\IA dos números primos\data\raw\multigene\msh2\msh2_secondary_external.tsv | placeholder_created |
| MSH2 | phase_2_expansion | gnomad_annotations | C:\Users\Wesley Capucho\Documents\IA dos números primos\data\raw\gnomad\msh2_missense_annotations.tsv | placeholder_created |
| MSH2 | phase_2_expansion | mavedb_scores | C:\Users\Wesley Capucho\Documents\IA dos números primos\data\raw\mavedb\msh2_function_scores.csv | placeholder_created |
| F9 | phase_2_expansion | training_clinvar_like | C:\Users\Wesley Capucho\Documents\IA dos números primos\data\raw\multigene\f9\f9_clinvar_training.tsv | placeholder_created |
| F9 | phase_2_expansion | external_clinical | C:\Users\Wesley Capucho\Documents\IA dos números primos\data\raw\multigene\f9\f9_clinical_external.tsv | placeholder_created |
| F9 | phase_2_expansion | external_secondary | C:\Users\Wesley Capucho\Documents\IA dos números primos\data\raw\multigene\f9\f9_secondary_external.tsv | placeholder_created |
| F9 | phase_2_expansion | gnomad_annotations | C:\Users\Wesley Capucho\Documents\IA dos números primos\data\raw\gnomad\f9_missense_annotations.tsv | placeholder_created |
| F9 | phase_2_expansion | mavedb_scores | C:\Users\Wesley Capucho\Documents\IA dos números primos\data\raw\mavedb\f9_function_scores.csv | placeholder_created |
| KRAS | phase_2_expansion | training_clinvar_like | C:\Users\Wesley Capucho\Documents\IA dos números primos\data\raw\multigene\kras\kras_clinvar_training.tsv | placeholder_created |
| KRAS | phase_2_expansion | external_clinical | C:\Users\Wesley Capucho\Documents\IA dos números primos\data\raw\multigene\kras\kras_clinical_external.tsv | placeholder_created |
| KRAS | phase_2_expansion | external_secondary | C:\Users\Wesley Capucho\Documents\IA dos números primos\data\raw\multigene\kras\kras_secondary_external.tsv | placeholder_created |
| KRAS | phase_2_expansion | gnomad_annotations | C:\Users\Wesley Capucho\Documents\IA dos números primos\data\raw\gnomad\kras_missense_annotations.tsv | placeholder_created |
| KRAS | phase_2_expansion | mavedb_scores | C:\Users\Wesley Capucho\Documents\IA dos números primos\data\raw\mavedb\kras_function_scores.csv | placeholder_created |