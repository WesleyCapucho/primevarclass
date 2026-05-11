# PrimeVarClass quantum template for BRCA1 p.Val41Asp
# Quantum rank: 9
# Vulnerability: metal_redox_or_cysteine_network
# QM center: BRCA1:41:V->D
# Prime coupling: 64.7% (directional_prime_rewiring)
# Prime topology: stable_prime_topology
# Prime active-space seed: 4e/6o prime-seeded start; expand only if xTB/DFT supports it
# Prime shot schedule: 2309;3557;6067
# Replace placeholder coordinates with a reviewed reference/mutant fragment before execution.
xtb mutant_fragment.xyz --gfn 2 --opt --alpb water > xtb_mutant_fragment.log
