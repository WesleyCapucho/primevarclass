# AlphaMissense priority enrichment package

- Generated at: `2026-05-15T16:47:33Z`
- Priority targets: `50`
- Coordinate-ready targets: `15` (`30.0%`)
- Local AlphaMissense subset exists: `True`
- Local subset coverage: `100.0%`
- Status: `ready_to_benchmark`

## Why this matters

- AlphaMissense is an independent functional predictor and is especially valuable for persistent BRCA1/LOVD errors with missing MAVE evidence.
- This package avoids downloading large files automatically; it creates exact target lists and a streaming extraction command.
- Coordinate-ready targets can be extracted directly from the official hg38 table. Protein-only targets remain useful for manual curation or coordinate resolution.
- If local coverage remains zero after extraction, treat this as an identifier/transcript harmonization problem rather than as biological absence.
- When local coverage is available, the package also benchmarks AlphaMissense against locked PrimeVarClass scores on the priority queue and exports discordant mechanistic hypotheses.

## Next action

- Rerun the BRCA benchmark with the generated AlphaMissense source config.

## Output files

- Protein targets: `primevarclass_jovem_cientista_evidence_20260511\alphamissense_priority_enrichment\alphamissense_priority_protein_targets.tsv`
- Coordinate targets: `primevarclass_jovem_cientista_evidence_20260511\alphamissense_priority_enrichment\alphamissense_priority_coordinate_targets.csv`
- Matched coverage: `primevarclass_jovem_cientista_evidence_20260511\alphamissense_priority_enrichment\alphamissense_priority_matched_coverage.csv`
- Functional overlay: `primevarclass_jovem_cientista_evidence_20260511\alphamissense_priority_enrichment\alphamissense_priority_functional_overlay.csv`
- Priority benchmark metrics: `primevarclass_jovem_cientista_evidence_20260511\alphamissense_priority_enrichment\alphamissense_priority_benchmark_metrics.csv`
- Priority benchmark predictions: `primevarclass_jovem_cientista_evidence_20260511\alphamissense_priority_enrichment\alphamissense_priority_benchmark_predictions.csv`
- Discordance hypotheses: `primevarclass_jovem_cientista_evidence_20260511\alphamissense_priority_enrichment\alphamissense_priority_discordance_hypotheses.csv`
- Missing targets: `primevarclass_jovem_cientista_evidence_20260511\alphamissense_priority_enrichment\alphamissense_priority_missing_targets.csv`
- Source config: `primevarclass_jovem_cientista_evidence_20260511\alphamissense_priority_enrichment\alphamissense_priority_source_config.toml`
- Extractor script: `primevarclass_jovem_cientista_evidence_20260511\alphamissense_priority_enrichment\extract_priority_alphamissense.ps1`
- Protein extractor script: `primevarclass_jovem_cientista_evidence_20260511\alphamissense_priority_enrichment\extract_priority_alphamissense_aa.ps1`
- Extraction attempts audit: `primevarclass_jovem_cientista_evidence_20260511\alphamissense_priority_enrichment\alphamissense_extraction_attempts.json`
