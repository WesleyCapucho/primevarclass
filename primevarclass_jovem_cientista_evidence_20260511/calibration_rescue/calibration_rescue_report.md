# Calibration rescue package

- Generated at: `2026-05-11T14:51:35Z`
- Candidate: `hybrid_plus_external__logistic_regression`
- Baseline: `external_predictors_only__logistic_regression`
- Focus cohort: `bridges_like_external_validation_brca1`
- Raw calibration safety vs baseline: `50%`
- Diagnostic calibrated safety vs baseline: `100%`
- Safety gain: `50%`
- Mean Brier improvement: `0.0541`
- Mean ECE improvement: `0.1170`
- Persistent focus-cohort errors after calibration: `64`

## Scientific interpretation

- This package is a diagnostic rescue analysis, not a replacement for blinded validation.
- It estimates whether simple cohort-level recalibration can reduce calibration regressions while preserving the original discrimination evidence.
- Deployment-grade calibration still requires a locked calibration cohort or prospective holdout.

## Cohort rescue summary

- bridges_like_external_validation_brca1: raw ECE=0.3350, calibrated ECE=0.1236, raw Brier=0.2800, calibrated Brier=0.1489, best calibrated threshold=0.0500.
- bridges_like_external_validation_brca2: raw ECE=0.1635, calibrated ECE=0.0212, raw Brier=0.1011, calibrated Brier=0.0521, best calibrated threshold=0.1000.
- clinvar_expert_external_validation_brca1: raw ECE=0.1782, calibrated ECE=0.0901, raw Brier=0.2139, calibrated Brier=0.1823, best calibrated threshold=0.7000.
- clinvar_expert_external_validation_brca2: raw ECE=0.0785, calibrated ECE=0.0521, raw Brier=0.1566, calibrated Brier=0.1517, best calibrated threshold=0.4500.

## Priority error triage

- Error queue size: `313`
- Persistent focus-cohort errors: `64`
- Highest-priority persistent errors should be reviewed with AlphaMissense, MaveDB, gnomAD, structural context and functional assay feasibility.

## Output files

- Summary: `primevarclass_jovem_cientista_evidence_20260511\calibration_rescue\calibration_rescue_summary.csv`
- Thresholds: `primevarclass_jovem_cientista_evidence_20260511\calibration_rescue\calibration_rescue_thresholds.csv`
- Calibration bins: `primevarclass_jovem_cientista_evidence_20260511\calibration_rescue\calibration_rescue_bins.csv`
- Error triage queue: `primevarclass_jovem_cientista_evidence_20260511\calibration_rescue\calibration_rescue_error_triage_queue.csv`
