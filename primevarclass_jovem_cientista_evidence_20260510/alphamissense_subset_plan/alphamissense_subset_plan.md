# AlphaMissense subset plan

- Generated at: `2026-05-11T00:11:12Z`
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

Local extractor prepared:

```powershell
py -3.14 scripts\extract_alphamissense_subset.py `
  --alphamissense-input https://storage.googleapis.com/dm_alphamissense/AlphaMissense_hg38.tsv.gz `
  --targets primevarclass_jovem_cientista_evidence_20260510\multigene_annotation_enrichment_refresh\multigene_variant_annotation_matrix.csv `
  --output data\raw\alphamissense\target_gene_alphamissense.tsv
```

For a first smoke test, add `--max-lines 1000000` or use a small local slice of the official file. For the final publication-grade subset, run without `--max-lines` in a long session or cloud/HPC environment.

## Output files

- Source config template: `primevarclass_jovem_cientista_evidence_20260510\alphamissense_subset_plan\alphamissense_target_gene_source_config.toml`
