# AlphaMissense priority enrichment package

- Generated at: `2026-05-11T15:29:06Z`
- Priority targets: `50`
- Coordinate-ready targets: `15` (`30.0%`)
- Local AlphaMissense subset exists: `False`
- Local subset coverage: `0.0%`
- Status: `ready_to_extract`

## Why this matters

- AlphaMissense is an independent functional predictor and is especially valuable for persistent BRCA1/LOVD errors with missing MAVE evidence.
- This package avoids downloading large files automatically; it creates exact target lists and a streaming extraction command.
- Coordinate-ready targets can be extracted directly from the official hg38 table. Protein-only targets remain useful for manual curation or coordinate resolution.

## Next action

- Run the generated PowerShell extractor or provide a local AlphaMissense subset, then rerun this package.

## Output files

- Protein targets: `primevarclass_jovem_cientista_evidence_20260511\alphamissense_priority_enrichment\alphamissense_priority_protein_targets.tsv`
- Coordinate targets: `primevarclass_jovem_cientista_evidence_20260511\alphamissense_priority_enrichment\alphamissense_priority_coordinate_targets.csv`
- Matched coverage: `primevarclass_jovem_cientista_evidence_20260511\alphamissense_priority_enrichment\alphamissense_priority_matched_coverage.csv`
- Missing targets: `primevarclass_jovem_cientista_evidence_20260511\alphamissense_priority_enrichment\alphamissense_priority_missing_targets.csv`
- Source config: `primevarclass_jovem_cientista_evidence_20260511\alphamissense_priority_enrichment\alphamissense_priority_source_config.toml`
- Extractor script: `primevarclass_jovem_cientista_evidence_20260511\alphamissense_priority_enrichment\extract_priority_alphamissense.ps1`
