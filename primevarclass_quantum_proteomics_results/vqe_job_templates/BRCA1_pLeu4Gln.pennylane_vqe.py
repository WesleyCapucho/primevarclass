# PrimeVarClass VQE template for BRCA1 p.Leu4Gln
# VQE rank: 1
# Active space: metal/cysteine side-chain fragment; start 4e/4o then expand after classical DFT; prime seed: 6e/6o prime-seeded start; expand only if xTB/DFT supports it
# Ansatz: UCCSD_then_ADAPT_VQE
# Prime coupling: 86.7% (strong_prime_displacement)
# Prime shot schedule: 1777;2741;4673
# Fill fragment geometry, charge, multiplicity, active space, and backend before execution.
import pennylane as qml
from pennylane import qchem
# TODO: define symbols, coordinates, charge, multiplicity, and active space.
# Prime-guided seed strategy: Mutant prime index contracts relative to reference; validate the smallest chemically stable active space first before any expansion.
# hamiltonian, qubits = qchem.molecular_hamiltonian(symbols, coordinates)
# dev = qml.device('default.qubit', wires=qubits)
# Build ansatz and optimize expectation value with a classical optimizer.
