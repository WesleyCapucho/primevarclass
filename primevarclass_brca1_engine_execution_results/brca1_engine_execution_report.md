# PrimeVarClass BRCA1 Real-Engine Execution Package

- Generated at: `2026-04-25T02:35:07Z`
- Queue targets: `12`
- AlphaFold reference available: `True`
- Engine availability: `100%`
- Missing engines: `0`
- Execution preflight: `blocked_needs_reviewed_coordinates`
- Ready-to-execute targets: `0`
- Targets needing reviewed coordinates/inputs: `9`
- Blocked targets: `0`
- Execution readiness: `81%`
- Real executions completed now: `0`

## Engine status

- xtb: `available`
- psi4: `available`
- vina: `available`
- obabel: `available`
- openmm: `available`
- qiskit_nature: `available`

## What this closes

- The BRCA1 campaign now has a concrete execution queue, environment file, installer, runner, and AlphaFold coordinate source.
- If engines are missing, the package records that blocker instead of fabricating xTB/DFT/VQE evidence.
- Once the environment is installed, rerunning this package can execute the ready rows and preserve command logs.