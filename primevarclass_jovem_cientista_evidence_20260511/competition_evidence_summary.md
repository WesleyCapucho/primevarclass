# PrimeVarClass evidence summary for article and competition

- Generated at: `2026-05-15T16:50:16Z`
- Git commit: `2964c1e91f4e60d2d7b8af854510262924451421`
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
- Diagnostic calibration safety: `50%` -> `100%`
- Locked calibration holdout safety: `50%` -> `100%` on `417` held-out variants
- Competition readiness: `93.1%`
- AlphaMissense priority staging: `30.0%` coordinate-ready; `100.0%` local coverage
- AlphaMissense priority overlay: best AUC-ROC `0.973333`; support rate `92.0%`; discordance hypotheses `4`
- Targeted automated tests: `39/39` passed

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
- Calibration rescue: 100.0% (ready) - safety 50% -> 100%
- Locked calibration holdout: 100.0% (ready) - heldout n=417; safety 50% -> 100%
- Competition readiness: 93.1% (ready) - paper 91.1%; priority variants 50
- AlphaMissense priority staging: 100.0% (ready_to_benchmark) - targets 50; local coverage 100.0%; support 92.0%
- AlphaMissense priority benchmark: 97.3% (priority_overlay_evaluated) - best=AlphaMissense priority overlay; discordance hypotheses=4
- Cohort independence: 100.0% (ready) - 0% train/external overlap in frozen cohorts
- Baseline and ablation: 74.0% (partial) - needs final ablation narrative and full-campaign confirmation
- Targeted automated tests: 100.0% (passed) - 39/39 targeted tests passed in 799.6s

## Automated test evidence

- targeted_core_ingestion_tests: passed, 13 tests, 2.927s
- targeted_scientific_modules_tests: passed, 8 tests, 1.334s
- targeted_study_benchmark_tests: passed, 9 tests, 670.078s
- targeted_api_operational_tests_fixed: passed, 5 tests, 123.264s
- targeted_calibration_rescue_tests: passed, 1 tests, 0.711s
- targeted_locked_calibration_holdout_tests: passed, 1 tests, 0.959s
- targeted_competition_readiness_tests: passed, 1 tests, 0.15s
- targeted_alphamissense_enrichment_tests: passed, 1 tests, 0.169s

## Main strengths for the article

- The platform now has reproducible training and external validation on frozen, independent BRCA cohorts.
- Cohort independence is locked at 100%, with no train/external variant overlap in the audited run.
- The central prime-aware hybrid claim is strong in the current quick-pass evidence package.
- The API and user-facing documentation endpoints are covered by targeted operational tests.
- A new diagnostic calibration-rescue package shows that simple cohort-level recalibration can close the calibration-safety gap in the audited BRCA quick pass.
- A locked calibration holdout now separates calibration/threshold fitting from held-out test evaluation using a deterministic prime-seeded split.
- A competition-readiness package now maps allowed scientific claims, paper sections, priority variants and the next experimental strategy.
- An AlphaMissense priority-staging package now creates exact target lists, a safe streaming extraction command, priority benchmark metrics and discordant functional hypotheses for persistent BRCA1/LOVD variants.
- The GitHub repository and Release assets separate source code from large scientific artifacts with checksums.

## Honest gaps to close before a top-tier paper

- BRCA1 LOVD remains the weakest holdout: best AUC-ROC `0.5904`.
- BRCA1 LOVD selected-model errors: `32` errors across `168` variants.
- gnomAD coverage in the weak BRCA1 LOVD cohort: `36.31%`.
- MaveDB coverage in the weak BRCA1 LOVD cohort: `6.55%`.
- External robustness is still `75%`; diagnostic recalibration and locked holdout both support `100%` calibration safety, but this must be repeated in a larger blinded/prospective holdout.
- Locked holdout status is `ready` with `57` persistent focus-cohort test errors; the next step is a larger blinded/prospective holdout.
- AlphaMissense priority coverage is `100.0%`; priority-overlay benchmark status is `priority_overlay_evaluated`. The remaining step is rerunning the full BRCA benchmark with this predictor before claiming full-cohort functional-predictor validation.
- Persistent BRCA1/LOVD errors after calibration: `64`.
- Baseline/ablation coverage is `74%`; this needs a final ablation narrative before a high-impact submission.
- The full unittest suite exceeded the interactive time budget and should be run as sharded CI jobs instead of one monolithic local command.

## Recommended next experimental package

- Run the full BRCA campaign with 200 bootstraps and multiple model families overnight or in CI/HPC.
- Add AlphaMissense target-gene subsets to improve weak BRCA1/LOVD functional coverage.
- Expand the locked calibration protocol to the full BRCA campaign and report calibration curves, Brier score, expected calibration error and decision thresholds.
- Promote the locked holdout protocol into a frozen prospective validation plan with no post-hoc threshold changes.
- Prioritize the BRCA1/LOVD false positives and false negatives for structural review and functional confirmation.
- Convert this summary, the methods package, and the manuscript tables into the LaTeX paper scaffold after the full campaign is locked.

## Output files

- Scorecard: `primevarclass_jovem_cientista_evidence_20260511\competition_evidence_scorecard.csv`
- Best external metrics: `primevarclass_jovem_cientista_evidence_20260511\competition_external_best_metrics.csv`
- Test matrix: `primevarclass_jovem_cientista_evidence_20260511\competition_test_matrix.csv`
- First-place strategy: `primevarclass_jovem_cientista_evidence_20260511\competition_first_place_strategy.md`
