# PrimeVarClass quantum template for BRCA1 p.Leu4Gln
# Quantum rank: 12
# Vulnerability: metal_redox_or_cysteine_network
# QM center: BRCA1:4:L->Q
# Prime coupling: 86.7% (strong_prime_displacement)
# Prime topology: stable_prime_topology
# Prime active-space seed: 6e/6o prime-seeded start; expand only if xTB/DFT supports it
# Prime shot schedule: 1777;2741;4673
# Replace placeholder coordinates with a reviewed reference/mutant fragment before execution.
xtb mutant_fragment.xyz --gfn 2 --opt --alpb water > xtb_mutant_fragment.log
