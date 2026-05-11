# PrimeVarClass quantum template for BRCA1 p.Leu22Glu
# Quantum rank: 3
# Vulnerability: metal_redox_or_cysteine_network
# QM center: BRCA1:22:L->E
# Prime coupling: 77.8% (strong_prime_displacement)
# Prime topology: stable_prime_topology
# Prime active-space seed: 6e/6o prime-seeded start; expand only if xTB/DFT supports it
# Prime shot schedule: 2789;4327;7349
# Replace placeholder coordinates with a reviewed reference/mutant fragment before execution.
from pathlib import Path
# TODO: load prepared reference/mutant PDB, run local restrained relaxation, export contact deltas.
structure_path = Path('mutant_prepared.pdb')
print(f'Prepare OpenMM local relaxation for {structure_path}')
