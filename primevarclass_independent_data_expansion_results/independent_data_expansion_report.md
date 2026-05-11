# Independent Real-Data Expansion

- Target genes: BRCA1, BRCA2, TP53, PTEN, MSH2, KRAS, GCK, F9
- Public/independent databases mapped: 16
- Supported ingestion presets: 16/16
- Automatable or semi-automatable sources: 14
- Connector/template readiness: 100%
- Locally staged line-level sources: 4/16
- Independent data expansion readiness: 94%

## Critical sources

- ClinVar; ClinGen Evidence Repository; BRCA Exchange / ENIGMA; gnomAD; MaveDB

## High-value expansion sources

- AlphaMissense; UniProt; AlphaFold DB; RCSB PDB; CIViC; cBioPortal Datahub; NCI Genomic Data Commons

## Validation plan

- 01_sync_freeze: Download or stage every source into a versioned, hashed local release. Success: Manifest has source URL, release, hash, row count, schema preset, and access terms.
- 02_supervised_training: Train only on allowed clinical-label cohorts and separate expert/newer releases. Success: Training labels are release-frozen and leakage checks pass against external holdouts.
- 03_independent_validation: Evaluate held-out expert, BRCA-specific, locus-specific, and prospective release cohorts. Success: AUC/PR/MCC/calibration hold across sources and genes without training contamination.
- 04_functional_mechanistic_validation: Triangulate predictions with MAVE, structural, protein, and quantum evidence. Success: High-risk predictions show consistent functional/structural signal or explainable disagreement.
- 05_translational_generalization: Test disease breadth and actionability without using actionability as pathogenicity labels. Success: Cancer, disease, and drug-evidence layers improve prioritization and reporting traceability.
- 06_prospective_lock: Lock a model, wait for new public releases, then evaluate unseen variants prospectively. Success: Pre-registered endpoints pass on variants absent from the locked training timestamp.

## Claim boundary

This package expands real-data readiness and source interoperability. It does not by itself prove clinical validity. Strong claims still require frozen independent benchmarks, prospective validation, and functional/structural confirmation for prioritized targets.