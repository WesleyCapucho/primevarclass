# PrimeVarClass

PrimeVarClass is a research-oriented Python project for missense variant classification using prime-number-based amino-acid encodings plus biochemical, conservation, structural, and external predictor features. The platform is BRCA-first in its strongest real benchmark today, but the core and scientific planning stack are now being opened for multigene expansion.

This repository was organized from the consolidated prototype you shared so it can evolve as a scientific software project instead of a single monolithic script.

## What is already here

- Prime-based encoding strategies: `codon`, `prime_mass`, and `hybrid`
- Parsing and validation for multigene missense variants in protein HGVS format
- Dataset curation helpers for ClinVar-like tables
- Feature engineering for biochemical, conservation, structural, and external predictor signals
- Model training with Random Forest
- Optional model zoo with Random Forest, Extra Trees, and Logistic Regression
- Cross-validation metrics, calibration tables, and exportable reports
- Multi-source ingestion from local files, SQLite, and HTTP JSON/CSV endpoints
- Study runner for publication-style benchmarking with external validation cohorts
- Biological-discovery package to turn real public data into hotspot windows, review-upgrade candidates, and hypothesis variants
- Protein-impact package to convert biological-discovery hits into proteomic/3D modeling queues, mechanism tags, assay suggestions, and prime-mechanistic rationale
- Prime-guided coupling layer to turn prime encodings into structural active-space seeds instead of leaving the prime signal as a passive score
- Validation-credibility closure package to consolidate evidence, proof layers, and remaining actions without overclaiming therapeutic readiness
- Gene-expansion package to rank the strongest next genes for multicohort and multigene scaling beyond BRCA
- Multigene-rollout package to turn gene expansion plus prime intelligence into a phased execution plan for the next real studies
- Multigene-study factory to generate per-gene study configs, benchmark scaffolds, placeholder data tables, and task sheets for the next real benchmarks
- Prime-intelligence package to quantify when the prime-number encoding truly adds internal lift, external leadership, biological alignment, and cross-gene runway
- Consensus ensemble generation from the top-ranked study experiments
- Claim-strength package to classify whether results support strong, moderate, suggestive, or insufficient comparative claims
- Validation-lock package to summarize whether a study is ready for statistical validation, submission lock, or translational pilot
- Translational-pilot package to classify demo, shadow-mode, or live-candidate readiness for laboratory rollout
- Final-mile package to turn the remaining scientific and operational blockers into a prioritized closure plan
- Real-data handoff tracker and reconciliation package to let the laboratory mark tasks as complete and have the platform validate them automatically
- Real-data handoff autofill package to scan a delivery folder, propose tracker completion automatically, and keep the reconciliation step auditável
- Real-data handoff application package to generate candidate source catalogs and a candidate study config from validated tracker entries
- Real-data candidate-promotion package to state when the candidate study config is actually ready to be promoted and rerun in a controlled public-study round
- Translational-impact package plus persistent pilot-session and feedback registry to measure adoption, operator satisfaction, and rollout readiness
- Platform-completion package to mark the software stack as complete while keeping real-data scientific validation explicitly tracked as a separate evidence layer
- Candidate public-study runner to execute a controlled rerun directly from the generated candidate config once the laboratory closes the tracker
- Scientific API for model registry inspection, variant scoring, training, and benchmark execution
- Laboratory web workbench served by FastAPI for non-programmatic use
- Optional API-key authentication, persistent user profiles, scientific teams, audit trail, release versioning, team dashboards, and job reports for institutional use
- CLI entrypoint and reusable Python package layout

## Repository layout

