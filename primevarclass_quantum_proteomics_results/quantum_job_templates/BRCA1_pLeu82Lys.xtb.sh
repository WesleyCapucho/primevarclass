# PrimeVarClass quantum template for BRCA1 p.Leu82Lys
# Quantum rank: 1
# Vulnerability: metal_redox_or_cysteine_network
# QM center: BRCA1:82:L->K
# Prime coupling: 77.8% (strong_prime_displacement)
# Prime topology: stable_prime_topology
# Prime active-space seed: 6e/6o prime-seeded start; expand only if xTB/DFT supports it
# Prime shot schedule: 2789;4327;7349
# Replace placeholder coordinates with a reviewed reference/mutant fragment before execution.
xtb mutant_fragment.xyz --gfn 2 --opt --alpb water > xtb_mutant_fragment.log
