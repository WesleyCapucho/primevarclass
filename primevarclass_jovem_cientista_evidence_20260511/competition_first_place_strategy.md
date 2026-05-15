# PrimeVarClass strategy for Prêmio Jovem Cientista 2026

## Official competition alignment

- Edition: 32nd Prêmio Jovem Cientista 2026.
- Theme: Inteligência Artificial para o bem comum.
- Official submission window: until 31 July 2026.
- Target category: Estudante do Ensino Superior.
- Eligibility focus: undergraduate students, or students who completed undergraduate studies from 1 January 2025 onward, under 30 years old by the end of 2026.
- Official sources:
  - https://www.gov.br/cnpq/pt-br/assuntos/noticias/premios/premio-jovem-cientista-2026-inscricoes-estao-abertas-ate-31-de-julho
  - https://www.gov.br/cnpq/pt-br/assuntos/noticias/premios/premio-jovem-cientista-2026-tera-como-tema-ia-para-o-bem-comum-inscricoes-estao-abertas

## Winning thesis

PrimeVarClass should be presented as a responsible AI platform for the common good that helps prioritize uncertain or difficult missense variants, starting with hereditary cancer genes, using a transparent prime-number encoding, public biomedical evidence, independent functional predictors and reproducible validation.

The project should not be framed as a diagnostic device. The strongest and safest claim is:

PrimeVarClass is an open, reproducible research platform that combines prime-number feature engineering with biological evidence to accelerate variant interpretation, expose uncertainty, nominate testable mechanisms and support more equitable access to genomic decision support in Brazil.

## Evidence already achieved

- Competition readiness: 93.1%.
- Paper readiness: 91.1%.
- Web-launch scientific readiness: 89.1%.
- Targeted tests: 39/39 passed in the current evidence matrix.
- AlphaMissense priority coverage: 50/50 priority variants, 100.0% local coverage.
- AlphaMissense priority overlay: AUC-ROC 0.973333, functional support rate 92.0%.
- Discordance hypotheses: 4 variants flagged for mechanistic review.
- Locked calibration holdout: 417 held-out variants with calibrated safety support.
- Cohort independence: frozen external cohorts with no train/external variant overlap in the audited run.

## What makes this competitive

- It directly matches the theme because it uses AI for health equity, scientific transparency and public-good biomedical infrastructure.
- It has a concrete social target: improving access to variant-prioritization tools for students, researchers and potentially under-resourced clinical research groups.
- It is not only a web app: it has reproducible pipelines, public-data provenance, benchmark artifacts, calibration evidence and claim boundaries.
- It contains a distinctive methodological element: prime-number encodings are used as structured biological feature engineering, then compared with biochemical and external evidence.
- It produces testable biological hypotheses instead of only a classification score.

## First-place development priorities

1. Full AlphaMissense BRCA benchmark.

Run the full BRCA study with AlphaMissense as a sparse/expanded functional predictor, then compare against the current frozen quick pass. This converts the current priority-overlay evidence into full-cohort functional validation.

2. Prime-number ablation narrative.

Create a concise table and figure showing prime-only, biochemical-only, external-only, hybrid and hybrid-plus-external performance. The key message should be honest: prime features are a transparent hypothesis engine, and their value is strongest when integrated with biological evidence.

3. Mechanistic case studies.

Turn the four AlphaMissense discordance/ambiguity cases into mini case studies with:
- clinical/external label
- PrimeVarClass score
- AlphaMissense score and class
- MAVE/gnomAD status
- structural or functional hypothesis
- recommended experimental confirmation

4. Public-good impact package.

Prepare a 1-page impact narrative focused on:
- democratizing access to genomic AI tools
- research-use safeguards
- Portuguese/English interface
- reproducible public-data workflows
- undergraduate-friendly manual and glossary
- non-diagnostic responsible-AI framing

5. Submission-grade demo.

Before submission, the platform should show one clean workflow:
- select module
- upload or choose example variants
- run prediction
- explain prime features
- show external evidence
- show uncertainty/limitations
- export a report

6. Validation boundary.

Keep the strongest clinical sentence conservative:

This platform is validated as a retrospective research and prioritization workflow, not as a standalone clinical diagnostic system. Prospective independent validation and wet-lab/structural confirmation remain required before diagnostic claims.

## Submission narrative

The strongest story is:

A Brazilian undergraduate-led AI platform uses an original prime-number representation of amino-acid changes, combines it with public biomedical evidence, validates it on real BRCA data, exposes its own failure modes, and turns difficult variants into functional hypotheses that can guide future experiments and reduce barriers to genomic research.

## Recommended figures for the final paper/application

- Figure 1: PrimeVarClass architecture from public datasets to prediction, explanation and hypothesis generation.
- Figure 2: Prime-number encoding of amino-acid substitutions and how it interacts with biochemical features.
- Figure 3: Validation design showing train, external cohorts, locked calibration and priority error queue.
- Figure 4: AlphaMissense priority overlay with 50/50 coverage, AUC-ROC 0.973333 and discordance hypotheses.
- Figure 5: Social-impact workflow for accessible research-use variant interpretation.

## Final pre-submission checklist

- Full BRCA AlphaMissense rerun completed or clearly marked as ongoing.
- Prime ablation table ready.
- Four mechanistic case studies written.
- Demo platform stable in Portuguese-BR and English.
- Manual and glossary available as PDF.
- Claims boundary included in the application.
- GitHub repository and Release artifacts clean, with no raw heavy files committed.
- One-page social-impact narrative prepared for the judges.
