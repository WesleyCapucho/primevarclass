# AlphaMissense subset plan

- Generated at: `2026-05-11T05:09:35Z`
- Goal: add AlphaMissense as an independent predictor without downloading a massive full table into routine campaign runs.
- Official hg38 all-variant file: `https://storage.googleapis.com/dm_alphamissense/AlphaMissense_hg38.tsv.gz`
- Official hg38 gene-level file: `https://storage.googleapis.com/dm_alphamissense/AlphaMissense_gene_hg38.tsv.gz`
- Target local subset: `data/raw/alphamissense/target_gene_alphamissense.tsv`

## Why this is a controlled step

- The full AlphaMissense hg38 table is very large and should not be pulled automatically during an interactive session.
- For publication-grade evidence, we only need rows matching the target genes or variants in the frozen benchmarks.
- The generated source config is ready once the target subset file is created.

## Target genes

- BRCA1
- BRCA2
- TP53
- PTEN
- MSH2
- KRAS
- GCK
- F9

## Required normalized columns

- `gene`
- `hgvs_p`
- `feature_alphamissense_pathogenicity`
- `feature_alphamissense_class`
- `meta_alphamissense_transcript_id`
- `meta_genome_build`

## Recommended execution

Use a streaming extractor or a cloud/HPC job to filter the official table to the target genes or frozen benchmark variants. Do not load the full table into memory.

## Output files

- Source config template: `primevarclass_jovem_cientista_evidence_20260511\alphamissense_subset_plan\alphamissense_target_gene_source_config.toml`
