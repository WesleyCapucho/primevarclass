# PrimeVarClass evidence summary for article and competition

- Generated at: `2026-05-11T05:13:50Z`
- Git commit: `4699538052907dcc0092e34bf5b1abf36295cf6e`
- Evidence run: `Jovem Cientista BRCA Real Evidence Quick Pass`
- Canonical release assets: `https://github.com/WesleyCapucho/primevarclass/releases/tag/data-artifacts-2026-05-11`

## What was validated

- Training variants: `869`
- External validation variants: `836`
- Total benchmarked variants: `1705`
- External cohorts: `4`
- Publication readiness: `95%`
- Validation lock: `94%`
- Claim strength: `98%` (`strong`)
- External robustness: `75%`
- Targeted automated tests: `35/35` passed

## Best external results by cohort

- bridges_like_external_validation_brca1: external_predictors_only__logistic_regression | AUC-ROC=0.5904, AUC-PR=0.1782, MCC=0.0923, n=168
- bridges_like_external_validation_brca2: hybrid__logistic_regression | AUC-ROC=0.7509, AUC-PR=0.1539, MCC=0.1612, n=289
- clinvar_expert_external_validation_brca1: gene_balanced_specialist | AUC-ROC=0.9223, AUC-PR=0.8640, MCC=0.6170, n=204
- clinvar_expert_external_validation_brca2: biochemical_only__logistic_regression | AUC-ROC=0.7764, AUC-PR=0.5427, MCC=0.4173, n=175

## Evidence scorecard

- Publication readiness: 95.0% (ready) - 5 cohorts, 4 external cohorts
- Validation lock: 94.0% (ready) - claim=strong; translational pilot=True
- Claim strength: 98.0% (strong) - hybrid_plus_external__logistic_regression
- External robustness: 75.0% (partial) - pooled calibration/discrimination support with remaining calibration-safety gap
- Cohort independence: 100.0% (ready) - 0% train/external overlap in frozen cohorts
- Baseline and ablation: 74.0% (partial) - needs final ablation narrative and full-campaign confirmation
- Targeted automated tests: 100.0% (passed) - 35/35 targeted tests passed in 797.6s

## Automated test evidence

- targeted_core_ingestion_tests: passed, 13 tests, 2.927s
- targeted_scientific_modules_tests: passed, 8 tests, 1.334s
- targeted_study_benchmark_tests: passed, 9 tests, 670.078s
- targeted_api_operational_tests_fixed: passed, 5 tests, 123.264s

## Main strengths for the article

- The platform now has reproducible training and external validation on frozen, independent BRCA cohorts.
- Cohort independence is locked at 100%, with no train/external variant overlap in the audited run.
- The central prime-aware hybrid claim is strong in the current quick-pass evidence package.
- The API and user-facing documentation endpoints are covered by targeted operational tests.
- The GitHub repository and Release assets separate source code from large scientific artifacts with checksums.

## Honest gaps to close before a top-tier paper

- BRCA1 LOVD remains the weakest holdout: best AUC-ROC `0.5904`.
- BRCA1 LOVD selected-model errors: `32` errors across `168` variants.
- gnomAD coverage in the weak BRCA1 LOVD cohort: `36.31%`.
- MaveDB coverage in the weak BRCA1 LOVD cohort: `6.55%`.
- External robustness is still `75%`, mainly limited by calibration safety and cross-cohort heterogeneity.
- Baseline/ablation coverage is `74%`; this needs a final ablation narrative before a high-impact submission.
- The full unittest suite exceeded the interactive time budget and should be run as sharded CI jobs instead of one monolithic local command.

## Recommended next experimental package

- Run the full BRCA campaign with 200 bootstraps and multiple model families overnight or in CI/HPC.
- Add AlphaMissense target-gene subsets to improve weak BRCA1/LOVD functional coverage.
- Calibrate external probabilities by cohort and report calibration curves, Brier score, and expected calibration error.
- Prioritize the BRCA1/LOVD false positives and false negatives for structural review and functional confirmation.
- Convert this summary, the methods package, and the manuscript tables into the LaTeX paper scaffold after the full campaign is locked.

## Output files

- Scorecard: `primevarclass_jovem_cientista_evidence_20260511\competition_evidence_scorecard.csv`
- Best external metrics: `primevarclass_jovem_cientista_evidence_20260511\competition_external_best_metrics.csv`
- Test matrix: `primevarclass_jovem_cientista_evidence_20260511\competition_test_matrix.csv`
