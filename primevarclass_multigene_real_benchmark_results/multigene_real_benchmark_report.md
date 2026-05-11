# PrimeVarClass Multigene Real Benchmark

- Generated at: `2026-04-24T05:31:12Z`
- Target genes: `TP53, PTEN, MSH2, KRAS, GCK, F9`
- Study executed: `yes`
- Training rows: `580`
- Combined external rows: `978`
- Mean gene progress: `76%`
- Overall multigene benchmark: `70%`
- Mean external balanced score: `58.7%`
- Claim strength: `67%`
- Prime signal in multigene benchmark: `55%`

## Gene progress

- TP53: progress=85%, train=100, external=264, status=validated_external_round_complete
- F9: progress=80%, train=154, external=62, status=validated_external_round_complete
- MSH2: progress=79%, train=250, external=164, status=validated_external_round_complete
- GCK: progress=77%, train=76, external=289, status=validated_external_round_complete
- PTEN: progress=77%, train=71, external=167, status=data_ready_class_balance_gap
- KRAS: progress=60%, train=39, external=32, status=data_ready_class_balance_gap

## Guardrail

- This package uses real ClinVar extraction for the selected genes.
- gnomAD and MaveDB row-level integration can still be expanded later for each gene, even though the multigene clinical benchmark is now unlocked.
- Treat the current round as a real multigene validation layer, not as final clinical deployment proof.