# Public Source Sync Plan

- Config path: C:\Users\Wesley Capucho\Documents\IA dos números primos\configs\public_brca_example.toml
- Sync candidates: 3
- Automatable: 2
- Semi-automatable: 1
- Manual-assisted: 0
- Catalog readiness: 72%
- Recommended next step: Usar ClinVar, MaveDB, gnomAD e ENIGMA em staging versionado e partir para os benchmarks finais com coortes publicas reais.

## Sync Items

### ClinVar - clinvar_variant_summary

- Release: -
- Automation level: automatable
- Sync strategy: direct_download
- Preferred channel: ftp_tsv
- Suggested local path: data/examples/clinvar_variant_summary_like.tsv
- Readiness: 72%
- Next action: Pode ser automatizada com download/API e versionamento local.

- Official entrypoint: ClinVar downloads overview -> https://www.ncbi.nlm.nih.gov/clinvar/docs/downloads/
- Official entrypoint: ClinVar TSV directory -> https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/
- Expected artifact: variant_summary.txt.gz
- Expected artifact: variant_summary.txt.gz.md5
- Note: Prefer the TSV summary file for cohort assembly.
- Note: Capture the archived monthly release when building a publication cohort.

### gnomAD - gnomad_brca_annotations

- Release: -
- Automation level: semi_automatable
- Sync strategy: download_or_toolbox_query
- Preferred channel: downloads_page
- Suggested local path: data/examples/gnomad_brca_annotations.tsv
- Readiness: 72%
- Next action: Pode executar recorte BRCA local a partir da tabela gnomAD ja baixada e versionada.

- Official entrypoint: gnomAD downloads -> https://gnomad.broadinstitute.org/downloads
- Official entrypoint: gnomAD toolbox announcement -> https://gnomad.broadinstitute.org/news/2025-01-gnomad-toolbox/
- Expected artifact: browser variants Hail Table or release table export
- Expected artifact: gene-filtered BRCA annotation subset
- Note: gnomAD short-variant downloads can be extremely large.
- Note: For BRCA-focused work, prefer gene-filtered extraction or toolbox-assisted queries.

### MaveDB - mavedb_brca_scores

- Release: -
- Automation level: automatable
- Sync strategy: api_or_bulk_download
- Preferred channel: api
- Suggested local path: data/examples/mavedb_brca_scores.csv
- Readiness: 72%
- Next action: Informe release_version com o URN publico do score set para habilitar sync automatico via API.

- Official entrypoint: MaveDB API -> https://www.mavedb.org/docs/mavedb/api/index.html
- Official entrypoint: MaveDB bulk downloads -> https://www.mavedb.org/docs/mavedb/bulk_downloads.html
- Expected artifact: score set metadata JSON
- Expected artifact: mapped variants JSON
- Expected artifact: score CSV per public score set (optional or bulk release)
- Note: Prefer stable public URNs for publication-grade reproducibility.
- Note: Bulk releases are a strong option when many score sets are needed.
- Note: When release_version stores a public URN, PrimeVarClass can stage score-set metadata and mapped variants directly via the official API.