- `src/primevarclass/core.py`: original consolidated pipeline, now inside a package
- `src/primevarclass/data_sources.py`: connectors and integration layer for multi-source ingestion
- `src/primevarclass/source_presets.py`: presets for public-source schemas such as ClinVar, gnomAD, and MaveDB
- `src/primevarclass/cli.py`: command-line wrapper
- `data/examples/clinvar_like_brca.csv`: small example dataset
- `configs/multisource_example.toml`: example configuration for connecting multiple sources
- `configs/public_brca_example.toml`: executable public-BRCA style catalog with real-like source schemas
- `configs/public_brca_study_template.toml`: template for a paper-grade public-data study
- `configs/public_brca_benchmark_example.toml`: executable benchmark with train/external validation cohorts
- `docs/projeto.md`: scientific scope and roadmap distilled from the project document
- `docs/public_data_blueprint.md`: blueprint for training and validating with public BRCA datasets
- `docs/product_blueprint.md`: software roadmap for turning the pipeline into a laboratory-grade tool
- `src/primevarclass/study.py`: publication-style benchmark runner
- `src/primevarclass/biological_discovery.py`: hotspot, review-upgrade, and functional-hypothesis package
- `src/primevarclass/gene_expansion.py`: expansion ranking for moving beyond BRCA into broader gene panels
- `src/primevarclass/api.py`: FastAPI service for inference, training, and benchmarking
- `src/primevarclass/deployment.py`: model registry, manifests, and single-variant scoring helpers
- `tests/test_core.py`: basic smoke tests for parsing, curation, and small-model training

## Quick start

Install the package in editable mode:

```bash
pip install -e .
```

Run the demo pipeline:

```bash
primevarclass --demo --output-dir primevarclass_results_demo
```

Integrate multiple sources from a TOML catalog and train from the merged table:

```bash
primevarclass --source-config configs/multisource_example.toml --output-dir primevarclass_results_multisource
```

Only materialize the integrated raw dataset without training:

```bash
primevarclass --source-config configs/multisource_example.toml --ingest-only --output-dir primevarclass_ingestion
```

## Launch and publication readiness

Generate the scientific-publication and web-launch readiness package:

```bash
primevarclass --build-launch-readiness --output-dir primevarclass_launch_readiness_results
```

Regenerate the user manual and glossary PDFs after documentation edits:

```bash
python scripts/generate_knowledge_pdfs.py
```

Generate a private launch environment before web staging:

```bash
python scripts/prepare_launch_env.py
```

The command writes a local `.env` with a strong `PRIMEVARCLASS_API_KEY` and persistent state paths. The file is ignored by git and should not be shared in articles, repositories, screenshots, or public attachments.

The package exports a manifest, Markdown/HTML report, and CSV checklist covering scientific evidence, web deployment, operational hardening, and truth-guardrails for claims. The same audit is available in the API and workbench:

```bash
primevarclass --serve-api --host 127.0.0.1 --port 8000
```

- Workbench: `http://127.0.0.1:8000/workbench`
- Readiness API: `GET /launch/readiness`
- Export readiness package: `POST /launch/readiness/export`

For containerized staging, copy `.env.example` to `.env`, set a strong `PRIMEVARCLASS_API_KEY`, and run:

```bash
docker compose up --build
```

See `docs/scientific_publication_and_web_launch.md` for the launch runbook. Publication readiness does not equal clinical validity; independent functional, structural, and prospective confirmation remains required before strong clinical or therapeutic claims.

Expand the independent real-data plan for training, validation, functional evidence, protein structure, oncology cohorts, and translational databases:

```bash
primevarclass --build-independent-data-expansion \
  --target-gene BRCA1 --target-gene BRCA2 --target-gene TP53 --target-gene PTEN \
  --target-gene MSH2 --target-gene KRAS --target-gene GCK --target-gene F9 \
  --output-dir primevarclass_independent_data_expansion_results
```

This exports a public database registry, a training/validation plan, a gene-source matrix, and source catalog templates for ClinVar, ClinGen ERepo, BRCA Exchange/ENIGMA, gnomAD, MaveDB, AlphaMissense, UniProt, AlphaFold DB, RCSB PDB, CIViC, cBioPortal, GDC/TCGA, GWAS Catalog, Open Targets, PharmGKB, and LOVD. The package separates label sources, independent holdouts, functional evidence, structural/proteomic evidence, and translational context so additional databases strengthen the science without leaking labels or overclaiming clinical validity.

