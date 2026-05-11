# PrimeVarClass - Glossary

Version: 2026.05

This glossary explains the most important platform terms in accessible language. It is intended for both beginners and experienced researchers.

## ACMG/AMP

Guidelines used to interpret genetic variants. PrimeVarClass can help organize evidence, but it does not replace formal ACMG/AMP curation.

## AlphaFold DB

Database of predicted protein structures. In PrimeVarClass, it helps locate where a variant occurs in the protein.

Limit: AlphaFold is structural prediction, not experimental structure.

## AlphaMissense

External predictor for missense variant effects. It can be used as an independent comparison against PrimeVarClass.

Correct use: compare agreement and disagreement, not as final truth.

## API

Programmable interface that allows other systems to communicate with the platform. PrimeVarClass uses a FastAPI backend.

## API key

Access key used to protect the platform when exposed on a network.

Best practice: never publish the key in a paper, screenshot, repository, or shared document.

## Baseline

Reference model or method used for comparison.

Example: a non-prime random forest, logistic regression, or external predictor.

## Batch screening

Analysis of many variants at once, usually from a CSV file.

## Benchmark

Evaluation designed to measure model performance under defined conditions.

## Frozen benchmark

Benchmark where data, splits, parameters, thresholds, and metrics are fixed before evaluation.

Why it matters: reduces leakage, overfitting, and opportunistic interpretation.

## BRCA Exchange

Specialized database for BRCA1 and BRCA2 variants. Useful for BRCA-specific validation and expert comparison.

## cBioPortal

Platform containing tumor cohort data. In PrimeVarClass, it helps connect genes and variants to oncology context.

Limit: somatic tumor evidence should not automatically be treated as germline pathogenicity evidence.

## ClinGen ERepo

Evidence repository containing expert-panel classifications. Important for external validation and independent curation.

## ClinVar

Public database of genetic variants and clinical interpretations submitted by laboratories and expert groups.

Limit: ClinVar may include conflicts, different review levels, and older submissions.

## Cohort

Set of variants, patients, samples, or records used in an analysis.

Examples: training cohort, external cohort, BRCA cohort, TP53 cohort.

## Computational preprint

Manuscript stage where software, data processing, benchmarks, and evidence are strong enough for computational publication, but not necessarily for clinical claims.

## Data leakage

When information from validation or test data indirectly enters training.

Risk: performance looks better than it truly is.

## DFT

Density Functional Theory. Quantum chemistry method used to estimate energetic and electronic properties.

Use in PrimeVarClass: stronger follow-up after fast xTB screening.

## Docking

Simulation of how a molecule may bind to a protein.

Limit: docking suggests a hypothesis, not therapeutic efficacy.

## External holdout

Dataset kept separate from training and used to evaluate generalization.

## Feature

Variable used by a model.

Examples: gnomAD frequency, MAVE score, conservation score, prime gap, prime curvature.

## Fingerprint

Technical summary of an artifact, usually including hash, size, and date.

Use: reproducibility and audit.

## Functional evidence

Evidence that measures or suggests the effect of a variant on biological function.

Examples: MAVE/DMS, cellular assay, transactivation, stability, enzymatic activity.

## GDC

NCI Genomic Data Commons. Source of cancer genomic data.

## Gene

DNA region that encodes or regulates a functional product. In the platform, gene is the main unit for grouping variants and evidence.

## gnomAD

Genome Aggregation Database. Public source of population allele frequencies.

Interpretation: high frequency may argue against strong pathogenicity for rare disease; low frequency does not prove pathogenicity.

## GWAS Catalog

Database of genetic associations between variants, regions, genes, and traits.

Use: biological plausibility and gene-disease context.

## HGVS protein notation

Standardized protein variant notation.

Example: `p.Cys61Gly` means cysteine changed to glycine at position 61.

## Independent validation

Evaluation on data not used during model development.

## Interpretability

Ability to understand why a result was produced.

