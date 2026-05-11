# PrimeVarClass - User Manual

Version: 2026.05

This manual is written for users with different levels of experience: undergraduate students, researchers, bioinformaticians, translational teams, and scientific managers. It uses accessible language while preserving the scientific boundaries needed for responsible use.

## How to use this manual

If this is your first contact with the platform, follow this sequence. It is designed to take a new user from first access to an interpretable analysis without requiring deep expertise in bioinformatics, machine learning, or quantum computing.

- Read sections 1 to 6 to understand the platform goal, responsible-use limits, and interface organization.
- Use section 22 as a guided first-use route.
- Use section 23 as a practical map of the platform modules.
- Use section 25 whenever you are unsure how to fill a field.
- Use section 26 to interpret cards, lists, manifests, reports, and logs.
- Use section 29 before sharing results with a collaborator, reviewer, prize committee, or journal audience.
- Use the glossary whenever a technical term is unfamiliar.

## 1. What PrimeVarClass is

PrimeVarClass is a translational research platform for prioritizing, interpreting, and computationally validating missense variants. It combines clinical, population, functional, structural, proteomic, quantum, and prime-number-based mathematical evidence.

In simple terms: the platform helps turn a genetic variant into an organized scientific hypothesis. It does not produce a final clinical truth by itself. It gathers evidence, runs models, compares results, exposes gaps, and exports reproducible research artifacts.

Its core differentiators are:

- Independent real-world data sources such as ClinVar, gnomAD, MaveDB, BRCA Exchange/ENIGMA, ClinGen ERepo, UniProt, AlphaFold DB, PDB, CIViC, cBioPortal, GDC, GWAS Catalog, Open Targets, PharmGKB, and LOVD.
- Missense variant classification models.
- Prime-number-based encodings.
- Baseline and non-prime control comparisons.
- Mechanistic layers, including 3D structure, proteomics, computational chemistry, and VQE.
- Audit trails, manifests, reports, and publication packages.

## 2. What the platform can do now

The platform can:

- Classify one variant at a time.
- Prioritize variants in CSV batch mode.
- Load trained model registries.
- Run pipelines with local and public sources.
- Prepare real data for study execution.
- Map independent public databases.
- Auto-stage open public sources through official APIs.
- Generate an inventory of ready, partial, and missing data.
- Build publication-style studies.
- Run preflight checks before benchmarking.
- Compare studies and monitor longitudinal evidence.
- Generate scientific credibility reports.
- Create proteomics, 3D structure, and quantum analysis queues.
- Measure social and translational impact through pilot sessions and feedback.
- Operate in Portuguese or English.

## 3. What the platform should not do alone

PrimeVarClass should not be used as:

- An autonomous clinical report.
- A replacement for formal ACMG/AMP curation.
- A replacement for expert review by clinical geneticists, oncologists, bioinformaticians, or structural biologists.
- Definitive proof of biological mechanism.
- Definitive proof of therapeutic efficacy.
- A direct treatment recommendation system without external validation.

Always read results as research evidence. The more consequential the decision, the stronger the independent validation should be.

## 4. Interface structure

The interface is organized into modules to avoid overwhelming the user. Use one module at a time.

Main modules:

- Start: quick orientation, language, API key, and overview.
- Models: model loading and inspection.
- Prediction: single-variant and batch classification.
- Team: profiles, institutions, teams, and collaboration.
- Public data: catalogs, bootstrap, resolution, and sync history.
- Studies: publication study, preflight, inspection, comparison, and longitudinal monitoring.
- Science: gene expansion, biological discovery, proteomics, quantum, credibility, and independent databases.
- Impact: pilot sessions, translational metrics, and feedback.
- Operations: readiness, audit, jobs, and launch checks.

## 5. First access

1. Open `/workbench`.
2. Select the language with `Idioma / Language`.
3. If authentication is enabled, paste the API key.
4. Click `Save key`.
5. Go to the `Team` module.
6. Create or select your institutional profile.
7. Create or select your scientific team.
8. Go to `Models`.
9. Click `Load models`.
10. Confirm that at least one experiment is available.
11. Go to `Prediction`.
12. Run a simple test variant.
13. Read the probability, class, and evidence carefully.
14. Record any confusion or disagreement through feedback.

