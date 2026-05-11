param(
    [string]$OutputRoot = "primevarclass_jovem_cientista_evidence_20260510\brca_real_full",
    [string]$PythonLauncher = "py -3.14"
)

$ErrorActionPreference = "Stop"

Write-Host "PrimeVarClass full evidence campaign"
Write-Host "Output: $OutputRoot"
Write-Host "This is the long publication-grade BRCA run. Prefer running it when the machine can work for several hours."

$env:PRIMEVARCLASS_N_JOBS = "1"

New-Item -ItemType Directory -Force -Path $OutputRoot | Out-Null

$command = "$PythonLauncher -m primevarclass --study-config configs\jovem_cientista_brca_evidence_full.toml --output-dir `"$OutputRoot`""
Write-Host "Running: $command"
Invoke-Expression $command

Write-Host "Full campaign finished."
