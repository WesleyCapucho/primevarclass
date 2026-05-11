$ErrorActionPreference = 'Stop'
$envFile = "C:\Users\Wesley Capucho\Documents\IA dos números primos\primevarclass_brca1_engine_execution_results\environment.structural-engines.yml"
if (Get-Command micromamba -ErrorAction SilentlyContinue) {
  micromamba create -y -f $envFile
  Write-Host 'Created primevarclass-structural-engines with micromamba.'
} elseif (Get-Command mamba -ErrorAction SilentlyContinue) {
  mamba env create -f $envFile
  Write-Host 'Created primevarclass-structural-engines with mamba.'
} elseif (Get-Command conda -ErrorAction SilentlyContinue) {
  conda env create -f $envFile
  Write-Host 'Created primevarclass-structural-engines with conda.'
} else {
  throw 'Install micromamba, mamba, or conda first, then rerun this script.'
}