Audit the files already staged locally and generate a ready-to-review TOML for the next independent training round:

```bash
primevarclass --autostage-open-independent-sources \
  --target-gene BRCA1 --target-gene BRCA2 --target-gene TP53 --target-gene PTEN \
  --target-gene MSH2 --target-gene KRAS --target-gene GCK --target-gene F9 \
  --output-dir primevarclass_independent_open_source_autostage_results

primevarclass --build-independent-data-staging-closure \
  --independent-data-expansion-manifest-path primevarclass_independent_data_expansion_results/independent_data_expansion_manifest.json \
  --output-dir primevarclass_independent_data_staging_closure_results
```

The autostager uses open official APIs/downloads for ClinGen ERepo, UniProt, AlphaFold DB, RCSB PDB, CIViC, cBioPortal, GDC, GWAS Catalog, Open Targets, and PharmGKB. The closure then exports a local inventory, SHA-256 fingerprints, a gap plan, a PowerShell staging handoff, and `independent_ready_source_config.toml`. It is intended to separate what can be used now from what still needs download, licensing review, normalization, or full line-level expansion.

Run the public-BRCA style example with ClinVar-like, gnomAD-like, and MaveDB-like sources:

```bash
primevarclass --source-config configs/public_brca_example.toml --output-dir primevarclass_results_public_brca
```

Materialize the real-data canonical artifacts and the frozen real-study TOMLs directly from the raw public downloads:

```bash
primevarclass --prepare-real-data \
  --clinvar-variant-summary-path "C:/path/to/variant_summary.txt.gz" \
  --brca-exchange-release-path "C:/path/to/release-01-05-26.tar.gz" \
  --mavedb-dump-path "C:/path/to/mavedb-dump.20260206153444.zip" \
  --output-dir primevarclass_real_data_preparation_results
```

By default, this step now queries the official gnomAD GraphQL API directly for BRCA1/BRCA2 missense population annotations, splits ClinVar into a non-expert training cohort plus an `expert panel` holdout, and rebuilds the real benchmark with four external cohorts:

- `clinvar_expert_external_validation_brca1`
- `clinvar_expert_external_validation_brca2`
- `bridges_like_external_validation_brca1`
- `bridges_like_external_validation_brca2`

The publication benchmark also materializes three heterogeneity-aware candidates on top of the regular experiment suite:

- `gene_balanced_specialist`: picks the internally strongest experiment separately for `BRCA1` and `BRCA2`
- `hybrid_external_gene_adaptive_blend`: learns a per-gene blend between the prime/hybrid candidate and the declared external baseline using only internal cross-validated evidence
- `hybrid_external_gene_robust_blend`: uses the same per-gene blend search, but selects the weight with an internal robustness-aware criterion that balances discrimination and Brier-style calibration before the frozen external run
- `hybrid_external_gene_calibrated_blend`: takes the adaptive per-gene blend and fits an internal logistic calibrator per gene before touching the frozen external cohorts, to improve calibration leadership and robustness in expert-grade cohorts
- a multicohort aggregate evidence layer that estimates the pooled external delta with stratified bootstrap, its approximate 95% interval, and directional confidence across the frozen validation cohorts
- a high-confidence clinical holdout layer that scores how well the candidate leads specifically in expert-grade external cohorts before we claim stronger scientific support
- an external robustness package that rechecks calibration, discrimination, no-regression safety, directional sign confidence, cross-cohort stability, and pooled bootstrap support for both all-external and high-confidence clinical slices from the frozen score tables
- a claim-strength layer that now combines pooled support, effective head-to-head leadership, effective no-regression safety, and clinical credibility before assigning the final scientific-claim tier

Those candidates are exported as explicit manifests in the study output so the external benchmark can test whether gene-aware specialization improves the comparative story without leaking information from the external cohorts.

When a per-gene cohort is too small to support local cross-validated training, the `gene_balanced_specialist` now degrades gracefully to the best frozen global experiment for that gene instead of disappearing from the benchmark. The manifest marks this as `training_origin = global_fallback`, so the result stays explicit and auditable.

