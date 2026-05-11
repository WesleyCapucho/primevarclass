# PrimeVarClass Public Source Bootstrap Guide

- Config path: C:\Users\Wesley Capucho\Documents\IA dos números primos\configs\public_brca_example.toml
- Output root: C:\Users\Wesley Capucho\Documents\IA dos números primos\primevarclass_continuous_learning_results\bootstrap_workspace

## Sources

### ClinVar - clinvar_variant_summary

- Release: -
- Automation level: automatable
- Target dir: C:\Users\Wesley Capucho\Documents\IA dos números primos\primevarclass_continuous_learning_results\bootstrap_workspace\clinvar\clinvar_variant_summary
- Script-executable: yes
- Next action: Pode ser automatizada com download/API e versionamento local.
- Official entrypoint: [ClinVar downloads overview](https://www.ncbi.nlm.nih.gov/clinvar/docs/downloads/)
- Notes: ClinVar documents weekly updates and monthly archived releases for XML, VCF, and TSV.
- Official entrypoint: [ClinVar TSV directory](https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/)
- Notes: Recommended for variant_summary-based ingestion into PrimeVarClass.
- Expected artifact: variant_summary.txt.gz
- Expected artifact: variant_summary.txt.gz.md5

### gnomAD - gnomad_brca_annotations

- Release: -
- Automation level: semi_automatable
- Target dir: C:\Users\Wesley Capucho\Documents\IA dos números primos\primevarclass_continuous_learning_results\bootstrap_workspace\gnomad\gnomad_brca_annotations
- Script-executable: yes
- Next action: Pode executar recorte BRCA local a partir da tabela gnomAD ja baixada e versionada.
- Local source path: data/examples/gnomad_brca_annotations.tsv
- Local source available: yes
- Gene allowlist: BRCA1, BRCA2
- Official entrypoint: [gnomAD downloads](https://gnomad.broadinstitute.org/downloads)
- Notes: Use the official downloads page for release files and browser tables.
- Official entrypoint: [gnomAD toolbox announcement](https://gnomad.broadinstitute.org/news/2025-01-gnomad-toolbox/)
- Notes: Recommended when full downloads are too large for local handling.
- Expected artifact: browser variants Hail Table or release table export
- Expected artifact: gene-filtered BRCA annotation subset

### MaveDB - mavedb_brca_scores

- Release: -
- Automation level: automatable
- Target dir: C:\Users\Wesley Capucho\Documents\IA dos números primos\primevarclass_continuous_learning_results\bootstrap_workspace\mavedb\mavedb_brca_scores
- Script-executable: no
- Next action: Informe release_version com o URN publico do score set para habilitar sync automatico via API.
- Resolved URN: -
- Official entrypoint: [MaveDB API](https://www.mavedb.org/docs/mavedb/api/index.html)
- Notes: Use for score set metadata and programmatic access.
- Official entrypoint: [MaveDB bulk downloads](https://www.mavedb.org/docs/mavedb/bulk_downloads.html)
- Notes: Zenodo-backed archival releases updated twice yearly.
- Expected artifact: score set metadata JSON
- Expected artifact: mapped variants JSON
- Expected artifact: score CSV per public score set (optional or bulk release)