## 6. Core concepts for beginners

Before interpreting a result, understand five ideas:

- Missense variant: a change from one amino acid to another.
- Protein HGVS: standardized notation such as `p.Cys61Gly`.
- Model probability: a computational estimate, not a diagnosis.
- External evidence: information from independent databases or assays.
- Gap: absence of evidence; it does not mean benign evidence.

Example: a high model probability means the variant should be prioritized for review. It does not automatically mean the variant is pathogenic.

## 7. Single-variant classification

Use this flow when analyzing one variant.

1. Open `Prediction`.
2. Confirm the model directory.
3. Choose the experiment.
4. Enter the gene, for example `BRCA1`.
5. Enter the protein HGVS, for example `p.Cys61Gly`.
6. Add optional evidence if available.
7. Click `Classify variant`.
8. Read the probability.
9. Read the returned class.
10. Review interpretability fields.
11. Compare with external databases when available.
12. Record disagreements in notes or feedback.

Useful optional fields:

- PhyloP: evolutionary conservation.
- GERP: evolutionary constraint.
- SiPhy: phylogenetic conservation.
- REVEL: external pathogenicity predictor.
- gnomAD AF: population frequency.
- MAVE score: functional experimental evidence.

## 8. Interpreting probability

Use probability as triage:

- High probability: prioritize expert review and independent evidence.
- Intermediate probability: treat as an uncertainty zone.
- Low probability: may suggest lower priority, but does not eliminate risk.
- Discordant result: investigate manually.
- Missing data: treat the conclusion as weak or incomplete.

Do not automatically convert probability into a clinical classification.

## 9. Batch screening

Use batch screening when you have many variants.

Minimal CSV format:

```csv
sample_id,gene,hgvs_p,phylop,gerp,siphy,revel,feature_gnomad_af,feature_mave_score
BRCA1_001,BRCA1,p.Cys61Gly,7.2,5.8,12.4,0.94,0.000002,-1.8
```

Best practices:

- Use one row per variant.
- Keep gene names uppercase.
- Use standardized protein HGVS.
- Do not mix GRCh37 and GRCh38 without declaring it.
- Review row-level errors before interpreting rankings.
- Download the Markdown report for scientific review.
- Save the output CSV with model version and date.

## 10. Real data and public sources

The `Public data` module helps inspect, download, stage, and resolve external sources. This strengthens credibility by reducing dependence on internal examples.

Key sources:

- ClinVar: clinical labels and submissions.
- gnomAD: population frequency.
- MaveDB: MAVE/DMS functional assays.
- BRCA Exchange/ENIGMA: BRCA-specific expert curation.
- ClinGen ERepo: expert-panel classifications.
- UniProt: protein context.
- AlphaFold DB: predicted structural models.
- RCSB PDB: experimental structures.
- CIViC: translational oncology evidence.
- cBioPortal: tumor cohorts.
- GDC: cancer genomics data.
- GWAS Catalog: genetic associations.
- Open Targets: gene-disease evidence.
- PharmGKB: pharmacogenomic context.
- LOVD: locus-specific variant databases.

## 11. Data readiness

A source is closer to ready when it has:

- Resolved local path.
- Non-trivial file size.
- Recognized schema.
- Gene and variant columns.
- Release or download date.
- Fingerprint or hash.
- Official source documented.
- Inventory status marked as `ready`.

Common statuses:

- `ready`: can enter an analysis round after review.
- `partial`: a file exists, but coverage is incomplete.
- `missing`: the source still needs download or normalization.

## 12. Independent data closure

The independent data staging closure creates an honest picture of what is locally staged.

It exports:

- Local inventory.
- Gap plan.
- Review-ready TOML configuration.
- Staging script.
- JSON manifest.
- Markdown and HTML reports.

How to interpret:

- `ready_source_count`: number of ready sources.
- `line_level_real_data_execution_percent`: row-level real-data coverage.
- `independent_data_staging_closure_percent`: overall staging closure.
- `ready_for_next_training_round`: enough data exists for the next round.
- `ready_for_full_independent_retraining`: requires broader critical coverage.

## 13. Publication-style studies

A publication-style study is not just model training. It needs a clear experimental design.

Before running:

