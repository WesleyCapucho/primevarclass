# PrimeVarClass VQE template for BRCA1 p.Leu22His
# VQE rank: 8
# Active space: metal/cysteine side-chain fragment; start 4e/4o then expand after classical DFT; prime seed: 4e/6o prime-seeded start; expand only if xTB/DFT supports it
# Ansatz: UCCSD_then_ADAPT_VQE
# Prime coupling: 69.9% (directional_prime_rewiring)
# Prime shot schedule: 3299;5087;8677
# Fill fragment geometry, charge, multiplicity, active space, and backend before execution.
import pennylane as qml
from pennylane import qchem
# TODO: define symbols, coordinates, charge, multiplicity, and active space.
# Prime-guided seed strategy: Mutant prime index contracts relative to reference; validate the smallest chemically stable active space first before any expansion.
# hamiltonian, qubits = qchem.molecular_hamiltonian(symbols, coordinates)
# dev = qml.device('default.qubit', wires=qubits)
# Build ansatz and optimize expectation value with a classical optimizer.
