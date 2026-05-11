# Locked calibration holdout package

- Generated at: `2026-05-11T15:02:54Z`
- Candidate: `hybrid_plus_external__logistic_regression`
- Baseline: `external_predictors_only__logistic_regression`
- Split algorithm: `stratified_sha256_prime_seed`
- Prime seed: `104729`
- Held-out test variants: `417`
- Raw test safety vs baseline: `50%`
- Locked calibrated test safety vs baseline: `100%`
- Locked safety gain: `50%`
- Mean locked Brier improvement: `0.0506`
- Mean locked ECE improvement: `0.1232`

## Scientific interpretation

- The calibration intercept and decision thresholds are fitted only on the locked calibration split.
- Reported Brier, ECE, MCC and accuracy are computed on disjoint held-out test variants.
- The prime seed is used for deterministic, reproducible splitting; it is an auditability device, not a standalone biological claim.
- A larger prospective holdout remains required before making deployment-grade clinical claims.

## Cohort-level locked test summary

- bridges_like_external_validation_brca1: n_test=84, locked ECE=0.0946, baseline ECE=0.3691, locked Brier=0.1316, baseline Brier=0.2492, locked MCC=0.1167.
- bridges_like_external_validation_brca2: n_test=144, locked ECE=0.0254, baseline ECE=0.4577, locked Brier=0.0376, baseline Brier=0.2570, locked MCC=0.2211.
- clinvar_expert_external_validation_brca1: n_test=102, locked ECE=0.0992, baseline ECE=0.1338, locked Brier=0.1906, baseline Brier=0.2329, locked MCC=0.4243.
- clinvar_expert_external_validation_brca2: n_test=87, locked ECE=0.0477, baseline ECE=0.2504, locked Brier=0.1169, baseline Brier=0.2292, locked MCC=0.4340.

## Output files

- Summary: `primevarclass_jovem_cientista_evidence_20260511\locked_calibration_holdout\locked_calibration_holdout_summary.csv`
- Assignments: `primevarclass_jovem_cientista_evidence_20260511\locked_calibration_holdout\locked_calibration_holdout_assignments.csv`
- Calibration bins: `primevarclass_jovem_cientista_evidence_20260511\locked_calibration_holdout\locked_calibration_holdout_bins.csv`
- Error queue: `primevarclass_jovem_cientista_evidence_20260511\locked_calibration_holdout\locked_calibration_holdout_error_queue.csv`