The adaptive and calibrated per-gene blends follow the same philosophy during candidate selection: if a gene does not have its own stable internal leaderboard yet, they can still fall back to the frozen global training leaderboard, and the manifest records that as `selection_origin = global_fallback`.

For quieter and more reproducible local execution, the tree models and permutation-importance routines now use `PRIMEVARCLASS_N_JOBS=1` by default. If you want more parallelism in a larger workstation run, set `PRIMEVARCLASS_N_JOBS` explicitly before training.

If you already have a heavy benchmark frozen on disk and only want to refresh the comparative, claim, and external-robustness packages after changing their logic, use:

```bash
primevarclass --study-config configs/public_brca_benchmark_real.toml \
  --output-dir primevarclass_study_results_real_multicohort_refined \
  --refresh-frozen-study-assessment
```

That refresh step now also regenerates the `prime_intelligence` package, which combines:

- internal prime-vs-nonprime competitiveness;
- external multicohort prime leadership;
- pairwise support against the declared baseline;
- feature-attribution evidence for prime-derived signals;
- alignment between prime displacement and the biological-discovery package;
- cross-gene runway from the expansion-ranking package.

If you already have a direct BRCA-only gnomAD table, add it as an optional override:

```bash
primevarclass --prepare-real-data \
  --clinvar-variant-summary-path "C:/path/to/variant_summary.txt.gz" \
  --brca-exchange-release-path "C:/path/to/release-01-05-26.tar.gz" \
  --mavedb-dump-path "C:/path/to/mavedb-dump.20260206153444.zip" \
  --gnomad-annotations-path "C:/path/to/gnomad_brca.tsv" \
  --output-dir primevarclass_real_data_preparation_results
```

This step rewrites the canonical real-study tables under `data/raw/...` and refreshes:

- `configs/public_brca_real.toml`
- `configs/public_brca_external_real_clinvar_expert.toml`
- `configs/public_brca_external_real_clinvar_expert_brca1.toml`
- `configs/public_brca_external_real_clinvar_expert_brca2.toml`
- `configs/public_brca_external_real.toml`
- `configs/public_brca_external_real_brca1.toml`
- `configs/public_brca_external_real_brca2.toml`
- `configs/public_brca_benchmark_real.toml`

Rank the best next genes for expansion beyond BRCA using real ClinVar + MaveDB overlap:

```bash
primevarclass --build-gene-expansion \
  --clinvar-variant-summary-path "C:/path/to/variant_summary.txt.gz" \
  --mavedb-dump-path "C:/path/to/mavedb-dump.20260206153444.zip" \
  --output-dir primevarclass_gene_expansion_results
```

Generate a biological-discovery package from an already frozen real-data manifest:

```bash
primevarclass --build-biological-discovery \
  --real-data-manifest-path "primevarclass_real_data_preparation_results/real_data_preparation_manifest.json" \
  --output-dir primevarclass_biological_discovery_results
```

This package highlights:

- mechanistic hotspot windows enriched for clinically deleterious and functionally damaging variants;
- low-review variants that deserve stronger curation priority;
- unlabeled high-risk functional hypotheses supported by MaveDB and rarity in gnomAD.

Convert biological-discovery hits into a protein-impact queue for proteomic follow-up and 3D modeling:

```bash
primevarclass --build-protein-impact \
  --biological-discovery-manifest-path "primevarclass_biological_discovery_results/biological_discovery_manifest.json" \
  --output-dir primevarclass_protein_impact_results
```

This package exports a variant triage table, a modeling queue, region-level summaries, mechanism tags, recommended assays, and a prime-mechanistic alignment score so the prime-number encoding remains visible as a mechanistic differentiator.

Generate a structural-proteomics package for local molecular dynamics and docking follow-up:

```bash
primevarclass --build-structural-proteomics \
  --protein-impact-manifest-path "primevarclass_protein_impact_results/protein_impact_manifest.json" \
  --output-dir primevarclass_structural_proteomics_results
```

