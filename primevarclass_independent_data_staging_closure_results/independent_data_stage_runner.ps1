# PrimeVarClass independent data staging handoff
# Review source licenses/terms before running any download command.
$ErrorActionPreference = "Stop"

New-Item -ItemType Directory -Force -Path "data/raw" | Out-Null

# MaveDB (mavedb)
New-Item -ItemType Directory -Force -Path "data\raw\mavedb" | Out-Null
# Official: https://www.mavedb.org/
# Hint: use public score-set CSVs, mapped variants, or bulk release dump
# TODO: stage file at data/raw/mavedb/target_gene_function_scores.csv

# AlphaMissense (alphamissense)
New-Item -ItemType Directory -Force -Path "data\raw\alphamissense" | Out-Null
# Official: https://storage.googleapis.com/dm_alphamissense/README.pdf
# Hint: stage AlphaMissense_hg38.tsv.gz or amino-acid substitution subset
# TODO: stage file at data/raw/alphamissense/target_gene_alphamissense.tsv
