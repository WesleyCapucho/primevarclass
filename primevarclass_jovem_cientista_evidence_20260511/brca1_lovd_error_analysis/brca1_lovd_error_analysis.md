# BRCA1 LOVD error analysis

- Generated at: `2026-05-11T05:09:35Z`
- Cohort: `bridges_like_external_validation_brca1`
- Variants analyzed: `168`
- Best external metric experiment: `external_predictors_only__logistic_regression`
- Best external AUC-ROC: `0.5904`
- Best external MCC: `0.0923`
- Selected model for error inspection: `external_predictors_only__logistic_regression`
- Selected-model errors at threshold 0.5: `32`
- False positives: `15`
- False negatives: `17`

## Label balance

- Label 0: 147 variants (87.5%).
- Label 1: 21 variants (12.5%).

## External evidence coverage in this cohort

- gnomAD AF coverage: `36.31%`.
- MaveDB score coverage: `6.55%`.

## Interpretation

- BRCA1 LOVD is the weakest BRCA holdout in the current campaign and should be treated as a priority error-analysis cohort.
- The low MaveDB coverage in this cohort suggests that some errors may be driven by limited functional evidence rather than model failure alone.
- The next scientific step is to enrich these variants with AlphaMissense, reviewed structural context and manual class-balance inspection.
- This analysis strengthens the competition dossier because it shows the platform does not hide weak cases; it identifies them and turns them into testable next steps.

## Output files

- Model error summary: `primevarclass_jovem_cientista_evidence_20260511\brca1_lovd_error_analysis\brca1_lovd_model_error_summary.csv`
- Selected-model errors: `primevarclass_jovem_cientista_evidence_20260511\brca1_lovd_error_analysis\brca1_lovd_selected_model_errors.csv`
- All model errors: `primevarclass_jovem_cientista_evidence_20260511\brca1_lovd_error_analysis\brca1_lovd_all_model_errors.csv`
- Feature coverage: `primevarclass_jovem_cientista_evidence_20260511\brca1_lovd_error_analysis\brca1_lovd_feature_coverage.json`
