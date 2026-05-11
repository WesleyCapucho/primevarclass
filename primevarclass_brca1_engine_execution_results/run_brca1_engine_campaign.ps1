$ErrorActionPreference = 'Stop'
$queuePath = "C:\Users\Wesley Capucho\Documents\IA dos números primos\primevarclass_brca1_engine_execution_results\brca1_engine_execution_queue.csv"
$queue = Import-Csv $queuePath
foreach ($row in $queue) {
  Write-Host "BRCA1 $($row.hgvs_p): $($row.execution_status)"
  if ($row.execution_status -ne 'ready_to_execute') { continue }
  foreach ($field in @('xtb_command','psi4_command','openmm_command','vina_command','qiskit_nature_vqe_command')) {
    $cmd = $row.$field
    if ([string]::IsNullOrWhiteSpace($cmd)) { continue }
    Write-Host "Running $field: $cmd"
    powershell -NoProfile -ExecutionPolicy Bypass -Command $cmd
  }
}