This package does not claim therapeutic efficacy. It prioritizes structural hypotheses, exports target tables plus a prime-structural bridge, and creates templates for OpenMM and AutoDock Vina that must be completed with reviewed 3D coordinates, protonation states, charge states, and experimental controls before execution.

Consolidate validation credibility across statistical, biological, structural, quantum, and multigene evidence layers:

```bash
primevarclass --build-validation-credibility-closure \
  --output-dir primevarclass_validation_credibility_closure_results
```

This closure package separates software/evidence readiness from definitive scientific proof. It can mark the platform ready for stronger external validation while still blocking definitive therapeutic claims until prospective, multigene, structural, and experimental evidence is complete.

Turn gene expansion plus prime intelligence into a phased multigene rollout:

```bash
primevarclass --build-multigene-rollout \
  --gene-expansion-manifest-path "primevarclass_gene_expansion_results/gene_expansion_manifest.json" \
  --prime-intelligence-manifest-path "primevarclass_study_results_real_multicohort_robust/prime_intelligence_manifest.json" \
  --output-dir primevarclass_multigene_rollout_results
```

Generate scaffolded study configs, placeholder data tables, and task sheets for the next real genes:

```bash
primevarclass --build-multigene-study-factory \
  --multigene-rollout-manifest-path "primevarclass_multigene_rollout_results/multigene_rollout_manifest.json" \
  --output-dir primevarclass_multigene_study_factory_results
```

The workbench now exposes this multigene track directly, so the same environment can:

- build `gene expansion` from ClinVar + MaveDB;
- materialize `biological discovery` from the real-data bundle;
- plan the phased `multigene rollout`;
- scaffold the next per-gene studies while keeping the prime-number strategy visible as a first-class differentiator.

Run the benchmark-style study with a training cohort and one or more external validation cohorts:

```bash
primevarclass --study-config configs/public_brca_benchmark_example.toml --output-dir primevarclass_study_results
```

Run the advanced benchmark with multiple model families and automatic consensus:

```bash
primevarclass --study-config configs/public_brca_benchmark_advanced_example.toml --output-dir primevarclass_study_results_advanced
```

Run the unified public-study pipeline with frozen public resolution, preflight, benchmark, and execution board:

```bash
primevarclass --study-config configs/public_brca_benchmark_example.toml --public-study-run --output-dir primevarclass_public_study_run
```

This unified public-study run now also exports a translational pilot package, so the same execution can be reviewed from both the publication and laboratory-adoption perspectives.

Compare two exported studies:

```bash
primevarclass --compare-study-baseline primevarclass_study_results --compare-study-candidate primevarclass_study_results_advanced --output-dir primevarclass_study_comparison_results
```

Generate a longitudinal monitor across multiple exported studies:

```bash
primevarclass --monitor-study-dir primevarclass_study_results --monitor-study-dir primevarclass_study_results_advanced --output-dir primevarclass_longitudinal_results
```

Start the scientific API locally:

```bash
primevarclass --serve-api --host 127.0.0.1 --port 8000
```

Or:

```bash
primevarclass-api
```

Depois abra:

```text
http://127.0.0.1:8000/workbench
```

Para ativar autenticacao leve por API key antes de subir a API:

```powershell
$env:PRIMEVARCLASS_API_KEY = "sua-chave-do-laboratorio"
primevarclass --serve-api --host 127.0.0.1 --port 8000
```

Or run from Python:

```python
from primevarclass import run_full_training_pipeline

results = run_full_training_pipeline(
    input_csv_path="data/examples/clinvar_like_brca.csv",
    mode="hybrid",
    output_dir="primevarclass_results",
    keep_metadata=True,
    high_confidence_only=True,
)
```

## Notes for the research workflow

- The bundled CSV is only a small demonstration dataset for smoke testing.
- The project is intended for research support and method development, not standalone clinical decision making.
- The next major step is integrating real curated datasets and external benchmarking data under a reproducible data-ingestion workflow.