- Define the scientific question.
- Freeze sources.
- Separate train, validation, and test sets.
- Define external cohorts.
- Define baselines.
- Define metrics before seeing results.
- Register thresholds.
- Run preflight.

After running:

- Read metrics by cohort.
- Compare prime, non-prime, and hybrid models.
- Check leakage risks.
- Check label conflicts.
- Export the publication package.
- Declare limitations.

## 14. Prime numbers in the platform

The prime-number layer is the project methodologic differentiator.

It can encode:

- Amino acid identity.
- Amino acid substitutions.
- Discrete distances.
- Position signatures.
- Modular relationships.
- Prime gaps and curvature.
- Signals that can be compared across genes.

The key scientific requirement is controlled comparison:

- Prime-feature model.
- Non-prime model.
- Hybrid model.
- External baselines.
- Prime-guided VQE versus non-prime VQE initialization.

Without controls, the prime layer is an interesting idea. With controls, it can become methodologic evidence.

## 15. Proteomics and 3D structure

The proteomics module helps turn a variant into a mechanistic hypothesis.

It can prioritize:

- Functional domains.
- Interface regions.
- Catalytic sites.
- Conserved motifs.
- Disordered regions.
- Fragments for computational chemistry.
- Candidates for functional assays.

Use it to ask:

- Is the mutation near a functional region?
- Could it alter stability?
- Could it alter protein-protein interaction?
- Could it affect DNA, cofactor, or ligand binding?
- Does it deserve more expensive 3D modeling?

## 16. Quantum module and VQE

The quantum module supports exploratory physical and chemical investigation.

It can organize:

- Molecular fragments.
- Active spaces.
- Prime-based seeds.
- Comparisons with non-prime seeds.
- Queues for xTB, DFT, Psi4, OpenMM, docking, and VQE.

Correct interpretation:

- xTB is fast screening.
- DFT is stronger but more expensive.
- Molecular dynamics evaluates stability over time.
- Docking suggests ligand-binding hypotheses.
- VQE is a simplified quantum exploration.

None of these layers prove treatment efficacy. They prioritize hypotheses for experimental validation.

## 17. Translational impact

The impact module measures whether the platform helps real users in real workflows.

Record:

- Reviewed case.
- Prioritized variant.
- Time saved.
- User confidence.
- Perceived actionability.
- Incidents.
- Final recommendation.
- Qualitative comments.

Strong translational impact requires evidence of usefulness, safety, clarity, and reproducibility.

## 18. Readiness levels

Ready for local testing:

- API runs.
- Interface loads.
- Models load.
- Prediction works.
- Documentation exists.

Ready for web staging:

- API key configured.
- CORS configured.
- Logs and audit enabled.
- Persistent volume configured.
- PDFs and manuals available.
- Major errors handled.

Ready for computational preprint:

- Real data tracked.
- Benchmarks frozen.
- Baseline comparisons.
- Prime versus non-prime ablation.
- Limitations declared.
- Reproducible package.

Ready for strong scientific claims:

- Independent validation.
- Functional, structural, or biophysical confirmation.
- Multigene generalization.
- External review.
- Conservative, auditable language.

## 19. Common problems

`API unavailable`

Check that the FastAPI server is running and the port is correct.

`Invalid key`

Check that the server `PRIMEVARCLASS_API_KEY` matches the key entered in the interface.

`No model found`

Confirm that the directory contains `model_registry.csv` and model artifacts.

`Unexpected result`

Check gene, HGVS, optional evidence, and whether the variant is truly missense.

`No gnomAD result`

Check genome build, chromosome, position, REF, ALT, and dataset version.

`MaveDB missing`

The variant may not be covered by the available score set, or coverage may be partial.

`Structural engine unavailable`

Check installation of xTB, Psi4, OpenMM, Vina, or Qiskit in the correct environment.

## 20. Scientific safety statement

Use this statement when needed:

> PrimeVarClass results represent computational prioritization and hypothesis generation. They should be interpreted together with expert curation, applicable guidelines, independent evidence, and functional or structural confirmation before any clinical or therapeutic conclusion.

## 21. Useful paths

- Main interface: `/workbench`
- API documentation: `/docs`
- Knowledge index: `/knowledge`
- User manual Markdown: `/knowledge/manual_en.md`
- User manual PDF: `/knowledge/manual_en.pdf`
- Glossary Markdown: `/knowledge/glossary_en.md`
- Glossary PDF: `/knowledge/glossary_en.pdf`

