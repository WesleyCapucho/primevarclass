# PrimeVarClass public-source bootstrap bundle
# Generated automatically to help stage official public datasets locally.
# Review comments for semi-automatable and manual-assisted sources before execution.

$ErrorActionPreference = 'Stop'

# Source: ClinVar (clinvar_variant_summary)
# Release: -
# Automation level: automatable
# Next action: Pode ser automatizada com download/API e versionamento local.
#
#
#
#
#
# Official entrypoint: ClinVar downloads overview -> https://www.ncbi.nlm.nih.gov/clinvar/docs/downloads/
# Official entrypoint: ClinVar TSV directory -> https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/
# Expected artifact: variant_summary.txt.gz
# Expected artifact: variant_summary.txt.gz.md5
New-Item -ItemType Directory -Force -Path 'C:\Users\Wesley Capucho\Documents\IA dos números primos\primevarclass_continuous_learning_results\bootstrap_workspace\clinvar\clinvar_variant_summary' | Out-Null
Invoke-WebRequest -Uri 'https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/variant_summary.txt.gz' -OutFile 'C:\Users\Wesley Capucho\Documents\IA dos números primos\primevarclass_continuous_learning_results\bootstrap_workspace\clinvar\clinvar_variant_summary\variant_summary.txt.gz'
Invoke-WebRequest -Uri 'https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/variant_summary.txt.gz.md5' -OutFile 'C:\Users\Wesley Capucho\Documents\IA dos números primos\primevarclass_continuous_learning_results\bootstrap_workspace\clinvar\clinvar_variant_summary\variant_summary.txt.gz.md5'


# Source: gnomAD (gnomad_brca_annotations)
# Release: -
# Automation level: semi_automatable
# Next action: Pode executar recorte BRCA local a partir da tabela gnomAD ja baixada e versionada.
# Local source path: data/examples/gnomad_brca_annotations.tsv
# Local source available: yes
#
#
#
# Official entrypoint: gnomAD downloads -> https://gnomad.broadinstitute.org/downloads
# Official entrypoint: gnomAD toolbox announcement -> https://gnomad.broadinstitute.org/news/2025-01-gnomad-toolbox/
# Expected artifact: browser variants Hail Table or release table export
# Expected artifact: gene-filtered BRCA annotation subset
New-Item -ItemType Directory -Force -Path 'C:\Users\Wesley Capucho\Documents\IA dos números primos\primevarclass_continuous_learning_results\bootstrap_workspace\gnomad\gnomad_brca_annotations' | Out-Null
# PrimeVarClass runner step: filter local table 'C:\Users\Wesley Capucho\Documents\IA dos números primos\data\examples\gnomad_brca_annotations.tsv'
# Output subset: 'C:\Users\Wesley Capucho\Documents\IA dos números primos\primevarclass_continuous_learning_results\bootstrap_workspace\gnomad\gnomad_brca_annotations\gnomad_brca_subset.tsv'
# Output manifest: 'C:\Users\Wesley Capucho\Documents\IA dos números primos\primevarclass_continuous_learning_results\bootstrap_workspace\gnomad\gnomad_brca_annotations\gnomad_brca_subset_manifest.json'
# Genes: BRCA1, BRCA2


# Source: MaveDB (mavedb_brca_scores)
# Release: -
# Automation level: automatable
# Next action: Informe release_version com o URN publico do score set para habilitar sync automatico via API.
#
#
#
#
# MaveDB URN: -
# Official entrypoint: MaveDB API -> https://www.mavedb.org/docs/mavedb/api/index.html
# Official entrypoint: MaveDB bulk downloads -> https://www.mavedb.org/docs/mavedb/bulk_downloads.html
# Expected artifact: score set metadata JSON
# Expected artifact: mapped variants JSON
# Expected artifact: score CSV per public score set (optional or bulk release)
New-Item -ItemType Directory -Force -Path 'C:\Users\Wesley Capucho\Documents\IA dos números primos\primevarclass_continuous_learning_results\bootstrap_workspace\mavedb\mavedb_brca_scores' | Out-Null
# TODO: defina release_version = 'urn:mavedb:...' no catalogo para habilitar sync automatico do score set.
