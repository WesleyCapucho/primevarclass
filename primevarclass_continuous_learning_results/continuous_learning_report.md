# PrimeVarClass Continuous Learning

- Generated at: 2026-04-23T22:42:21Z
- Configured public sources: 3
- Auto-sync coverage: 100%
- Script-execution coverage: 67%
- Continuous-learning readiness: 68%
- Benchmark readiness: 36%
- Live runner selected sources: clinvar_variant_summary, gnomad_brca_annotations

## Why This Matters

- The platform can now maintain a live-learning lane that syncs supported public sources, resolves staged artifacts into a runnable config, and retrains candidate models automatically.
- At the same time, the platform preserves a frozen-release lane so scientific validation, manuscripts, and high-stakes comparisons stay reproducible.

## Configured Connectors

### ClinVar

- Automation level: automatable
- Bootstrap ready now: yes
- Training role: clinical supervision and label refresh
- Scientific value: core pathogenicity supervision with review metadata
- Promotion gate: never promote directly from live updates; require locked benchmark rerun

### MaveDB

- Automation level: automatable
- Bootstrap ready now: no
- Training role: functional assay enrichment and calibration
- Scientific value: functional effect evidence for mechanistic and gene-specialist models
- Promotion gate: promote only after overlapping-gene benchmark holds or improves

### gnomAD

- Automation level: semi_automatable
- Bootstrap ready now: yes
- Training role: population rarity and background constraint annotation
- Scientific value: population baseline and rarity control for calibration
- Promotion gate: annotation-only refresh can go live; model promotion still requires benchmark lock

## Expansion Connectors

- ENIGMA: high-trust BRCA adjudication for credibility and adjudication checks (cadence: manual frozen refresh when a curated release is staged; gate: always freeze and audit before external benchmark or publication claims)
- UniProt: protein context and accession backbone for structural modules (cadence: monthly or per targeted gene refresh; gate: annotation-only until structural and performance checks pass)
- AlphaFold DB: 3D coordinate prior for residue environment and quantum targeting (cadence: per accession/model refresh after accession mapping lock; gate: never alone; use as structural enrichment for protein and quantum modules)
- RCSB PDB: experimental structural evidence and local geometry support (cadence: targeted refresh for prioritized genes and residues; gate: validation overlay only; do not treat as label supervision)
- CIViC: drug, disease, and evidence context for translational deployment (cadence: monthly or per project review cycle; gate: downstream translational layer only; never use as standalone pathogenicity labels)

## Retraining Policy

### live_label_refresh

- Sources: ClinVar, ENIGMA
- Active now: yes
- Trigger: new review statuses, expert curation, or label shifts
- Action: execute sync, resolve staged config, run candidate benchmark, and compare against frozen reference
- Promotion gate: promote only if locked external benchmark and calibration are preserved or improved

### functional_refresh

- Sources: MaveDB
- Active now: yes
- Trigger: new score set for overlapping genes or stronger assay coverage
- Action: refresh functional annotations, rebuild gene-specialist candidates, and rerank mechanistic targets
- Promotion gate: promote only after overlap-aware benchmark and assay-consistency checks

### population_refresh

- Sources: gnomAD
- Active now: yes
- Trigger: new population release or local subset refresh
- Action: refresh rarity annotations and recalibrate downstream evidence layers
- Promotion gate: annotation refresh can go live, but a new core model still requires a frozen benchmark rerun

### structure_refresh

- Sources: UniProt, AlphaFold DB, RCSB PDB
- Active now: no
- Trigger: new accession mapping, structural model, or experimental structure
- Action: refresh protein-impact and quantum prioritization without changing core labels
- Promotion gate: structural evidence strengthens interpretation; it should not alone trigger model promotion

### translational_refresh

- Sources: CIViC
- Active now: no
- Trigger: new disease, drug, or actionability evidence
- Action: refresh translational ranking, pilot prioritization, and reporting layers
- Promotion gate: never use as standalone supervision for pathogenicity classification

## Governance Lanes

### live_learning_lane

- Purpose: keep public evidence current and retrain candidate models
- Data behavior: ingest freshest staged public sources and allow frequent candidate refreshes
- Claim policy: no definitive scientific or therapeutic claims from this lane alone
- Promotion gate: must beat or match the frozen release on locked benchmarks

### frozen_release_lane

- Purpose: support manuscripts, validation packages, and external comparison
- Data behavior: use release-frozen artifacts, hashes, manifests, and locked cohort definitions
- Claim policy: all major claims and comparisons should point to this lane
- Promotion gate: immutable until a new versioned release is deliberately created

## Automation Matrix

- clinvar_variant_summary (clinvar): automation=automatable, script_ready=yes, next=Pode ser automatizada com download/API e versionamento local.
- gnomad_brca_annotations (gnomad): automation=semi_automatable, script_ready=yes, next=Pode executar recorte BRCA local a partir da tabela gnomAD ja baixada e versionada.
- mavedb_brca_scores (mavedb): automation=automatable, script_ready=no, next=Informe release_version com o URN publico do score set para habilitar sync automatico via API.