## 22. Guided first-use route

This route is the recommended path for a new user. It helps you understand the platform, test one variant, inspect evidence, and avoid overinterpreting computational output.

### 22.1 Step 1: open the workbench

Open `/workbench` and confirm:

- The selected language is correct.
- The API key field is empty only if authentication is disabled.
- You can switch between the available modules.
- The documentation, manual, glossary, and feedback links are visible.

Expected result: you understand where to start and how to access support material.

### 22.2 Step 2: inspect models

Open Models before running important predictions.

Check:

- Model directory.
- Model health endpoint.
- Model version or identifier.
- Availability of trained artifacts.

Expected result: you know whether the inference layer is operational.

### 22.3 Step 3: run one variant

Open Prediction and enter:

- Gene symbol, for example `BRCA1`.
- Protein HGVS, for example `p.Arg1699Gln`.
- Experiment name, if available.
- Execution mode, if the interface offers this option.

Expected result: the platform returns a computational probability, class, evidence summary, and warnings when data are missing.

### 22.4 Step 4: read the result responsibly

Read results in this order:

- Probability or primary score.
- Computational class.
- Supporting evidence.
- Conflicting evidence.
- Public sources queried.
- Missing data warnings.
- Suggested validation steps.

Never treat a computational prediction as a standalone clinical conclusion.

### 22.5 Step 5: inspect public data

Open Public data to understand which external sources were used.

Look for:

- Source name.
- Version or release date.
- Manifest.
- Availability status.
- Whether the source is clinical, population, functional, structural, or therapeutic.

Expected result: evidence becomes traceable and auditable.

### 22.6 Step 6: organize a study

Open Studies when you want a reproducible analysis.

Define:

- Scientific question.
- Gene or gene panel.
- Dataset version.
- Inclusion criteria.
- Exclusion criteria.
- Output directory.

Expected result: the analysis becomes suitable for review, benchmarking, and reporting.

### 22.7 Step 7: strengthen scientific credibility

Open Science to inspect:

- Baseline comparisons.
- Non-prime controls.
- Independent validation.
- Prospective validation.
- Functional evidence.
- Structural evidence.

Expected result: the user can separate an exploratory result from a stronger scientific claim.

### 22.8 Step 8: translate findings into impact

Open Impact to connect computational findings with translational relevance.

Ask:

- Which variants deserve experimental prioritization?
- What biological mechanism is plausible?
- Which evidence is still missing?
- Which experimental test would confirm the hypothesis?
- What should not be claimed yet?

Expected result: a responsible translational narrative.

### 22.9 Step 9: check operation

Open Operation before sharing results.

Confirm:

- API status is healthy.
- Jobs completed successfully.
- Logs do not show critical errors.
- Manifests exist.
- Reports were generated.

Expected result: the analysis is traceable and reproducible.

## 23. Platform modules

### 23.1 Home

Use Home to understand the platform, access documentation, select language, and start safely.

### 23.2 Models

Use Models to confirm trained artifacts, model health, directories, and inference readiness.

### 23.3 Prediction

Use Prediction to analyze one variant or a batch of variants and obtain computational prioritization.

### 23.4 Team

Use Team to manage local profile, team context, and multiuser accountability.

### 23.5 Public data

Use Public data to consult, sync, and register independent evidence sources.

### 23.6 Studies

Use Studies to create reproducible analyses with criteria, datasets, outputs, and artifacts.

### 23.7 Science

Use Science to evaluate validation, benchmarks, controls, prime-number contribution, and mechanistic evidence.

### 23.8 Impact

Use Impact to frame translational, social, and experimental relevance.

### 23.9 Operation

Use Operation to inspect jobs, logs, incidents, status, and launch readiness.

## 24. Choosing the right workflow

For a single variant:

- Home.
- Models.
- Prediction.
- Public data.
- Science.
- Impact.
- Operation.

For real-data validation:

- Public data.
- Studies.
- Models.
- Science.
- Operation.
- Impact.

For a publication-oriented study:

- Studies.
- Public data.
- Science.
- Impact.
- Operation.
- Documentation.

For a web launch:

