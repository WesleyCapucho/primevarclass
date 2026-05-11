# PrimeVarClass Multigene Row-Level Annotation Enrichment

- Generated at: `2026-05-11T00:13:11Z`
- Target genes: `F9, GCK, KRAS, MSH2, PTEN, TP53`
- Variant rows: `1668`
- GRCh38 coordinate coverage: `100%`
- gnomAD line evidence coverage: `0%`
- MaveDB line evidence coverage: `90%`
- Line-level annotation readiness: `62%`

## Gene coverage

| Gene | Rows | Coord | gnomAD hit | MaveDB | Readiness |
| --- | ---: | ---: | ---: | ---: | ---: |
| TP53 | 364 | 100% | 0% | 99% | 65% |
| F9 | 216 | 99% | 1% | 96% | 64% |
| MSH2 | 414 | 100% | 0% | 98% | 64% |
| GCK | 365 | 100% | 1% | 92% | 63% |
| PTEN | 238 | 100% | 0% | 73% | 58% |
| KRAS | 71 | 100% | 0% | 23% | 46% |

## Guardrails

- gnomAD live queries are intentionally capped to keep the benchmark reproducible and respectful of public services.
- MaveDB live evidence is joined by gene and protein HGVS; genomic VRS reconciliation is queued as the next precision upgrade.
- Rows without GRCh38 coordinates remain excluded from gnomAD allele-frequency interpretation until coordinate reconciliation is complete.