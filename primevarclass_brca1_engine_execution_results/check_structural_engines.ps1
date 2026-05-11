$ErrorActionPreference = 'Continue'
Write-Host 'PrimeVarClass structural engine doctor'
$prefix = $env:PRIMEVARCLASS_STRUCTURAL_ENGINE_PREFIX
if ([string]::IsNullOrWhiteSpace($prefix)) { $prefix = 'C:\primevarclass_mamba\envs\primevarclass-structural-engines' }
$env:PATH = "$prefix\Library\bin;$prefix\Scripts;$prefix\bin;$env:PATH"
foreach ($cmd in @('xtb','psi4','vina','autodock_vina','qvina2','qvina','obabel')) {
  $found = Get-Command $cmd -ErrorAction SilentlyContinue
  if ($found) { Write-Host "${cmd}: available at $($found.Source)" }
  else { Write-Host "${cmd}: missing" }
}
@'
import importlib.util
for module in ['openmm', 'qiskit_nature', 'qiskit_algorithms']:
    print(f'{module}: ' + ('available' if importlib.util.find_spec(module) else 'missing'))
'@ | python -