## API workflow

- `GET /health`: service health check
- `GET /auth/status`: inspect whether API-key authentication is enabled
- `GET /users/context`: inspect the active institutional profile for the current request
- `GET /users/profiles` and `POST /users/profiles`: manage persistent operator profiles
- `GET /teams/context`: inspect the active scientific team for the current request
- `GET /teams`, `POST /teams`, and `GET/POST /teams/{team_id}/members`: manage scientific teams and memberships
- `GET /analytics/team-dashboard`: inspect operational and scientific activity for the active team
- `POST /monitoring/studies/longitudinal`: build a longitudinal monitor across multiple exported studies
- `GET /jobs` and `GET /jobs/{job_id}`: inspect asynchronous operations and execution history
- `GET /jobs/{job_id}/report`: download the human-readable report for a job
- `GET /audit/events`: inspect recent audit entries
- `GET /models?model_dir=...`: inspect the saved model registry
- `POST /predict/variant`: score a single BRCA1/2 missense variant with an exported model
- `POST /predict/batch`: prioritize multiple BRCA1/2 variants in one run and return CSV plus Markdown laboratory reports
- `POST /train/source-config`: train from a TOML multi-source catalog
- `POST /jobs/train/source-config`: enqueue a training job in background
- `POST /science/independent-data-expansion`: map independent public databases for training, validation, functional, structural, and translational evidence
- `POST /science/independent-open-source-autostage`: stage open public independent sources through official APIs/downloads
- `POST /science/independent-data-staging-closure`: audit locally staged independent files and export the next training-ready source config plus gap plan
- `POST /study/run`: execute a publication-style benchmark study
- `POST /study/public-run`: execute the unified public-study pipeline with public-resolution, preflight, benchmark, and execution board
- `POST /study/preflight`: run a pre-benchmark validation pass over a study config and export a study-readiness package
- `POST /jobs/study/run`: enqueue a benchmark study in background
- `POST /jobs/study/public-run`: enqueue the unified public-study pipeline in background for long public-data runs
- `POST /study/bundle/inspect`: inspect an exported study directory and summarize scientific packages/manifests
- `POST /study/compare`: compare two exported studies and generate a formal comparison package
- `POST /releases/manifest/load`: inspect a saved data or study release manifest and audit its provenance
- `POST /public-sources/catalog/inspect`: inspect a multi-source public catalog and measure release/version coverage
- Public catalog inspection now also returns a source-by-source sync plan with official entrypoints and recommended automation strategy.
- `POST /public-sources/catalog/bootstrap` now generates a bootstrap bundle with manifest, guide, and PowerShell script for staging public sources locally.
- `POST /public-sources/catalog/bootstrap/execute`: run the bootstrap in controlled mode, with `dry_run` support and persistent sync manifests
- `POST /public-sources/catalog/resolve`: resolve a public-source catalog to staged artifacts or retained local versioned files and export a frozen TOML
- `GET /public-sources/catalog/bootstrap/history`: inspect sync history, latest source status, and benchmark readiness derived from bootstrap runs
- `POST /study/public-config/resolve`: generate a resolved study config that points each cohort to frozen public-source TOMLs
- The public-study runner now closes the loop from catalog resolution to execution board generation, so the same workbench can move from public-data staging to a benchmark-ready package without manual path editing.
- Study benchmarks now also export a comparative-evidence package, making it easier to inspect cohort-by-cohort support for prime/hybrid gains against the declared baseline.
- Study benchmarks now also export a claim-strength package, making the strength of the scientific claim explicit instead of implicit.
- Study benchmarks now also export a cohort-independence audit, so train/external overlap and label-conflict risks are visible before final interpretation.
- Study benchmarks now also export a validation-lock package, so readiness for statistical validation, submission lock, and translational pilot can be audited directly.
- Unified public-study runs now also export a translational-pilot package, making demo-mode, shadow-mode, and live-candidate readiness explicit for laboratory rollout planning.
- Unified public-study runs now also export a final-mile package, making the remaining blockers toward real-data execution, final evidence, and submission closeout explicit.
- Public-study resolution now also exports a handoff tracker CSV and a reconciliation package, so data-acquisition tasks can be closed in a machine-readable way.
- Public-study resolution can now also consume a `delivery_dir` and export a handoff-autofill package, turning a lab delivery folder into a proposed tracker update before reconciliation.
- Public-study resolution now also exports a candidate study config derived from validated handoff entries, reducing manual TOML editing before the next real-data run.
- Public-study resolution now also exports a candidate-promotion package, making explicit whether the generated candidate config is only reviewable or already ready for a controlled rerun.
- Unified public-study runs now also export a translational-impact package, while the API/workbench can persist pilot sessions and field feedback in a machine-readable registry.
- The API, CLI, and workbench now also expose a dedicated candidate public-study rerun path, so the generated candidate config can move into a guarded evidence round without manual orchestration.
- `GET /roadmap/progress`: inspect the macro-stage progress toward the final publication-grade product
- `GET /workbench`: laboratory web interface for interactive use

