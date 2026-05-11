# PrimeVarClass - data and repository policy

This repository stores source code, configuration templates, documentation, reproducible scripts, manifests, and lightweight evidence reports.

It intentionally does not store raw public database downloads or large generated artifacts.

## Included in Git

- Source code in `src/`.
- Tests in `tests/`.
- Reproducible scripts in `scripts/`.
- Configuration files in `configs/`.
- Documentation in `docs/`.
- Lightweight campaign reports and manifests.
- Docker and local staging files.

## Excluded from Git

- `.env` files and secrets.
- Raw datasets under `data/raw/`.
- Local mirrors under `external_data/`.
- External engines/tools under `external_tools/`.
- Large compressed downloads such as `.gz`, `.zip`, `.tar.gz`, `.bgz`.
- Heavy structural/model artifacts such as `.pdb`, `.cif`, `.joblib`, `.pkl`, `.pt`.
- Temporary folders and historical local experiment outputs.

## Reproducibility

Raw data should be restored from official public sources using the manifests, hashes, source URLs, and preparation scripts documented in the project.

For scientific publication, include dataset versions, release dates, SHA-256 fingerprints, and frozen cohort manifests in supplementary material rather than committing large public databases directly.
