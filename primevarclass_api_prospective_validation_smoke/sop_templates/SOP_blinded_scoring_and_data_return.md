# Blinded Scoring and Data Return

## Objective

Prevent data leakage and preserve independent validation credibility during partner execution.

## Procedure

1. PrimeVarClass generates a blinded handoff sheet with `PVC-BLIND-*` IDs.
2. The partner lab runs assays without seeing score bins, rank, predicted class or mechanistic interpretation.
3. The partner returns raw readouts, normalized effects, QC flags, replicate counts and protocol deviations.
4. The analysis team joins results to frozen scores only after raw/QC data are sealed.
5. Every failed, unmapped or discordant variant remains in the audit trail.

## Required return fields

`blinding_id`, `assay_version`, `raw_readout`, `normalized_effect`, `qc_status`, `replicate_count`, `control_pass`, `operator_blinded`, `notes`.