Example variant-scoring payload:

```json
{
  "model_dir": "primevarclass_results_demo/models",
  "experiment": "hybrid_plus_external",
  "gene": "BRCA1",
  "hgvs_p": "p.Cys61Gly",
  "feature_payload": {
    "phylop": 7.2,
    "gerp": 5.8,
    "siphy": 12.4,
    "revel": 0.94
  }
}
```

Example batch-screening payload:

```json
{
  "model_dir": "primevarclass_results_public_brca/models",
  "experiment": "hybrid_plus_external",
  "variants": [
    {
      "sample_id": "BRCA1_001",
      "gene": "BRCA1",
      "hgvs_p": "p.Cys61Gly",
      "feature_payload": {
        "phylop": 7.2,
        "gerp": 5.8,
        "siphy": 12.4,
        "revel": 0.94
      }
    },
    {
      "sample_id": "BRCA2_002",
      "gene": "BRCA2",
      "hgvs_p": "p.Gly2508Ser",
      "feature_payload": {
        "phylop": 5.9,
        "gerp": 4.7,
        "siphy": 8.2,
        "revel": 0.88
      }
    }
  ]
}
```

## Multi-source data architecture

- `cohort` sources contribute labeled variants for model training.
- `annotation` sources are merged on keys such as `gene` and `hgvs_p` to enrich the cohort with external features.
- Source catalogs are configured in TOML, so we can connect ClinVar-like tables, local SQLite databases, and HTTP endpoints without rewriting the training code.
- Public-source presets normalize real-world schemas into the canonical training table and push external scientific signals into `feature_*` columns.

## Benchmark workflow

- `study` configs define one training cohort and one or more external validation cohorts.
- PrimeVarClass can train the ablation matrix with one or more model families, then reuse those trained models on each external cohort.
- The study runner can build a consensus ensemble from the top-ranked internal experiments and score it on external cohorts.
- Outputs include internal metrics, repeated holdout summaries, feature-set leaderboards, model-family summaries, consensus manifests, external evaluation tables, pairwise delta-vs-baseline comparisons, claim-strength and validation-lock packages, trained models, and a text summary for manuscript drafting.

## Operations workflow