Examples: frequency, conservation, MAVE score, structural region, prime signature.

## Label

Target class used for training or evaluation.

Examples: benign, pathogenic, VUS, functional, non-functional.

## LOVD

Leiden Open Variation Database. A collection of locus-specific variant databases.

## Manifest

JSON file recording paths, parameters, sources, versions, hashes, and generated artifacts.

Why it matters: enables reproducibility and audit.

## MAVE

Multiplexed Assay of Variant Effect. High-throughput assay measuring effects of many variants.

## MaveDB

Public repository of MAVE studies.

Use in PrimeVarClass: independent functional evidence.

## Missense variant

Variant that changes one amino acid to another.

Example: `p.Arg175His`.

## Multigene generalization

Ability of the method to work beyond one gene.

Example: expanding from BRCA1/BRCA2 to TP53, PTEN, MSH2, KRAS, GCK, and F9.

## Non-prime control

Model, initialization, or feature set that does not use the prime-number layer.

Why it matters: tests whether prime numbers add real value.

## Open Targets

Gene-disease evidence platform. Useful for translational context.

## Overfitting

When a model learns training-specific details but fails on new data.

Warning sign: excellent training performance and weak external performance.

## PDB

Protein Data Bank. Repository of experimental protein structures.

Use: strengthens structural interpretation when a relevant structure exists.

## PharmGKB

Pharmacogenomic knowledge base. Helps contextualize genes and variants in relation to drugs and therapeutic response.

## Preflight

Check performed before a main execution.

It detects missing files, incomplete schemas, leakage risk, insufficient data, and reproducibility problems.

## Prime numbers

Numbers divisible only by 1 and themselves.

In PrimeVarClass, prime numbers are used to encode amino acids, substitutions, distances, and discrete patterns.

Scientific importance: the prime layer becomes credible only when it beats fair non-prime controls.

## Prime-guided VQE

Use of prime-number signatures to guide initialization, fragment choice, active-space seed, or execution strategy in VQE.

Required control: compare with non-prime VQE initialization.

## Protein structural context

Information about where a variant lies in a protein and what that region does.

Examples: domain, interface, catalytic site, disordered region.

## Reproducibility

Ability to repeat an analysis with the same data, versions, and parameters.

Platform tools: manifests, fingerprints, reports, configs, and logs.

## Shadow pilot

Pilot mode where the platform runs alongside the human process without influencing final decisions.

Use: measure safety, clarity, and usefulness before real adoption.

## Split

Division of data into training, validation, test, or external cohorts.

## Staging

Process of placing data in a standardized, traceable local format ready for use.

## Threshold

Cutoff used to convert probability into a class.

Best practice: define it before external evaluation.

## Translational impact

Evidence that the platform is useful in real scientific or laboratory workflows.

Examples: time saved, better prioritization, clearer evidence, safer review.

## UniProt

Protein knowledge base providing accessions, length, domains, function, and annotations.

## VQE

Variational Quantum Eigensolver. Hybrid quantum-classical algorithm for estimating energy in simplified systems.

## VUS

Variant of Uncertain Significance.

Important: a VUS should not be treated as benign or pathogenic without additional evidence.

## xTB

Fast semiempirical method for chemical and structural screening.

Use: first-pass triage before more expensive calculations such as DFT.

## Actionability

Degree to which evidence can guide a practical research, experimental, translational, or therapeutic-investigation action.

Important: actionability in the platform is not an automatic clinical recommendation.

## API key

Code used to authenticate a request or identify an authorized user.

Safety: never expose API keys in public screenshots, reports, repositories, or messages.

## Artifact

Any file used or produced during an analysis.

Examples: trained model, report, manifest, log, chart, result table, configuration, and study package.

## Authentication disabled

State in which the platform allows local use without requiring an API key.

Use: common in development, local validation, and controlled demonstrations.

## Browser cache

Local storage used by a browser to load pages, styles, and scripts faster.