- Operation.
- Team.
- Public data.
- Feedback.
- Manual.
- Glossary.
- Studies.

## 25. Main fields and how to fill them

### 25.1 API key

Use only when authentication is enabled. Paste the key exactly as provided and never expose it in public material.

### 25.2 Gene

Use the official gene symbol, such as `BRCA1`, `TP53`, `PTEN`, `MSH2`, `KRAS`, `GCK`, or `F9`.

### 25.3 Protein variant

Prefer HGVS protein notation, such as `p.Arg1699Gln` or `p.Val600Glu`.

### 25.4 Experiment

Use a short and traceable name, such as `brca1_pilot_2026_05` or `multigene_validation_v1`.

### 25.5 Model directory

Provide the folder containing trained model artifacts, metadata, features, and configuration.

### 25.6 Output directory

Provide the folder where reports, manifests, metrics, logs, and generated artifacts should be saved.

### 25.7 TOML file

Use a TOML file to define study configuration, paths, sources, and execution parameters.

### 25.8 Manifest path

Use a manifest to record data source, version, date, settings, and reproducibility context.

### 25.9 Threshold

Set the cutoff before external validation whenever possible. Avoid changing it after inspecting final results.

## 26. How to interpret outputs

### 26.1 Probability

Probability is the model score. It indicates computational priority, not a clinical diagnosis.

### 26.2 Computational class

Class is the category assigned from the probability and threshold.

Examples: high priority, low priority, uncertain, requires review.

### 26.3 Supporting evidence

Supporting evidence may include rare population frequency, functional score, clinical consistency, conservation, domain relevance, or structural sensitivity.

### 26.4 Conflicting evidence

Conflicting evidence may include ClinVar disagreement, high population frequency, neutral functional assays, or weak structural support.

### 26.5 Manifest

A manifest records what data, configuration, version, and context were used.

### 26.6 Logs

Logs reveal errors, warnings, unavailable sources, missing fields, and incomplete jobs.

### 26.7 Final report

A strong report includes scientific question, data, model, result, evidence, controls, limitations, and next validation steps.

## 27. Ready-to-use workflows

For one variant:

- Open Prediction.
- Enter gene and HGVS protein variant.
- Run inference.
- Read probability and class.
- Check public evidence.
- Inspect Science for validation needs.
- Save the result with a manifest.

For batch triage:

- Prepare a file with gene and variant columns.
- Confirm consistent formatting.
- Run batch analysis.
- Review format errors.
- Rank variants by priority.
- Separate strong, conflicting, and missing-evidence cases.

For public-data validation:

- Confirm real sources.
- Register versions.
- Define train, validation, and test splits.
- Compare against baselines.
- Compare prime encodings against non-prime controls.
- Record metrics and limitations.

For structural investigation:

- Identify protein and variant.
- Check UniProt domains.
- Check AlphaFold DB or PDB structure.
- Inspect functional regions, interfaces, and binding sites.
- Compare reference and mutant.
- Treat the result as a testable hypothesis.

## 28. Common problems

If the interface looks outdated, refresh with `Ctrl+F5`.

If execution returns no result, check API status, required fields, model availability, authentication, and job status.

If public evidence is missing, check source configuration, variant format, and whether the variant exists in that source.

If the model conflicts with ClinVar, record the conflict and inspect population, functional, and structural evidence.

If a benchmark looks too good, check leakage, duplicates, split design, and post-hoc threshold tuning.

## 29. Checklist before sharing results

Technical checklist:

- Platform version is known.
- Gene and HGVS are checked.
- Model loaded correctly.
- Output directory is defined.
- Manifest exists.
- Logs have no critical error.

Scientific checklist:

- Data sources are recorded.
- Independent validation is separated from training.
- Baselines were considered.
- Non-prime controls were considered when relevant.
- Conflicting evidence is preserved.
- Limitations are explicit.

Translational checklist:

- Biological hypothesis is clear.
- Experimental confirmation is suggested.
- Impact is stated without overclaiming.
- Clinical or therapeutic conclusions are not made prematurely.

## 30. Golden rule

PrimeVarClass is strongest when it combines three elements:

- Traceable computational prediction.
- Independent real-world evidence.
- Testable biological interpretation.

Agreement strengthens the hypothesis. Disagreement is not a failure; it is often where the most interesting science begins.