- Long-running training and study requests can now be queued in background jobs.
- Job history is persisted on disk, so the workbench can show queued, running, completed, failed, or interrupted operations.
- The workbench includes an operations panel for refreshing and inspecting recent jobs without blocking the main interface.
- The workbench now also includes a project-roadmap panel with progress bars by macro-stage, so product maturity can be tracked visually.
- When `PRIMEVARCLASS_API_KEY` is configured, protected API routes require `X-API-Key`.
- The active operator can now be identified with `X-PrimeVarClass-Profile`, backed by persistent profiles in `user_profiles.json`.
- The active scientific team can now be identified with `X-PrimeVarClass-Team`, backed by persistent teams and memberships in `teams.json`.
- Source-config ingestions now write `data_release_manifest.json` and `data_release_registry.csv` automatically when an output directory is provided.
- Data ingestions now capture per-source provenance automatically, including file hashes, SQLite database fingerprints, and HTTP response metadata with payload hashes.
- The workbench now includes a release-manifest inspector so researchers can audit provenance and artifact fingerprints directly from `/workbench`.
- Public-source catalogs now receive automatic recognition for ClinVar, gnomAD, MaveDB, and ENIGMA, with release/version coverage reports in JSON and Markdown.
- Public-source inspection now also scores schema coverage, highlighting whether each source contains the normalized columns expected for benchmark-grade use.
- Public-source bootstrap now supports controlled `dry-run` execution, persistent sync history, and source-level operational readiness for public benchmark preparation.
- MaveDB sources now become script-executable in the bootstrap when `release_version` stores a public `urn:mavedb:...`, allowing official API staging of score-set metadata and mapped variants.
- gnomAD sources now become runner-executable when the catalog points to a local exported table, allowing controlled BRCA subset extraction with a staging manifest.
- ENIGMA sources now support auditable local staging of curated import files, producing a staged copy plus manifest for institutional traceability.
- The workbench now includes actions to inspect the public catalog, generate bootstrap bundles, execute a safe dry-run, and review synchronization history directly from `/workbench`.
- Batch screening responses now include `csv_report` and `markdown_report` for immediate laboratory export.
- Publication-style studies now also export `study_scientific_dossier.md` and `study_scientific_dossier.html`.
- Publication-style studies now also export a full publication-readiness package with `publication_readiness_report.md`, `publication_readiness_report.html`, `publication_readiness_manifest.json`, and evidence tables for criteria, cohorts, public sources, artifacts, and external comparisons.
- Publication-style studies now also export `claim_strength_report.md/.html` plus CSV tables for candidate ranking, metric-by-cohort support, and head-to-head external wins versus baseline.
- Publication-style studies now also export `baseline_coverage_report.md/.html` plus CSV tables to show baseline presence, ablation coverage, and prime/hybrid gain against the declared baseline.
- Publication-style studies now also export `methods_package.md/.html` plus reproducibility tables summarizing cohorts, source provenance, and checklist items for manuscript methods.
- Publication-style studies now also export a manuscript package with `manuscript_package.md`, `manuscript_package.html`, manuscript-ready tables, and SVG figures for internal/external AUC-ROC summaries.
- Publication-style studies now also export `study_cohort_freeze_report.md/.html` plus a cohort-freeze manifest that makes it explicit when a study is still using demo/example inputs instead of real frozen public cohorts.
- Public-study resolution now also exports `study_real_data_handoff.md/.html` plus a handoff manifest and task table to show exactly which sources still need replacement, release locking or staging before the real benchmark round.
- Public-study resolution now also exports `study_real_data_candidate_promotion.md/.html` plus a manifest and CSV criteria/blockers tables to show when the generated candidate config can actually be promoted to the next public-study execution.
- Publication-style studies now also export `study_validation_lock.md/.html` plus a validation manifest that consolidates claim strength, comparative evidence, baseline coverage, readiness, and translational gates.
- Publication-style studies now also export `study_release_manifest.json` and `study_release_registry.csv` for reproducible version tracking.
- The workbench now includes a diagnostics panel for `study preflight` and `study bundle inspection`, so benchmark readiness and exported scientific packages can be reviewed visually.
- The workbench now also resolves public catalogs and whole study configs into frozen TOMLs, reducing manual path edits before a real public benchmark run.
- Study comparisons now export `study_comparison_report.md`, `study_comparison_report.html`, and paired internal/external comparison tables.
- Longitudinal monitoring exports `study_longitudinal_timeline.csv`, `study_longitudinal_report.md`, and `study_longitudinal_report.html`.
- Team dashboards aggregate jobs, audit events, and scientific outputs for the currently active team.
- Job directories now include `job.json` and `job_report.md`, while audit events are appended to `audit_events.ndjson`.
