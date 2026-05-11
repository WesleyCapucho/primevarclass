# PrimeVarClass quantum template for BRCA1 p.Leu22His
# Quantum rank: 7
# Vulnerability: metal_redox_or_cysteine_network
# QM center: BRCA1:22:L->H
# Prime coupling: 69.9% (directional_prime_rewiring)
# Prime topology: stable_prime_topology
# Prime active-space seed: 4e/6o prime-seeded start; expand only if xTB/DFT supports it
# Prime shot schedule: 3299;5087;8677
# Replace placeholder coordinates with a reviewed reference/mutant fragment before execution.
from pathlib import Path
# TODO: load prepared reference/mutant PDB, run local restrained relaxation, export contact deltas.
structure_path = Path('mutant_prepared.pdb')
print(f'Prepare OpenMM local relaxation for {structure_path}')
