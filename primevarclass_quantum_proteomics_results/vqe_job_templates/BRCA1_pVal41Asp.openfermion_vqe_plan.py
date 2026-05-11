# PrimeVarClass VQE template for BRCA1 p.Val41Asp
# VQE rank: 10
# Active space: metal/cysteine side-chain fragment; start 4e/4o then expand after classical DFT; prime seed: 4e/6o prime-seeded start; expand only if xTB/DFT supports it
# Ansatz: UCCSD_then_ADAPT_VQE
# Prime coupling: 64.7% (directional_prime_rewiring)
# Prime shot schedule: 2309;3557;6067
# Fill fragment geometry, charge, multiplicity, active space, and backend before execution.
from openfermion.transforms import jordan_wigner
# TODO: generate molecular Hamiltonian with PySCF/Psi4, freeze core, choose active space.
# Prime qubit budget hint: 10-14 qubits after mapping/tapering review
# qubit_hamiltonian = jordan_wigner(fermion_hamiltonian)
# Export to a simulator/VQE stack and compare against xTB/DFT controls.