Common issue: after an interface update, the browser may show an older version. Refreshing with `Ctrl+F5` usually resolves it.

## Codon

Sequence of three DNA or RNA bases that encodes one amino acid or a stop signal.

Relation to missense variants: a base change can alter a codon and replace the resulting amino acid.

## Data sync

Process of fetching, updating, or registering data from public scientific sources.

Use: keeps the platform aligned with current external evidence.

## Engine

Computational component that performs a specific task.

Examples: inference engine, structural engine, quantum engine, public-data sync engine, and benchmark engine.

## Feedback

User-submitted record describing an error, question, suggestion, or usability issue.

Good feedback includes module, input, expected result, observed result, and error message.

## File path

Local or relative address indicating where a file is stored.

Examples: model directory, output directory, manifest path, and dataset path.

## Handoff

Organized delivery of data, results, or artifacts from one step to another person, module, or process.

Example: a package containing manifest, results, and logs delivered for independent validation.

## Interpretable inference

Prediction accompanied by explanations, evidence, or signals that help the user understand why a model produced a result.

Important: interpretability does not make a result infallible.

## Interpretable inference with real data

Analysis mode that combines model prediction with evidence from public sources or real datasets.

Scientific value: reduces dependence on synthetic examples and strengthens external credibility.

## Job

Computational task executed by the platform.

Examples: predict variant, sync data, train model, run benchmark, generate PDF, and create manifest.

## Job queue

List of tasks waiting to be executed or processed.

Use: important for multiuser platforms, long analyses, and automated routines.

## Local environment

Mode in which the platform runs on the user's own machine or internal development environment.

Use: suitable for tests, demonstrations, early validation, and private work.

## Local profile

Profile used in a local environment when full authentication is not enabled.

Use: useful for development and initial validation, but less robust than complete multiuser identity.

## Module

Functional area of the interface dedicated to one part of the platform.

Examples: Home, Models, Prediction, Team, Public data, Studies, Science, Impact, and Operation.

## Multiuser

Capability for multiple people to use the platform with separated profiles, permissions, logs, and context.

Important: requires authentication, audit trails, feedback, documentation, and governance.

## Nitrogenous bases

Chemical components of DNA and RNA. In DNA, the main bases are adenine, thymine, cytosine, and guanine.

Relation to the platform: genetic variants start as base changes and may result in amino acid changes.

## Nucleotide

Basic unit of DNA or RNA, composed of a nitrogenous base, sugar, and phosphate group.

Relation to variants: nucleotide changes can alter codons and proteins.

## Output directory

Folder where the platform writes results.

Examples: reports, manifests, logs, metrics, figures, and analysis packages.

## Panel

Visual block in the interface that groups related information or actions.

Examples: status panel, result panel, team panel, and public-data panel.

## Public catalog

Public scientific data source used for query, training, validation, or evidence enrichment.

Examples: ClinVar, gnomAD, MaveDB, UniProt, PDB, AlphaFold DB, Open Targets, PharmGKB, and GWAS Catalog.

## Public data

Data made available by institutions, consortia, repositories, or scientific databases.

Important: public does not mean perfect. Every source has scope, version, bias, criteria, and limitations.

## Request

Message sent by the interface or another system asking the API to perform an action.

Examples: query model, predict variant, download document, or start data sync.

## Score

Numerical value produced by a model, database, or computational method.

Examples: model probability, MAVE functional score, allele frequency, conservation score, and estimated energy.

## Study package

Organized set of files needed to review or reproduce an analysis.

Examples: configuration, manifest, results, logs, metrics, figures, and report.

## Team ID

Identifier associated with the active team.

Use: relevant for collaboration, auditing, governance, and multiuser operation.

## Web readiness

Degree to which the platform is prepared for external users over the web.

Includes: authentication, stability, documentation, security, feedback, logs, accessibility, and infrastructure.

## Workbench

Main platform working area, available at `/workbench`.

Use: gathers the scientific and operational modules in a single interface.
