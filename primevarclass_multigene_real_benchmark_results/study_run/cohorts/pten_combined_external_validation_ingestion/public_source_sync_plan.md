# Public Source Sync Plan

- Config path: C:\Users\Wesley Capucho\Documents\IA dos números primos\primevarclass_multigene_real_benchmark_results\configs\pten_combined_external.toml
- Sync candidates: 1
- Automatable: 1
- Semi-automatable: 0
- Manual-assisted: 0
- Catalog readiness: 72%
- Recommended next step: Usar ClinVar, MaveDB, gnomAD e ENIGMA em staging versionado e partir para os benchmarks finais com coortes publicas reais.

## Sync Items

### ClinVar - pten_combined_external

- Release: -
- Automation level: automatable
- Sync strategy: direct_download
- Preferred channel: ftp_tsv
- Suggested local path: C:/Users/Wesley Capucho/Documents/IA dos números primos/data/raw/multigene/pten/pten_combined_external.tsv
- Readiness: 72%
- Next action: Pode ser automatizada com download/API e versionamento local.

- Official entrypoint: ClinVar downloads overview -> https://www.ncbi.nlm.nih.gov/clinvar/docs/downloads/
- Official entrypoint: ClinVar TSV directory -> https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/
- Expected artifact: variant_summary.txt.gz
- Expected artifact: variant_summary.txt.gz.md5
- Note: Prefer the TSV summary file for cohort assembly.
- Note: Capture the archived monthly release when building a publication cohort.