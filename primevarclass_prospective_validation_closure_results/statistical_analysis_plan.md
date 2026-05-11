# PrimeVarClass Locked Statistical Analysis Plan

## Scope

This plan governs the next independent/prospective validation run. It must be versioned before labels or partner assay results are opened.

## Frozen assets

- Model/protocol freeze target: `2026-04-30T06:04:47Z`
- Store model hash, feature schema hash, source checksums, command log, dependency lock and output manifest.
- Do not retune thresholds, feature transforms or prime-derived encodings after the cohort lock.

## Primary endpoints

- ClinVar/BRCA temporal validation: AUROC, AUPRC, MCC, balanced accuracy, calibration slope/intercept and Brier score.
- Functional validation: rank enrichment and concordance with quantitative MaveDB/wet-lab functional effect.
- Structural validation: concordance between sealed structural hypothesis and experimental stability, binding or conformational readout.

## Comparators

- PrimeVarClass full model.
- Prime-ablation model with the same non-prime features.
- Non-prime initialization/control for quantum/VQE structural prioritization where applicable.
- External predictors when locally available, such as AlphaMissense, REVEL, EVE or CADD, reported without cherry-picking.

## Inference and uncertainty

- Report 95% confidence intervals using bootstrap or paired resampling; use paired tests for comparator deltas.
- Report calibration curves, decision-curve style net benefit and precision at top-K for experimental triage.
- Stratify by gene, label confidence, evidence density, ancestry/frequency bins when population data are used, and variant domain.

## Leakage and missingness

- Exclude rows that were used for training, threshold choice or manual hypothesis tuning.
- Publish all unmapped variants, failed assays, ambiguous labels and source-coordinate exceptions.
- Any post-hoc exploratory analysis must be clearly separated from the locked primary analysis.

## Success rules

- The platform is considered prospectively credible if the frozen full model beats locked baselines on primary metrics without calibration collapse.
- The prime-number contribution is considered supported if prime-ablation or non-prime controls underperform on the same locked cohort/fragment set.
- Therapeutic claims remain hypothesis-generating until binding, rescue, toxicity and disease-relevant cellular evidence are complete.