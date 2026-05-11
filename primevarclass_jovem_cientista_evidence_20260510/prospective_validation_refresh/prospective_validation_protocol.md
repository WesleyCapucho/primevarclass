# PrimeVarClass Prospective and Experimental Validation Protocol

- Generated at: `2026-05-11T00:15:09Z`
- Prospective validation readiness: `88%`
- Experimental confirmation completion: `0%`
- Final scientific proof cap: `88%`

## Locked gates

- Frozen independent/prospective benchmark: 94% (ready_for_next_release_lock) - Freeze the next public ClinVar/gnomAD/MaveDB release before model refit and score it once without retuning.
- Row-level gnomAD/MaveDB public annotation: 98% (strong_with_coordinate_exceptions) - Resolve remaining coordinate exceptions and complete VRS reconciliation for publication-grade variant identity.
- BRCA1 xTB/DFT/VQE/MD execution with real engines: 92% (triage_executed_needs_reviewed_controls) - Upgrade automated geometry QC into expert protonation/domain review plus DFT/OpenMM and docking controls.
- Orthogonal functional confirmation: 68% (lab_required) - Run HDR/SGE, transcriptional, enzymatic, or stability assays for the top predicted variants in an independent lab.
- Structural experimental confirmation: 74% (computational_triage_ready_lab_required) - Confirm selected structural mechanisms with biophysical assays, binding readouts, reviewed mutant models or experimental structures.
- Therapeutic translation and drug-discovery claim: 45% (hypothesis_only) - Only make therapeutic claims after binding, rescue, toxicity, and disease-relevant cellular evidence.

## Execution rule

- Freeze public-source releases and model parameters before scoring the next independent/prospective cohort.
- Report all variants, not only winners, and preserve failure modes as part of the scientific record.
- Treat computational outputs as prioritization until orthogonal functional or structural experiments confirm the mechanism.

## Cohort lock plan

- PVC-PROSPECTIVE-CLINVAR-NEXT-RELEASE: primary prospective temporal validation | ready_to_lock | primary endpoint: Pathogenic/likely pathogenic vs benign/likely benign discrimination
- PVC-PROSPECTIVE-BRCA-EXCHANGE-TEMPORAL: BRCA-focused independent update | ready_to_lock | primary endpoint: BRCA-specific concordance, precision at top-K pathogenic predictions and calibration
- PVC-BLINDED-MULTIGENE-HOLDOUT: generalization validation | ready_to_lock | primary endpoint: Cross-gene AUROC/AUPRC, MCC, balanced accuracy and calibration
- PVC-MAVEDB-FUNCTIONAL-HOLDOUT: orthogonal functional validation | ready_to_lock | primary endpoint: Concordance with quantitative functional effect and rank enrichment
- PVC-GNOMAD-POPULATION-CONTROL: population constraint and benign-enrichment control | ready_to_lock | primary endpoint: Risk-score depletion among common tolerated variation and enrichment among constrained regions
- PVC-PARTNER-SHADOW-MODE: real-world translational shadow validation | partner_required | primary endpoint: Operational concordance, failure-mode taxonomy and clinical/research usability

## Experimental confirmation criteria

- BRCA1_HDR_SGE: BRCA1 and BRCA DNA-repair variants | HDR/SGE functional score, RAD51 foci, protein stability and localization
- TP53_TRANSCRIPTION: TP53 | Transactivation/luciferase response-element panel and protein abundance
- PTEN_PHOSPHATASE_AKT: PTEN | Lipid/protein phosphatase activity, pAKT suppression and localization rescue
- MSH2_MMR: MSH2 | Mismatch-repair reporter, MSI rescue, MSH6 interaction and protein stability
- KRAS_GTPASE_MAPK: KRAS | GTP loading/hydrolysis, effector binding and ERK/MAPK pathway output
- GCK_ENZYMATIC: GCK | Glucokinase kinetics, thermal stability and glucose-response effect
- F9_COAGULATION: F9 | FIX activity, secretion/antigen level and activation/coagulation readout
- STRUCTURAL_BIOPHYSICS: Any prioritized structural mechanism | DSF/nanoDSF/CD/SEC-MALS, SPR/BLI/ITC, HDX-MS, cryo-EM/X-ray/NMR when feasible
- COMPUTATIONAL_REPRODUCIBILITY: All PrimeVarClass prospective runs | Frozen model hash, feature schema, source checksums, thresholds, environment and command log

## Blinded partner handoff

- Handoff targets generated: `24`
- Blinded IDs must be used until raw assay/QC outputs are sealed.
- Therapeutic claims remain hypothesis-only until binding, rescue, toxicity and disease-relevant cellular evidence are complete.