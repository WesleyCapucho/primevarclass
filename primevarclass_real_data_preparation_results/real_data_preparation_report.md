# PrimeVarClass Real-data Preparation

- Generated at: 2026-04-16T21:11:10Z
- Workspace root: C:\Users\Wesley Capucho\Documents\IA dos números primos
- ClinVar training variants: 869
- ClinVar expert external variants: 379
- ClinVar expert BRCA1 variants: 204
- ClinVar expert BRCA2 variants: 175
- BRCA Exchange LOVD external variants: 457
- BRCA1 external variants: 168
- BRCA2 external variants: 289
- ENIGMA curated missense variants: 366
- gnomAD-style annotation rows: 6749
- MaveDB function-score rows: 11284

## Input provenance

- ClinVar input: C:\Users\Wesley Capucho\Downloads\variant_summary.txt.gz
- BRCA Exchange input: C:\Users\Wesley Capucho\Downloads\release-01-05-26.tar.gz
- MaveDB input: C:\Users\Wesley Capucho\Downloads\mavedb-dump.20260206153444.zip
- gnomAD mode: direct_api

## Canonical artifacts

- training_table: C:\Users\Wesley Capucho\Documents\IA dos números primos\data\raw\clinvar\brca_missense_variant_summary.tsv
- clinvar_expert_table: C:\Users\Wesley Capucho\Documents\IA dos números primos\data\raw\clinvar\brca_missense_expert_external.tsv
- clinvar_expert_brca1_table: C:\Users\Wesley Capucho\Documents\IA dos números primos\data\raw\clinvar\brca_missense_expert_external_brca1.tsv
- clinvar_expert_brca2_table: C:\Users\Wesley Capucho\Documents\IA dos números primos\data\raw\clinvar\brca_missense_expert_external_brca2.tsv
- external_table: C:\Users\Wesley Capucho\Documents\IA dos números primos\data\raw\brca_exchange\brca_exchange_lovd_external.tsv
- external_brca1_table: C:\Users\Wesley Capucho\Documents\IA dos números primos\data\raw\brca_exchange\brca_exchange_lovd_external_brca1.tsv
- external_brca2_table: C:\Users\Wesley Capucho\Documents\IA dos números primos\data\raw\brca_exchange\brca_exchange_lovd_external_brca2.tsv
- enigma_table: C:\Users\Wesley Capucho\Documents\IA dos números primos\data\raw\brca_exchange\enigma_brca_curated.tsv
- gnomad_table: C:\Users\Wesley Capucho\Documents\IA dos números primos\data\raw\gnomad\brca_missense_annotations.tsv
- mavedb_table: C:\Users\Wesley Capucho\Documents\IA dos números primos\data\raw\mavedb\brca_function_scores.csv

## Study configs

- training_config: C:\Users\Wesley Capucho\Documents\IA dos números primos\configs\public_brca_real.toml
- clinvar_expert_config: C:\Users\Wesley Capucho\Documents\IA dos números primos\configs\public_brca_external_real_clinvar_expert.toml
- clinvar_expert_brca1_config: C:\Users\Wesley Capucho\Documents\IA dos números primos\configs\public_brca_external_real_clinvar_expert_brca1.toml
- clinvar_expert_brca2_config: C:\Users\Wesley Capucho\Documents\IA dos números primos\configs\public_brca_external_real_clinvar_expert_brca2.toml
- external_config: C:\Users\Wesley Capucho\Documents\IA dos números primos\configs\public_brca_external_real.toml
- external_brca1_config: C:\Users\Wesley Capucho\Documents\IA dos números primos\configs\public_brca_external_real_brca1.toml
- external_brca2_config: C:\Users\Wesley Capucho\Documents\IA dos números primos\configs\public_brca_external_real_brca2.toml
- benchmark_config: C:\Users\Wesley Capucho\Documents\IA dos números primos\configs\public_brca_benchmark_real.toml

## Preparation notes

- ClinVar label conflicts removed: 0
- ClinVar expert holdout rows: 379
- BRCA Exchange LOVD overlaps removed against training cohort: 50
- BRCA Exchange release value: release-01-05-26
- gnomAD release value: gnomad_r4_graphql_2026-04-16
- gnomAD source mode: direct_api
- MaveDB selected score sets: 11
- Benchmark external cohorts: 4