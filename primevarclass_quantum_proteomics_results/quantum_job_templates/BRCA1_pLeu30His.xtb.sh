# PrimeVarClass quantum template for BRCA1 p.Leu30His
# Quantum rank: 6
# Vulnerability: metal_redox_or_cysteine_network
# QM center: BRCA1:30:L->H
# Prime coupling: 69.9% (directional_prime_rewiring)
# Prime topology: stable_prime_topology
# Prime active-space seed: 4e/6o prime-seeded start; expand only if xTB/DFT supports it
# Prime shot schedule: 3299;5087;8677
# Replace placeholder coordinates with a reviewed reference/mutant fragment before execution.
xtb mutant_fragment.xyz --gfn 2 --opt --alpb water > xtb_mutant_fragment.log
